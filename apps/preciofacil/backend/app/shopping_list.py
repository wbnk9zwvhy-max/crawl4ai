"""Lista de la compra con reparto óptimo entre supermercados.

El usuario añade tipos de producto genéricos (categorías canónicas, igual
que en el comparador: "pasta", "leche", "fuet"...). Para cada uno buscamos
el supermercado con el precio vigente más bajo (misma aproximación que el
motor de ahorro, ver insights.py) y calculamos:

- El coste "óptimo": ir a comprar cada producto donde está más barato
  (varias paradas).
- El coste de la mejor "única parada": el supermercado más barato en el
  que se puede comprar TODA la lista, sumando lo que cuesta cada item ahí.
- El ahorro de repartir la compra frente a comprarlo todo junto.
"""
from __future__ import annotations

from sqlmodel import Session, select

from .models import Category, ShoppingListItem, Supermarket
from .queries import min_price_by_category_and_supermarket


def list_items(session: Session, user_email: str) -> list[ShoppingListItem]:
    return session.exec(
        select(ShoppingListItem)
        .where(ShoppingListItem.user_email == user_email)
        .order_by(ShoppingListItem.created_at)
    ).all()


def add_item(session: Session, user_email: str, category_slug: str) -> ShoppingListItem:
    existing = session.exec(
        select(ShoppingListItem).where(
            ShoppingListItem.user_email == user_email,
            ShoppingListItem.category_slug == category_slug,
        )
    ).first()
    if existing:
        return existing
    item = ShoppingListItem(user_email=user_email, category_slug=category_slug)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def remove_item(session: Session, user_email: str, item_id: int) -> None:
    item = session.get(ShoppingListItem, item_id)
    if item and item.user_email == user_email:
        session.delete(item)
        session.commit()


def compute_plan(session: Session, user_email: str) -> dict:
    items = list_items(session, user_email)
    categories = {c.slug: c for c in session.exec(select(Category)).all()}
    supermarkets = {s.slug: s for s in session.exec(select(Supermarket)).all()}
    best_price_by_key = min_price_by_category_and_supermarket(session)

    items_out = []
    # precio de cada item en cada supermercado que lo tiene, para calcular
    # después el total de "comprarlo todo en un único súper"
    price_matrix: dict[str, dict[str, float]] = {}

    for item in items:
        category = categories.get(item.category_slug)
        candidates = {
            supermarket_slug: price
            for (category_slug, supermarket_slug), price in best_price_by_key.items()
            if category_slug == item.category_slug
        }
        price_matrix[item.category_slug] = candidates

        best_slug = min(candidates, key=candidates.get) if candidates else None
        best_price = candidates[best_slug] if best_slug else None
        best_supermarket = supermarkets.get(best_slug) if best_slug else None

        items_out.append(
            {
                "id": item.id,
                "category_slug": item.category_slug,
                "category_label": category.label if category else item.category_slug,
                "category_icon": category.icon if category else "🛒",
                "best_supermarket_slug": best_slug,
                "best_supermarket_name": best_supermarket.name if best_supermarket else None,
                "best_supermarket_color": best_supermarket.color if best_supermarket else None,
                "best_supermarket_emoji": best_supermarket.logo_emoji if best_supermarket else None,
                "best_price": best_price,
            }
        )

    priced_items = [i for i in items_out if i["best_price"] is not None]
    total_optimal = round(sum(i["best_price"] for i in priced_items), 2) if priced_items else 0.0

    # Súper de "parada única": el que tiene TODOS los items de la lista con
    # precio conocido, con el menor coste total.
    single_stop_slug = None
    single_stop_total = None
    if priced_items:
        for slug in supermarkets:
            totals = [price_matrix[i["category_slug"]].get(slug) for i in priced_items]
            if all(t is not None for t in totals):
                total = round(sum(totals), 2)
                if single_stop_total is None or total < single_stop_total:
                    single_stop_total = total
                    single_stop_slug = slug

    savings_amount = None
    savings_pct = None
    if single_stop_total is not None and single_stop_total > total_optimal:
        savings_amount = round(single_stop_total - total_optimal, 2)
        savings_pct = round(savings_amount / single_stop_total * 100, 1) if single_stop_total else 0.0

    single_stop_supermarket = supermarkets.get(single_stop_slug) if single_stop_slug else None

    return {
        "items": items_out,
        "total_optimal": total_optimal,
        "single_stop_supermarket_slug": single_stop_slug,
        "single_stop_supermarket_name": single_stop_supermarket.name if single_stop_supermarket else None,
        "single_stop_total": single_stop_total,
        "savings_amount": savings_amount,
        "savings_pct": savings_pct,
    }
