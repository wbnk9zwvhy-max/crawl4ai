from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..db import get_session
from ..schemas import SpendingOut
from ..spending import compute_spending

router = APIRouter(prefix="/api/spending", tags=["spending"])


@router.get("", response_model=SpendingOut)
def get_spending(user_email: str, session: Session = Depends(get_session)):
    return compute_spending(session, user_email)
