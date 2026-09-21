"""Scraper de Mercadona.

Mercadona expone una API JSON pública y sin autenticación que alimenta su
propia PWA de compra online (tienda.mercadona.es). Es la fuente MÁS fiable
de las seis: no requiere renderizar JavaScript ni simular un navegador,
así que la usamos vía la estrategia HTTP ligera de Crawl4AI
(``AsyncHTTPCrawlerStrategy``), mucho más rápida que un crawl con navegador.

Verificado en vivo: 2026-09-20, devuelve precios reales y actualizados.

Gestión del código postal 46022 (Valencia):
Mercadona resuelve la tienda/almacén a partir de un código de almacén
("wh") en vez de aceptar el código postal directamente en la API de
catálogo. 46022 (ciudad de Valencia) cae dentro del almacén "vlc1"
(Valencia), que es el que usan las tiendas de Mercadona en la propia
ciudad de Valencia. Ese código se obtiene normalmente resolviendo el CP
contra ``https://tienda.mercadona.es/api/postal-codes/46022/`` (devuelve
el warehouse asignado); lo dejamos fijo a "vlc1" con un pequeño resolver
por si en el futuro se quiere soportar otros códigos postales.
"""
from __future__ import annotations

import asyncio
import json
import logging

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from crawl4ai.async_configs import HTTPCrawlerConfig
from crawl4ai.async_crawler_strategy import AsyncHTTPCrawlerStrategy

from .base import BaseSupermarketScraper, ScrapedProduct
from .taxonomy import CANONICAL_CATEGORIES

logger = logging.getLogger(__name__)

API_BASE = "https://tienda.mercadona.es/api"

#: Mercadona no escribe la cantidad de envase en el nombre del producto
#: ("Huevos", "Fideo cabello de ángel Hacendado"...), así que la sacamos
#: directamente de price_instructions: "unit_size" es la cantidad en el
#: formato "size_format" (p.ej. unit_size=24, size_format="ud" -> docena y
#: media de huevos = 24 unidades; unit_size=0.5, size_format="kg" -> 500 g).
_SIZE_FORMAT_TO_PACK_UNIT = {"ud": "ud", "kg": "g", "l": "ml"}
_SIZE_FORMAT_MULTIPLIER = {"ud": 1, "kg": 1000, "l": 1000}


def _pack_qty_from_price_info(price_info: dict) -> float | None:
    size_format = price_info.get("size_format")
    unit_size = price_info.get("unit_size")
    if size_format not in _SIZE_FORMAT_MULTIPLIER or not isinstance(unit_size, (int, float)):
        return None
    return round(unit_size * _SIZE_FORMAT_MULTIPLIER[size_format], 2)


def _pack_unit_from_price_info(price_info: dict) -> str | None:
    return _SIZE_FORMAT_TO_PACK_UNIT.get(price_info.get("size_format"))


async def resolve_warehouse(postal_code: str) -> str:
    """Resuelve el almacén de Mercadona asociado a un código postal."""
    strategy = AsyncHTTPCrawlerStrategy(browser_config=HTTPCrawlerConfig())
    try:
        async with AsyncWebCrawler(crawler_strategy=strategy) as crawler:
            result = await crawler.arun(
                f"{API_BASE}/postal-codes/{postal_code}/",
                config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS),
            )
            if result.success:
                data = json.loads(result.html)
                wh = data.get("wh")
                if wh:
                    return wh
    except Exception:  # pragma: no cover - best effort, cae al fallback
        logger.warning("No se pudo resolver warehouse para CP %s, usando vlc1", postal_code)
    return "vlc1"


class MercadonaScraper(BaseSupermarketScraper):
    slug = "mercadona"
    display_name = "Mercadona"
    color = "#00A19A"
    online_store_url = "https://tienda.mercadona.es"
    live_verified = True
    notes = "API JSON pública oficial de la tienda online de Mercadona."

    def __init__(self, postal_code: str = "46022"):
        self.postal_code = postal_code
        self._warehouse: str | None = None

    async def fetch_products(self) -> list[ScrapedProduct]:
        self._warehouse = await resolve_warehouse(self.postal_code)
        category_ids = sorted({
            cid
            for category in CANONICAL_CATEGORIES
            for cid in category.mercadona_category_ids
        })
        strategy = AsyncHTTPCrawlerStrategy(browser_config=HTTPCrawlerConfig())
        products: list[ScrapedProduct] = []
        async with AsyncWebCrawler(crawler_strategy=strategy) as crawler:
            sem = asyncio.Semaphore(6)

            async def fetch_one(cat_id: int) -> None:
                async with sem:
                    url = f"{API_BASE}/categories/{cat_id}/?lang=es&wh={self._warehouse}"
                    result = await crawler.arun(url, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
                    if not result.success:
                        logger.warning("Fallo al descargar categoría Mercadona %s", cat_id)
                        return
                    data = json.loads(result.html)
                    products.extend(self._parse_category(data))

            await asyncio.gather(*(fetch_one(cid) for cid in category_ids))
        return products

    def _parse_category(self, data: dict) -> list[ScrapedProduct]:
        canonical_slug = next(
            (
                c.slug
                for c in CANONICAL_CATEGORIES
                if data.get("id") in c.mercadona_category_ids
            ),
            None,
        )
        out: list[ScrapedProduct] = []
        for subcategory in data.get("categories", []):
            for item in subcategory.get("products", []):
                price_info = item.get("price_instructions", {})
                try:
                    price = float(price_info.get("unit_price") or price_info.get("bulk_price") or 0)
                except (TypeError, ValueError):
                    continue
                if price <= 0:
                    continue
                previous_price = None
                if price_info.get("previous_unit_price"):
                    try:
                        previous_price = float(price_info["previous_unit_price"])
                    except (TypeError, ValueError):
                        previous_price = None
                is_offer = bool(price_info.get("price_decreased")) or previous_price is not None
                out.append(
                    ScrapedProduct(
                        supermarket_slug=self.slug,
                        external_id=str(item["id"]),
                        name=item.get("display_name", "").strip(),
                        category_slug=canonical_slug,
                        raw_category_name=subcategory.get("name"),
                        price=price,
                        url=item.get("share_url"),
                        image_url=item.get("thumbnail"),
                        unit=price_info.get("size_format"),
                        unit_price=float(price_info["bulk_price"]) if price_info.get("bulk_price") else None,
                        pack_qty=_pack_qty_from_price_info(price_info),
                        pack_unit=_pack_unit_from_price_info(price_info),
                        is_offer=is_offer,
                        previous_price=previous_price,
                        discount_pct=self.compute_discount(price, previous_price),
                    )
                )
        return out
