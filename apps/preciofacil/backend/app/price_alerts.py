"""Alertas de precio (seguimiento de producto).

No hay infraestructura de notificaciones push en esta app (eso exigiría
claves VAPID, una suscripción por dispositivo y un servidor de envío aparte
— una pieza de infraestructura considerable). Lo que sí ofrecemos, y es lo
realmente útil sin esa pieza, es seguimiento en la propia app: el usuario
marca "avísame si baja" en un producto, guardamos el precio de ese momento,
y cada vez que abre la app le mostramos qué productos vigilados han bajado
desde entonces (o han tocado su precio más bajo registrado), con el ahorro
que representa.
"""
from __future__ import annotations

from sqlmodel import Session, select

from .models import PriceSnapshot, PriceWatch, Product, Supermarket


def watched_product_ids(session: Session, user_email: str) -> list[int]:
    rows = session.exec(select(PriceWatch).where(PriceWatch.user_email == user_email)).all()
    return [r.product_id for r in rows]


def add_watch(session: Session, user_email: str, product_id: int) -> None:
    existing = session.exec(
        select(PriceWatch).where(
            PriceWatch.user_email == user_email, PriceWatch.product_id == product_id
        )
    ).first()
    if existing:
        return
    snapshot = session.exec(
        select(PriceSnapshot)
        .where(PriceSnapshot.product_id == product_id)
        .order_by(PriceSnapshot.scraped_at.desc())
    ).first()
    if snapshot is None:
        return
    session.add(PriceWatch(user_email=user_email, product_id=product_id, watched_price=snapshot.price))
    session.commit()


def remove_watch(session: Session, user_email: str, product_id: int) -> None:
    existing = session.exec(
        select(PriceWatch).where(
            PriceWatch.user_email == user_email, PriceWatch.product_id == product_id
        )
    ).first()
    if existing:
        session.delete(existing)
        session.commit()


def compute_alerts(session: Session, user_email: str) -> list[dict]:
    watches = session.exec(select(PriceWatch).where(PriceWatch.user_email == user_email)).all()
    if not watches:
        return []

    supermarkets = {s.slug: s for s in session.exec(select(Supermarket)).all()}
    alerts: list[dict] = []
    for watch in watches:
        product = session.get(Product, watch.product_id)
        if product is None:
            continue
        latest = session.exec(
            select(PriceSnapshot)
            .where(PriceSnapshot.product_id == watch.product_id)
            .order_by(PriceSnapshot.scraped_at.desc())
        ).first()
        if latest is None:
            continue

        all_prices = session.exec(
            select(PriceSnapshot.price).where(PriceSnapshot.product_id == watch.product_id)
        ).all()
        historic_low = min(all_prices) if all_prices else latest.price
        is_historic_low = latest.price <= historic_low

        if latest.price >= watch.watched_price and not is_historic_low:
            continue  # no ha bajado desde que se empezó a seguir: nada que avisar

        supermarket = supermarkets.get(product.supermarket_slug)
        savings = round(watch.watched_price - latest.price, 2)
        alerts.append(
            {
                "watch_id": watch.id,
                "product_id": product.id,
                "product_name": product.name,
                "supermarket_slug": product.supermarket_slug,
                "supermarket_name": supermarket.name if supermarket else product.supermarket_slug,
                "supermarket_color": supermarket.color if supermarket else "#334155",
                "supermarket_emoji": supermarket.logo_emoji if supermarket else "🛒",
                "watched_price": watch.watched_price,
                "current_price": latest.price,
                "savings_amount": max(savings, 0.0),
                "is_historic_low": is_historic_low,
            }
        )
    return alerts
