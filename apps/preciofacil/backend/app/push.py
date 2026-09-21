"""Notificaciones push (Web Push / VAPID) para las alertas de precio.

No hay servidor de notificaciones propio: usamos el servicio de push del
propio navegador del usuario (p.ej. FCM en Chrome) autenticado con un par de
claves VAPID del backend. El flujo es:

1. El usuario activa notificaciones en Ajustes -> el navegador crea una
   `PushSubscription` (endpoint + claves de cifrado) que guardamos aquí.
2. Cada vez que termina el scraping diario (o uno manual), recorremos las
   alertas de precio activas de cada usuario y, si alguna se ha disparado
   por primera vez o el precio ha bajado más desde el último aviso, le
   enviamos un push a todas sus suscripciones.

Sin `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY` configuradas, las notificaciones
push están desactivadas: el resto de la app (incluidas las alertas dentro
de la app, ver app/price_alerts.py) sigue funcionando igual.
"""
from __future__ import annotations

import json
import logging
import os
from collections import defaultdict

from pywebpush import WebPushException, webpush
from sqlmodel import Session, select

from .models import PriceWatch, PushSubscription
from .price_alerts import compute_alerts

logger = logging.getLogger(__name__)


class PushNotConfiguredError(RuntimeError):
    pass


def vapid_public_key() -> str:
    key = os.environ.get("VAPID_PUBLIC_KEY")
    if not key:
        raise PushNotConfiguredError(
            "Las notificaciones push no están activadas en este backend: falta la variable de "
            "entorno VAPID_PUBLIC_KEY. Genera un par de claves con "
            "`python -m scripts.generate_vapid_keys` y añádelas a la configuración del servidor."
        )
    return key


def _vapid_private_key() -> str:
    key = os.environ.get("VAPID_PRIVATE_KEY")
    if not key:
        raise PushNotConfiguredError(
            "Las notificaciones push no están activadas en este backend: falta la variable de "
            "entorno VAPID_PRIVATE_KEY. Genera un par de claves con "
            "`python -m scripts.generate_vapid_keys` y añádelas a la configuración del servidor."
        )
    return key


def _vapid_claims() -> dict:
    email = os.environ.get("VAPID_CLAIMS_EMAIL", "mailto:preciofacil@example.com")
    return {"sub": email}


def add_subscription(session: Session, user_email: str, endpoint: str, p256dh: str, auth: str) -> None:
    existing = session.exec(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    ).first()
    if existing:
        existing.user_email = user_email
        existing.p256dh = p256dh
        existing.auth = auth
        session.add(existing)
    else:
        session.add(
            PushSubscription(user_email=user_email, endpoint=endpoint, p256dh=p256dh, auth=auth)
        )
    session.commit()


def remove_subscription(session: Session, endpoint: str) -> None:
    existing = session.exec(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    ).first()
    if existing:
        session.delete(existing)
        session.commit()


def _send_to_subscription(session: Session, subscription: PushSubscription, payload: dict) -> None:
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=_vapid_private_key(),
            vapid_claims=dict(_vapid_claims()),
        )
    except WebPushException as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in (404, 410):
            # la suscripción ya no es válida (el usuario desinstaló la PWA,
            # borró datos del navegador...): la limpiamos.
            remove_subscription(session, subscription.endpoint)
        else:
            logger.warning("Error enviando push a %s: %s", subscription.endpoint, exc)


def send_push_to_user(session: Session, user_email: str, payload: dict) -> int:
    """Envía un push a todas las suscripciones activas de un usuario.
    Devuelve cuántas suscripciones recibieron el envío."""
    subscriptions = session.exec(
        select(PushSubscription).where(PushSubscription.user_email == user_email)
    ).all()
    for sub in subscriptions:
        _send_to_subscription(session, sub, payload)
    return len(subscriptions)


def notify_triggered_alerts_for_all_users(session: Session) -> dict:
    """Recorre todos los usuarios con suscripción push activa y les envía un
    aviso por cada alerta de precio recién disparada (o que ha bajado más
    desde el último aviso) que aún no se les había notificado. Se llama tras
    cada scraping (diario o manual), ver app/scheduler.py y app/main.py."""
    user_emails = {
        row[0] for row in session.exec(select(PushSubscription.user_email)).all()
    }
    summary: dict[str, int] = defaultdict(int)
    for user_email in user_emails:
        alerts = compute_alerts(session, user_email)
        watches_by_id = {
            w.id: w
            for w in session.exec(
                select(PriceWatch).where(PriceWatch.user_email == user_email)
            ).all()
        }
        to_notify = []
        for alert in alerts:
            watch = watches_by_id.get(alert["watch_id"])
            if watch is None:
                continue
            if watch.last_notified_price is not None and alert["current_price"] >= watch.last_notified_price:
                continue  # ya se avisó de este precio (o uno más bajo)
            to_notify.append((watch, alert))

        for watch, alert in to_notify:
            title = "📉 " + alert["product_name"]
            if alert["is_historic_low"]:
                body = f"Mínimo histórico en {alert['supermarket_name']}: {alert['current_price']:.2f}€"
            else:
                body = (
                    f"Ha bajado a {alert['current_price']:.2f}€ en {alert['supermarket_name']} "
                    f"(ahorras {alert['savings_amount']:.2f}€)"
                )
            sent = send_push_to_user(
                session, user_email, {"title": title, "body": body, "url": "/"}
            )
            if sent:
                watch.last_notified_price = alert["current_price"]
                session.add(watch)
                summary[user_email] += 1
        session.commit()
    return dict(summary)
