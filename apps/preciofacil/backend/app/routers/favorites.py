from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..db import get_session
from ..models import Favorite
from ..schemas import FavoriteIn

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


def _list_slugs(session: Session, user_email: str) -> list[str]:
    rows = session.exec(select(Favorite).where(Favorite.user_email == user_email)).all()
    return [r.category_slug for r in rows]


@router.get("", response_model=list[str])
def list_favorites(user_email: str, session: Session = Depends(get_session)):
    return _list_slugs(session, user_email)


@router.post("", response_model=list[str])
def add_favorite(payload: FavoriteIn, session: Session = Depends(get_session)):
    existing = session.exec(
        select(Favorite).where(
            Favorite.user_email == payload.user_email,
            Favorite.category_slug == payload.category_slug,
        )
    ).first()
    if not existing:
        session.add(Favorite(user_email=payload.user_email, category_slug=payload.category_slug))
        session.commit()
    return _list_slugs(session, payload.user_email)


@router.delete("/{category_slug}", response_model=list[str])
def remove_favorite(category_slug: str, user_email: str, session: Session = Depends(get_session)):
    existing = session.exec(
        select(Favorite).where(
            Favorite.user_email == user_email, Favorite.category_slug == category_slug
        )
    ).first()
    if existing:
        session.delete(existing)
        session.commit()
    return _list_slugs(session, user_email)
