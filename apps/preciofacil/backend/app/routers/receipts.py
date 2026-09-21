from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from ..db import get_session
from ..insights import recompute_insights_for_user
from ..media import RECEIPTS_DIR, save_receipt_image
from ..models import Category, Purchase, Supermarket
from ..receipt_analysis import (
    ReceiptAnalysisError,
    analyze_receipt_bytes,
    category_slug_for_item_name,
    guess_supermarket_slug,
    media_type_for_extension,
)
from ..schemas import PurchaseOut, ReceiptConfirmIn, ReceiptDraftItemOut, ReceiptDraftOut

router = APIRouter(prefix="/api/receipts", tags=["receipts"])

_MAX_UPLOAD_BYTES = 15 * 1024 * 1024


@router.post("/analyze", response_model=ReceiptDraftOut)
async def analyze_receipt(file: UploadFile = File(...), session: Session = Depends(get_session)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="La imagen es demasiado grande (máximo 15 MB).")

    rel_path = save_receipt_image(content, file.content_type)
    ext = ("." + rel_path.rsplit(".", 1)[-1]) if "." in rel_path else ".jpg"
    media_type = media_type_for_extension(ext)

    try:
        extraction = analyze_receipt_bytes(content, media_type)
    except ReceiptAnalysisError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    supermarkets = session.exec(select(Supermarket)).all()
    names_by_slug = {s.slug: s.name for s in supermarkets}
    supermarket_slug = guess_supermarket_slug(extraction.supermarket_guess, names_by_slug)
    supermarket_name = names_by_slug.get(supermarket_slug) if supermarket_slug else None

    categories = {c.slug: c for c in session.exec(select(Category)).all()}
    items_out: list[ReceiptDraftItemOut] = []
    for item in extraction.items:
        category_slug = category_slug_for_item_name(item.name)
        category = categories.get(category_slug) if category_slug else None
        items_out.append(
            ReceiptDraftItemOut(
                name=item.name,
                unit_price=item.unit_price,
                quantity=item.quantity,
                category_slug=category_slug,
                category_label=category.label if category else None,
            )
        )

    warning = None
    if not items_out:
        warning = "No hemos podido leer ningún producto en esta foto. Prueba con más luz o menos inclinación."

    return ReceiptDraftOut(
        receipt_image_path=rel_path,
        supermarket_slug=supermarket_slug,
        supermarket_name=supermarket_name,
        purchase_date=extraction.purchase_date,
        total=extraction.total,
        items=items_out,
        warning=warning,
    )


@router.post("/confirm", response_model=list[PurchaseOut])
def confirm_receipt(payload: ReceiptConfirmIn, session: Session = Depends(get_session)):
    if not payload.items:
        raise HTTPException(status_code=400, detail="No hay productos que registrar.")

    # El path viene de nuestro propio /analyze; comprobamos que exista de
    # verdad en disco antes de guardarlo colgado de las compras.
    receipt_path = payload.receipt_image_path
    if receipt_path and not (RECEIPTS_DIR.parent / receipt_path).exists():
        receipt_path = None

    created: list[Purchase] = []
    for item in payload.items:
        purchase = Purchase(
            user_email=payload.user_email,
            category_slug=item.category_slug,
            supermarket_slug=payload.supermarket_slug,
            product_name=item.product_name,
            price=item.price,
            quantity=item.quantity,
            purchased_at=payload.purchased_at,
            receipt_image_path=receipt_path,
        )
        session.add(purchase)
        created.append(purchase)

    session.commit()
    for purchase in created:
        session.refresh(purchase)

    recompute_insights_for_user(session, payload.user_email)
    return created
