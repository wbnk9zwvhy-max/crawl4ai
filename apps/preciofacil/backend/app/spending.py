"""Panel de gasto: cuánto ha gastado el usuario mes a mes, y en qué
categorías y supermercados, a partir de su historial de compras
(`Purchase`, alimentado a mano o desde tickets escaneados).
"""
from __future__ import annotations

from collections import defaultdict

from sqlmodel import Session, select

from .models import Category, Purchase, Supermarket

MONTH_LABELS = [
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
]


def _month_key(purchase: Purchase) -> str:
    d = purchase.purchased_at
    return f"{d.year:04d}-{d.month:02d}"


def _month_label(month_key: str) -> str:
    year, month = month_key.split("-")
    return f"{MONTH_LABELS[int(month) - 1]} {year}"


def compute_spending(session: Session, user_email: str) -> dict:
    purchases = session.exec(select(Purchase).where(Purchase.user_email == user_email)).all()

    categories = {c.slug: c for c in session.exec(select(Category)).all()}
    supermarkets = {s.slug: s for s in session.exec(select(Supermarket)).all()}

    by_month: dict[str, float] = defaultdict(float)
    by_category: dict[str, float] = defaultdict(float)
    by_supermarket: dict[str, float] = defaultdict(float)

    for p in purchases:
        amount = p.price * p.quantity
        by_month[_month_key(p)] += amount
        by_category[p.category_slug] += amount
        by_supermarket[p.supermarket_slug] += amount

    monthly = [
        {"month": key, "label": _month_label(key), "total": round(total, 2)}
        for key, total in sorted(by_month.items())
    ]

    category_breakdown = [
        {
            "category_slug": slug,
            "category_label": categories[slug].label if slug in categories else slug,
            "category_icon": categories[slug].icon if slug in categories else "🛒",
            "total": round(total, 2),
        }
        for slug, total in sorted(by_category.items(), key=lambda kv: kv[1], reverse=True)
    ]

    supermarket_breakdown = [
        {
            "supermarket_slug": slug,
            "supermarket_name": supermarkets[slug].name if slug in supermarkets else slug,
            "supermarket_color": supermarkets[slug].color if slug in supermarkets else "#334155",
            "supermarket_emoji": supermarkets[slug].logo_emoji if slug in supermarkets else "🛒",
            "total": round(total, 2),
        }
        for slug, total in sorted(by_supermarket.items(), key=lambda kv: kv[1], reverse=True)
    ]

    total_all_time = round(sum(by_month.values()), 2)
    months_with_spend = len(by_month)
    avg_monthly = round(total_all_time / months_with_spend, 2) if months_with_spend else 0.0
    current_month_total = monthly[-1]["total"] if monthly else 0.0
    previous_month_total = monthly[-2]["total"] if len(monthly) > 1 else None

    return {
        "monthly": monthly,
        "by_category": category_breakdown,
        "by_supermarket": supermarket_breakdown,
        "total_all_time": total_all_time,
        "avg_monthly": avg_monthly,
        "current_month_total": current_month_total,
        "previous_month_total": previous_month_total,
    }
