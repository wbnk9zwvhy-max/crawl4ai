from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..db import get_session
from ..models import Category
from ..queries import category_out
from ..schemas import CategoryOut

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(session: Session = Depends(get_session)):
    categories = session.exec(select(Category).order_by(Category.label)).all()
    return [category_out(c) for c in categories]
