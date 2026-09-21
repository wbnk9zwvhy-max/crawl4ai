from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Category, PriceSnapshot, Product, Supermarket
from ..queries import (
    category_out,
    find_similar_products,
    latest_snapshot_per_product,
    to_product_price_out,
)
from ..schemas import CategoryComparisonOut, PriceHistoryPointOut, ProductPriceOut

router = APIRouter(prefix="/api/compare", tags=["compare"])
products_router = APIRouter(prefix="/api/products", tags=["products"])


@products_router.get("/{product_id}/history", response_model=list[PriceHistoryPointOut])
def product_price_history(product_id: int, session: Session = Depends(get_session)):
    if session.get(Product, product_id) is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    snapshots = session.exec(
        select(PriceSnapshot)
        .where(PriceSnapshot.product_id == product_id)
        .order_by(PriceSnapshot.scraped_at)
    ).all()
    return [
        PriceHistoryPointOut(scraped_at=s.scraped_at, price=s.price, is_offer=s.is_offer) for s in snapshots
    ]


@products_router.get("/{product_id}/similar", response_model=list[ProductPriceOut])
def product_similar(product_id: int, session: Session = Depends(get_session)):
    """El mismo producto (misma categoría y formato: docena, 500 g, 1 L...)
    en otros supermercados, uno por cadena y ordenado de más barato a más
    caro — para la sección "también lo tienes en" de la ficha de producto."""
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    supermarkets = {s.slug: s for s in session.exec(select(Supermarket)).all()}
    pairs = find_similar_products(session, product)
    out = []
    for other, snapshot in pairs:
        supermarket = supermarkets.get(other.supermarket_slug)
        if supermarket:
            out.append(to_product_price_out(other, snapshot, supermarket))
    return out


@router.get("/{category_slug}", response_model=CategoryComparisonOut)
def compare_category(category_slug: str, session: Session = Depends(get_session)):
    category = session.get(Category, category_slug)
    if category is None:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    supermarkets = {s.slug: s for s in session.exec(select(Supermarket)).all()}
    pairs = latest_snapshot_per_product(session, category_slug=category_slug)

    products_out = []
    for product, snapshot in pairs:
        supermarket = supermarkets.get(product.supermarket_slug)
        if not supermarket:
            continue
        products_out.append(to_product_price_out(product, snapshot, supermarket))

    products_out.sort(key=lambda p: p.price)

    cheapest_price = products_out[0].price if products_out else None
    cheapest_supermarket = products_out[0].supermarket_slug if products_out else None

    return CategoryComparisonOut(
        category=category_out(category),
        cheapest_price=cheapest_price,
        cheapest_supermarket=cheapest_supermarket,
        products=products_out,
    )
