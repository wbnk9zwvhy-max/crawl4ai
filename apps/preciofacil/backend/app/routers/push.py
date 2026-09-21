from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..db import get_session
from ..push import (
    PushNotConfiguredError,
    add_subscription,
    remove_subscription,
    send_push_to_user,
    vapid_public_key,
)
from ..schemas import PushSubscriptionIn, PushUnsubscribeIn, VapidPublicKeyOut

router = APIRouter(prefix="/api/push", tags=["push"])


@router.get("/vapid-public-key", response_model=VapidPublicKeyOut)
def get_vapid_public_key():
    try:
        return VapidPublicKeyOut(public_key=vapid_public_key())
    except PushNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/subscribe")
def subscribe(payload: PushSubscriptionIn, session: Session = Depends(get_session)):
    add_subscription(session, payload.user_email, payload.endpoint, payload.keys.p256dh, payload.keys.auth)
    return {"status": "ok"}


@router.delete("/subscribe")
def unsubscribe(payload: PushUnsubscribeIn, session: Session = Depends(get_session)):
    remove_subscription(session, payload.endpoint)
    return {"status": "ok"}


@router.post("/test")
def send_test(user_email: str, session: Session = Depends(get_session)):
    try:
        vapid_public_key()
    except PushNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    sent = send_push_to_user(
        session,
        user_email,
        {
            "title": "PrecioFácil",
            "body": "Así se verán tus avisos de precio 🔔",
            "url": "/",
        },
    )
    if not sent:
        raise HTTPException(status_code=404, detail="No tienes ninguna suscripción push activa.")
    return {"status": "ok", "sent_to": sent}
