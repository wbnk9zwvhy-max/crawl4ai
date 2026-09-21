from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, select

from .models import Category, PriceSnapshot, Product, Supermarket
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
    return ProductPriceOut(
        product_id=product.id,
        supermarket_slug=supermarket.slug,
        supermarket_name=supermarket.name,
        supermarket_color=supermarket.color,
        supermarket_emoji=supermarket.logo_emoji,
        name=product.name,
        brand=product.brand,
        image_url=image_url,
        url=product.url,
        unit=product.unit,
        price=snapshot.price,
        unit_price=snapshot.unit_price,
        is_offer=snapshot.is_offer,
        previous_price=snapshot.previous_price,
        discount_pct=snapshot.discount_pct,
        scraped_at=snapshot.scraped_at,
    )


def category_out(category: Category) -> CategoryOut:
    return CategoryOut(slug=category.slug, label=category.label, icon=category.icon)
