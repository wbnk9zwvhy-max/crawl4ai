from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Category, Supermarket
from ..queries import category_out, latest_snapshot_per_product, to_product_price_out
from ..schemas import CategoryComparisonOut

router = APIRouter(prefix="/api/compare", tags=["compare"])


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
