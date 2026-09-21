"""Sugerencias de recompra: a partir del historial de compras, detecta
categorías que el usuario compra con cierta regularidad (al menos dos
compras registradas) y, cuando ha pasado ya su intervalo medio entre
compras sin volver a registrarla, la sugiere para añadir a la lista de la
compra. No usa ningún modelo predictivo complejo: es una media móvil simple
sobre las fechas de compra, suficiente para un patrón como "sueles comprar
leche cada 2 semanas".
"""
from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from .models import Category, Purchase, ShoppingListItem

MIN_INTERVAL_DAYS = 3  # por debajo de esto no merece la pena sugerir (ruido)
DUE_THRESHOLD = 0.85  # sugerir cuando ya ha pasado el 85% del intervalo medio


def compute_suggestions(session: Session, user_email: str, today: date | None = None) -> list[dict]:
    today = today or date.today()

    purchases = session.exec(
        select(Purchase)
        .where(Purchase.user_email == user_email)
        .order_by(Purchase.purchased_at)
    ).all()
    if not purchases:
        return []

    already_listed = {
        i.category_slug
        for i in session.exec(
            select(ShoppingListItem).where(ShoppingListItem.user_email == user_email)
        ).all()
    }

    dates_by_category: dict[str, list[date]] = {}
    for p in purchases:
        dates_by_category.setdefault(p.category_slug, []).append(p.purchased_at)

    categories = {c.slug: c for c in session.exec(select(Category)).all()}

    suggestions: list[dict] = []
    for category_slug, dates in dates_by_category.items():
        if category_slug in already_listed or len(dates) < 2:
            continue
        dates = sorted(dates)
        span_days = (dates[-1] - dates[0]).days
        if span_days <= 0:
            continue
        avg_interval_days = span_days / (len(dates) - 1)
        if avg_interval_days < MIN_INTERVAL_DAYS:
            continue
        days_since_last = (today - dates[-1]).days
        if days_since_last < avg_interval_days * DUE_THRESHOLD:
            continue

        category = categories.get(category_slug)
        suggestions.append(
            {
                "category_slug": category_slug,
                "category_label": category.label if category else category_slug,
                "category_icon": category.icon if category else "🛒",
                "avg_interval_days": round(avg_interval_days),
                "days_since_last": days_since_last,
            }
        )

    suggestions.sort(key=lambda s: s["days_since_last"] - s["avg_interval_days"], reverse=True)
    return suggestions
