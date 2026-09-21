from __future__ import annotations

import asyncio
import logging

from sqlmodel import Session, select

from scrapers.base import ScrapedProduct
from scrapers.registry import REGISTRY
from scrapers.taxonomy import CANONICAL_CATEGORIES

from .db import engine
from .media import download_product_images
from .models import Category, PriceSnapshot, Product, Supermarket
from .product_matching import resolve_pack_for_item

logger = logging.getLogger(__name__)


def sync_static_tables(session: Session) -> None:
    for cat in CANONICAL_CATEGORIES:
        existing = session.get(Category, cat.slug)
        if existing is None:
            session.add(Category(slug=cat.slug, label=cat.label, icon=cat.icon))
    for entry in REGISTRY:
        existing = session.get(Supermarket, entry.slug)
        if existing is None:
            session.add(
                Supermarket(
                    slug=entry.slug,
                    name=entry.name,
                    color=entry.color,
                    logo_emoji=entry.logo_emoji,
                    online_store_url=entry.online_store_url,
                    live_verified=False,
                    notes=entry.notes,
                )
            )
    session.commit()


def _upsert_product(session: Session, item: ScrapedProduct) -> Product:
    pack = resolve_pack_for_item(item.name, item.unit, item.pack_qty, item.pack_unit)
    pack_qty, pack_unit = pack if pack else (None, None)

    stmt = select(Product).where(
        Product.supermarket_slug == item.supermarket_slug,
        Product.external_id == item.external_id,
    )
    product = session.exec(stmt).first()
    if product is None:
        product = Product(
            supermarket_slug=item.supermarket_slug,
            external_id=item.external_id,
            category_slug=item.category_slug,
            name=item.name,
            brand=item.brand,
            image_url=item.image_url,
            image_path=item.local_image_path,
            url=item.url,
            unit=item.unit,
            pack_qty=pack_qty,
            pack_unit=pack_unit,
        )
        session.add(product)
        session.flush()
    else:
        product.name = item.name
        product.category_slug = item.category_slug or product.category_slug
        product.image_url = item.image_url or product.image_url
        product.image_path = item.local_image_path or product.image_path
        product.url = item.url or product.url
        product.unit = item.unit or product.unit
        product.pack_qty = pack_qty if pack_qty is not None else product.pack_qty
        product.pack_unit = pack_unit if pack_unit is not None else product.pack_unit
    return product


def store_products(session: Session, products: list[ScrapedProduct]) -> int:
    count = 0
    for item in products:
        if not item.category_slug:
            continue
        product = _upsert_product(session, item)
        session.add(
            PriceSnapshot(
                product_id=product.id,
                price=item.price,
                unit_price=item.unit_price,
                is_offer=item.is_offer,
                previous_price=item.previous_price,
                discount_pct=item.discount_pct,
                scraped_at=item.scraped_at,
            )
        )
        count += 1
    session.commit()
    return count


async def run_daily_scrape() -> dict:
    """Ejecuta todos los scrapers disponibles y guarda un snapshot de precios.

    Pensado para lanzarse cada día a las 8:00 vía APScheduler (ver scheduler.py)
    o manualmente con ``python -m app.ingest``.
    """
    summary: dict[str, dict] = {}
    with Session(engine) as session:
        sync_static_tables(session)

        for entry in REGISTRY:
            if entry.scraper_cls is None:
                summary[entry.slug] = {"status": "sin_scraper", "productos": 0}
                continue
            scraper = entry.scraper_cls()
            try:
                products = await scraper.fetch_products()
            except Exception as exc:
                logger.exception("Fallo scrapeando %s", entry.slug)
                summary[entry.slug] = {"status": f"error: {exc}", "productos": 0}
                continue

            await download_product_images(products)
            imagenes = sum(1 for p in products if p.local_image_path)

            stored = store_products(session, products)
            live = len(products) > 0
            supermarket = session.get(Supermarket, entry.slug)
            if supermarket:
                supermarket.live_verified = live
                if getattr(scraper, "notes", None):
                    supermarket.notes = scraper.notes
                session.add(supermarket)
                session.commit()
            summary[entry.slug] = {
                "status": "ok" if live else "sin_datos",
                "productos": stored,
                "ofertas": sum(1 for p in products if p.is_offer),
                "imagenes": imagenes,
            }
    return summary


if __name__ == "__main__":
    from .db import init_db

    logging.basicConfig(level=logging.INFO)
    init_db()
    result = asyncio.run(run_daily_scrape())
    for slug, info in result.items():
        print(f"{slug}: {info}")
