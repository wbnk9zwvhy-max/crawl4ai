from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..db import get_session
from ..models import Supermarket
from ..schemas import SupermarketOut

router = APIRouter(prefix="/api/supermarkets", tags=["supermarkets"])


@router.get("", response_model=list[SupermarketOut])
def list_supermarkets(session: Session = Depends(get_session)):
    return session.exec(select(Supermarket)).all()
