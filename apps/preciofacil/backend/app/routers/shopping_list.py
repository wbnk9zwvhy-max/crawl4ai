from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..db import get_session
from ..shopping_list import add_item, compute_plan, remove_item
from ..schemas import ShoppingListItemIn, ShoppingListPlanOut

router = APIRouter(prefix="/api/shopping-list", tags=["shopping-list"])


@router.get("", response_model=ShoppingListPlanOut)
def get_plan(user_email: str, session: Session = Depends(get_session)):
    return compute_plan(session, user_email)


@router.post("", response_model=ShoppingListPlanOut)
def add_to_list(payload: ShoppingListItemIn, session: Session = Depends(get_session)):
    add_item(session, payload.user_email, payload.category_slug)
    return compute_plan(session, payload.user_email)


@router.delete("/{item_id}", response_model=ShoppingListPlanOut)
def remove_from_list(item_id: int, user_email: str, session: Session = Depends(get_session)):
    remove_item(session, user_email, item_id)
    return compute_plan(session, user_email)
