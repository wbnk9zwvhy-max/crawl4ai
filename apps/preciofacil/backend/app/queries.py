from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, select

from scrapers.taxonomy import CATEGORY_BY_SLUG

from .models import Category, PriceSnapshot, Product, Supermarket
from .product_matching import format_pack, is_plausible_match
from .schemas import CategoryOut, ProductPriceOut


def _filtered_snapshot_query(category_slug: str | None, supermarket_slug: str | None):
    query = select(Product, PriceSnapshot).join(PriceSnapshot, PriceSnapshot.product_id == Product.id)
    if category_slug:
        query = query.where(Product.category_slug == category_slug)
    if supermarket_slug:
        query = query.where(Product.supermarket_slug == supermarket_slug)
    return query


def latest_snapshot_per_product(
    session: Session, category_slug: str | None = None, supermarket_slug: str | None = None
) -> list[tuple[Product, PriceSnapshot]]:
    """Para cada producto, su snapshot de precio más reciente."""
    rows = session.exec(_filtered_snapshot_query(category_slug, supermarket_slug)).all()

    latest: dict[int, tuple[Product, PriceSnapshot]] = {}
    for product, snapshot in rows:
        current = latest.get(product.id)
        if current is None or snapshot.scraped_at > current[1].scraped_at:
            latest[product.id] = (product, snapshot)
    return list(latest.values())


def best_snapshot_per_product_since(
    session: Session,
    since: datetime,
    category_slug: str | None = None,
    supermarket_slug: str | None = None,
) -> list[tuple[Product, PriceSnapshot]]:
    """Para cada producto, su MEJOR precio (más bajo) visto desde ``since``
    en adelante — usado para las ofertas destacadas "de la semana"."""
    query = _filtered_snapshot_query(category_slug, supermarket_slug).where(PriceSnapshot.scraped_at >= since)
    rows = session.exec(query).all()

    best: dict[int, tuple[Product, PriceSnapshot]] = {}
    for product, snapshot in rows:
        current = best.get(product.id)
        if current is None or snapshot.price < current[1].price:
            best[product.id] = (product, snapshot)
    return list(best.values())


def to_product_price_out(product: Product, snapshot: PriceSnapshot, supermarket: Supermarket) -> ProductPriceOut:
    # Preferimos la copia local descargada del producto (servida bajo
    # /media) a enlazar en caliente el CDN del supermercado: es más
    # fiable, más rápida y no depende de que el hotlink siga permitido.
    image_url = f"/media/{product.image_path}" if product.image_path else product.image_url
    # Si no tenemos la URL exacta del producto, al menos enlazamos a la
    # tienda online del supermercado para el botón "Comprar en X".
    buy_url = product.url or supermarket.online_store_url or None
    pack_label = (
        format_pack(product.pack_qty, product.pack_unit)
        if product.pack_qty is not None and product.pack_unit is not None
        else None
    )
    return ProductPriceOut(
        product_id=product.id,
        supermarket_slug=supermarket.slug,
        supermarket_name=supermarket.name,
        supermarket_color=supermarket.color,
        supermarket_emoji=supermarket.logo_emoji,
        name=product.name,
        brand=product.brand,
        image_url=image_url,
        url=buy_url,
        unit=product.unit,
        pack_label=pack_label,
        price=snapshot.price,
        unit_price=snapshot.unit_price,
        is_offer=snapshot.is_offer,
        previous_price=snapshot.previous_price,
        discount_pct=snapshot.discount_pct,
        scraped_at=snapshot.scraped_at,
    )


def category_out(category: Category) -> CategoryOut:
    return CategoryOut(slug=category.slug, label=category.label, icon=category.icon)


def min_price_by_category_and_supermarket(session: Session) -> dict[tuple[str, str], float]:
    """Para cada (categoría, supermercado), el precio más bajo entre el
    último snapshot de cada producto de esa categoría en ese supermercado.

    Usado tanto por el motor de ahorro (insights.py) como por la lista de
    la compra (shopping_list.py) como aproximación de "mejor precio
    disponible" para un tipo de producto genérico."""
    rows = session.exec(
        select(
            Product.category_slug,
            Product.supermarket_slug,
            Product.id,
            PriceSnapshot.price,
            PriceSnapshot.scraped_at,
        ).join(PriceSnapshot, PriceSnapshot.product_id == Product.id)
    ).all()

    latest_by_product: dict[int, tuple[float, object]] = {}
    meta_by_product: dict[int, tuple[str, str]] = {}
    for category_slug, supermarket_slug, product_id, price, scraped_at in rows:
        if category_slug is None:
            continue
        prev = latest_by_product.get(product_id)
        if prev is None or scraped_at > prev[1]:
            latest_by_product[product_id] = (price, scraped_at)
            meta_by_product[product_id] = (category_slug, supermarket_slug)

    best: dict[tuple[str, str], float] = {}
    for product_id, (price, _) in latest_by_product.items():
        key = meta_by_product[product_id]
        if key not in best or price < best[key]:
            best[key] = price
    return best


def find_similar_products(session: Session, product: Product) -> list[tuple[Product, PriceSnapshot]]:
    """El mismo tipo de producto y formato (misma categoría + misma
    cantidad/tamaño de envase, ver app/product_matching.py) en otros
    supermercados — lo que ve el usuario como "el mismo producto" al abrir
    la ficha de un producto (p.ej. media docena de huevos)."""
    if product.pack_qty is None or product.pack_unit is None or product.category_slug is None:
        return []

    category = CATEGORY_BY_SLUG.get(product.category_slug)
    search_terms = category.search_terms if category else ()

    pairs = latest_snapshot_per_product(session, category_slug=product.category_slug)
    best_by_supermarket: dict[str, tuple[Product, PriceSnapshot]] = {}
    for other, snapshot in pairs:
        if other.id == product.id or other.supermarket_slug == product.supermarket_slug:
            continue
        if other.pack_qty != product.pack_qty or other.pack_unit != product.pack_unit:
            continue
        if not is_plausible_match(product.name, other.name, search_terms):
            continue
        current = best_by_supermarket.get(other.supermarket_slug)
        if current is None or snapshot.price < current[1].price:
            best_by_supermarket[other.supermarket_slug] = (other, snapshot)

    return sorted(best_by_supermarket.values(), key=lambda ps: ps[1].price)
