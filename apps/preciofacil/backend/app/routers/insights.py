from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..db import get_session
from ..insights import recompute_insights_for_user
from ..schemas import SavingsInsightOut

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("", response_model=list[SavingsInsightOut])
def get_insights(user_email: str, session: Session = Depends(get_session)):
    return recompute_insights_for_user(session, user_email)
