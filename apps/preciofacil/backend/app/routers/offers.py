from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..db import get_session
from ..models import Category, Supermarket
from ..queries import category_out, latest_snapshot_per_product, to_product_price_out
from ..schemas import CategoryComparisonOut

router = APIRouter(prefix="/api/offers", tags=["offers"])

TOP_N_PER_CATEGORY = 3


@router.get("/today", response_model=list[CategoryComparisonOut])
def offers_today(session: Session = Depends(get_session)):
    """Ofertas más destacadas del día, agrupadas por categoría de producto."""
    supermarkets = {s.slug: s for s in session.exec(select(Supermarket)).all()}
    categories = session.exec(select(Category).order_by(Category.label)).all()

    result: list[CategoryComparisonOut] = []
    for category in categories:
        pairs = latest_snapshot_per_product(session, category_slug=category.slug)
        offers = [
            (product, snapshot)
            for product, snapshot in pairs
            if snapshot.is_offer
        ]
        if not offers:
            continue
        offers.sort(key=lambda ps: ps[1].discount_pct or 0, reverse=True)
        offers = offers[:TOP_N_PER_CATEGORY]

        products_out = []
        for product, snapshot in offers:
            supermarket = supermarkets.get(product.supermarket_slug)
            if not supermarket:
                continue
            products_out.append(to_product_price_out(product, snapshot, supermarket))

        if not products_out:
            continue

        result.append(
            CategoryComparisonOut(
                category=category_out(category),
                cheapest_price=min(p.price for p in products_out),
                cheapest_supermarket=min(products_out, key=lambda p: p.price).supermarket_slug,
                products=products_out,
            )
        )

    result.sort(key=lambda c: max((p.discount_pct or 0) for p in c.products), reverse=True)
    return result
