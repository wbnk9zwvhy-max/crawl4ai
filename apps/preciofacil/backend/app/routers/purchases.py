from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..db import get_session
from ..insights import recompute_insights_for_user
from ..models import Purchase
from ..schemas import PurchaseIn, PurchaseOut

router = APIRouter(prefix="/api/purchases", tags=["purchases"])


@router.get("", response_model=list[PurchaseOut])
def list_purchases(user_email: str, session: Session = Depends(get_session)):
    return session.exec(
        select(Purchase).where(Purchase.user_email == user_email).order_by(Purchase.purchased_at.desc())
    ).all()


@router.post("", response_model=PurchaseOut)
def create_purchase(payload: PurchaseIn, session: Session = Depends(get_session)):
    purchase = Purchase(**payload.model_dump())
    session.add(purchase)
    session.commit()
    session.refresh(purchase)
    recompute_insights_for_user(session, payload.user_email)
    return purchase


@router.delete("/{purchase_id}")
def delete_purchase(purchase_id: int, user_email: str, session: Session = Depends(get_session)):
    purchase = session.get(Purchase, purchase_id)
    if purchase and purchase.user_email == user_email:
        session.delete(purchase)
        session.commit()
        recompute_insights_for_user(session, user_email)
    return {"ok": True}
