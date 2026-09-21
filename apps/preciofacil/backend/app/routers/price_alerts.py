from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..db import get_session
from ..price_alerts import add_watch, compute_alerts, remove_watch, watched_product_ids
from ..schemas import PriceAlertsStateOut, PriceWatchIn

router = APIRouter(prefix="/api/price-alerts", tags=["price-alerts"])


def _state(session: Session, user_email: str) -> PriceAlertsStateOut:
    return PriceAlertsStateOut(
        watched_product_ids=watched_product_ids(session, user_email),
        triggered=compute_alerts(session, user_email),
    )


@router.get("", response_model=PriceAlertsStateOut)
def get_alerts(user_email: str, session: Session = Depends(get_session)):
    return _state(session, user_email)


@router.post("", response_model=PriceAlertsStateOut)
def watch_product(payload: PriceWatchIn, session: Session = Depends(get_session)):
    add_watch(session, payload.user_email, payload.product_id)
    return _state(session, payload.user_email)


@router.delete("/{product_id}", response_model=PriceAlertsStateOut)
def unwatch_product(product_id: int, user_email: str, session: Session = Depends(get_session)):
    remove_watch(session, user_email, product_id)
    return _state(session, user_email)
