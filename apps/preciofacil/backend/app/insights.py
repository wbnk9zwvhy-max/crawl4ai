"""Motor de recomendación de ahorro.

Compara el historial de compras registrado por el usuario con los precios
actuales (último snapshot) de todos los supermercados para la misma
categoría de producto, y genera mensajes del tipo:

    "Compraste fuet en Carrefour por 3.20€. En Mercadona lo tienen desde
    2.45€ · ahorrarías 0.75€ (23%) la próxima vez."

La comparación se hace a nivel de categoría canónica (no de producto exacto,
porque cada supermercado vende referencias distintas), usando el precio
mínimo vigente de esa categoría en cada supermercado como "mejor precio
disponible". Es una aproximación razonable para un producto genérico tipo
"pasta" o "leche" tal y como pidió el usuario.
"""
from __future__ import annotations

from sqlmodel import Session, select

from .models import Category, PriceSnapshot, Product, Purchase, SavingsInsight, Supermarket

MIN_SAVINGS_EUR = 0.05
MIN_SAVINGS_PCT = 3.0


def _latest_min_price_by_category_and_supermarket(session: Session) -> dict[tuple[str, str], float]:
    """Para cada (categoria, supermercado) devuelve el precio más bajo entre
    el último snapshot de cada producto de esa categoría en ese supermercado."""
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


def recompute_insights_for_user(session: Session, user_email: str) -> list[SavingsInsight]:
    session.exec(
        select(SavingsInsight).where(SavingsInsight.user_email == user_email)
    )
    old = session.exec(select(SavingsInsight).where(SavingsInsight.user_email == user_email)).all()
    for row in old:
        session.delete(row)
    session.commit()

    purchases = session.exec(
        select(Purchase).where(Purchase.user_email == user_email).order_by(Purchase.purchased_at.desc())
    ).all()
    if not purchases:
        return []

    best_price_by_key = _latest_min_price_by_category_and_supermarket(session)
    categories = {c.slug: c for c in session.exec(select(Category)).all()}
    supermarkets = {s.slug: s for s in session.exec(select(Supermarket)).all()}

    seen_categories: set[str] = set()
    insights: list[SavingsInsight] = []
    for purchase in purchases:
        if purchase.category_slug in seen_categories:
            continue  # solo el insight más reciente por categoría para no repetir
        seen_categories.add(purchase.category_slug)

        candidates = {
            supermarket_slug: price
            for (category_slug, supermarket_slug), price in best_price_by_key.items()
            if category_slug == purchase.category_slug
        }
        if not candidates:
            continue

        cheapest_slug = min(candidates, key=candidates.get)
        cheapest_price = candidates[cheapest_slug]
        if cheapest_slug == purchase.supermarket_slug:
            continue

        savings = round(purchase.price - cheapest_price, 2)
        if savings < MIN_SAVINGS_EUR:
            continue
        savings_pct = round(savings / purchase.price * 100, 1) if purchase.price else 0
        if savings_pct < MIN_SAVINGS_PCT:
            continue

        category = categories.get(purchase.category_slug)
        bought_name = supermarkets.get(purchase.supermarket_slug)
        cheap_name = supermarkets.get(cheapest_slug)
        label = category.label.lower() if category else purchase.category_slug
        message = (
            f"Compraste {label} en {bought_name.name if bought_name else purchase.supermarket_slug} "
            f"por {purchase.price:.2f}€. En {cheap_name.name if cheap_name else cheapest_slug} lo tienen "
            f"desde {cheapest_price:.2f}€ · ahorrarías {savings:.2f}€ ({savings_pct:.0f}%) la próxima vez."
        )
        insight = SavingsInsight(
            user_email=user_email,
            category_slug=purchase.category_slug,
            bought_supermarket_slug=purchase.supermarket_slug,
            bought_price=purchase.price,
            cheaper_supermarket_slug=cheapest_slug,
            cheaper_price=cheapest_price,
            savings_amount=savings,
            savings_pct=savings_pct,
            message=message,
        )
        session.add(insight)
        insights.append(insight)

    session.commit()
    for insight in insights:
        session.refresh(insight)
    return insights
