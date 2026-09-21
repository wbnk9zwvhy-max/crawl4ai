from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..db import get_session
from ..reorder_suggestions import compute_suggestions
from ..schemas import ReorderSuggestionOut

router = APIRouter(prefix="/api/reorder-suggestions", tags=["reorder"])


@router.get("", response_model=list[ReorderSuggestionOut])
def get_suggestions(user_email: str, session: Session = Depends(get_session)):
    return compute_suggestions(session, user_email)
