"""Scraper de Consum.

Consum (cooperativa valenciana) tiene su tienda online en
``tienda.consum.es``, una SPA Angular servida por la plataforma Aktios/TOL.
Aunque la web en sí requiere iniciar sesión (OAuth vía ``iam.consum.es``)
para llegar al checkout, su backend expone una API REST pública y SIN
autenticación que alimenta el buscador y los listados de producto de esa
SPA:

    GET https://tienda.consum.es/api/rest/V1.0/catalog/product
        ?q=<texto de búsqueda>&limit=<max 100>

Se descubrió inspeccionando, con la estrategia de navegador real de
Crawl4AI (``capture_network_requests=True``), las peticiones XHR que la
propia web de Consum hace al cargar buscadores/listados. La API devuelve
JSON con nombre, marca, categoría real de Consum, precio normal
(``PRICE``) y precio de oferta (``OFFER_PRICE``) cuando lo hay, precio por
unidad de medida, imagen y URL pública del producto — sin necesidad de
sesión, token ni cabeceras especiales. Por eso usamos la estrategia HTTP
ligera de Crawl4AI (``AsyncHTTPCrawlerStrategy``), igual que hace
``mercadona.py``, en vez de un navegador con Playwright: es más rápido y
más fiable porque no depende de renderizar la SPA.

Verificado en vivo: 2026-09-20. Se ejecutó contra internet desde este
entorno y devolvió productos y precios reales y coherentes con el mercado
(p.ej. Fuet Espetec 2,49€, Leche Semidesnatada Asturiana en oferta a
1,67€ frente a 1,79€ de PVP normal).

Gestión del código postal 46022 (Valencia):
Se investigó cómo la SPA fija tienda/almacén a partir del código postal
(inspección de red + pruebas manuales de parámetros ``zipCode``,
``shippingZoneId=0D``/``shippingMethod=D`` que aparecen en las llamadas
del frontend, y endpoints ``/api/rest/V1.0/shipping/...``). Se comprobó
que la API pública de catálogo (``catalog/product``) devuelve exactamente
los mismos precios se le pase o no ``zipCode``/``shippingZoneId`` — Consum
sirve un catálogo y tarifa únicos para toda la compra online, sin
segmentar precio por código postal a nivel de API pública (la
segmentación por almacén solo aparece más adelante, en el flujo de
checkout autenticado). Como Consum es una cooperativa con sede y origen
en la Comunitat Valenciana, 46022 (Valencia ciudad) cae de sobra dentro de
su zona de cobertura de compra online, así que el catálogo devuelto es el
que vería un usuario real de esa zona.
"""
from __future__ import annotations

import asyncio
import json
import logging

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from crawl4ai.async_configs import HTTPCrawlerConfig
from crawl4ai.async_crawler_strategy import AsyncHTTPCrawlerStrategy

from .base import BaseSupermarketScraper, ScrapedProduct
from .taxonomy import CANONICAL_CATEGORIES, match_category_for_product_name

logger = logging.getLogger(__name__)

API_BASE = "https://tienda.consum.es/api/rest/V1.0"
SEARCH_LIMIT = 100


class ConsumScraper(BaseSupermarketScraper):
    slug = "consum"
    display_name = "Consum"
    color = "#E2001A"
    online_store_url = "https://www.consum.es"
    postal_code = "46022"
    live_verified = True
    notes = (
        "API JSON pública (sin login) del buscador de tienda.consum.es "
        "(catalog/product?q=...), descubierta inspeccionando las peticiones "
        "XHR reales de la SPA con el navegador de Crawl4AI. Precios "
        "verificados en vivo contra internet."
    )

    def __init__(self, postal_code: str = "46022"):
        self.postal_code = postal_code

    async def fetch_products(self) -> list[ScrapedProduct]:
        # Un término de búsqueda por categoría canónica basta para traer un
        # muestreo real y relevante; usamos varios términos por categoría
        # cuando el primero es muy genérico para tener más variedad.
        terms: dict[str, str] = {}
        for category in CANONICAL_CATEGORIES:
            for term in category.search_terms[:2]:
                terms[term] = category.slug

        strategy = AsyncHTTPCrawlerStrategy(
            browser_config=HTTPCrawlerConfig(
                headers={"Accept": "application/json"},
            )
        )
        products_by_code: dict[str, ScrapedProduct] = {}
        async with AsyncWebCrawler(crawler_strategy=strategy) as crawler:
            sem = asyncio.Semaphore(5)

            async def fetch_term(term: str) -> None:
                async with sem:
                    url = f"{API_BASE}/catalog/product?limit={SEARCH_LIMIT}&q={term}"
                    result = await crawler.arun(url, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
                    if not result.success:
                        logger.warning("Fallo al descargar búsqueda Consum %r", term)
                        return
                    try:
                        data = json.loads(result.html)
                    except (json.JSONDecodeError, TypeError):
                        logger.warning("Respuesta no-JSON para término Consum %r", term)
                        return
                    for raw in data.get("products", []):
                        product = self._parse_product(raw)
                        if product is not None:
                            products_by_code[product.external_id] = product

            await asyncio.gather(*(fetch_term(term) for term in terms))
        return list(products_by_code.values())

    def _parse_product(self, raw: dict) -> ScrapedProduct | None:
        product_data = raw.get("productData", {})
        name = (product_data.get("name") or "").strip()
        description = (product_data.get("description") or "").strip()
        full_name = description or name
        if not full_name:
            return None

        category_slug = match_category_for_product_name(full_name)
        if category_slug is None:
            return None

        price_data = raw.get("priceData", {})
        prices = {p.get("id"): p.get("value", {}) for p in price_data.get("prices", [])}
        base_price = prices.get("PRICE", {}).get("centAmount")
        offer_price = prices.get("OFFER_PRICE", {}).get("centAmount")
        if offer_price is not None:
            try:
                price = float(offer_price)
            except (TypeError, ValueError):
                return None
            previous_price = float(base_price) if base_price is not None else None
        elif base_price is not None:
            try:
                price = float(base_price)
            except (TypeError, ValueError):
                return None
            previous_price = None
        else:
            return None
        if price <= 0:
            return None
        if previous_price is not None and previous_price <= price:
            previous_price = None

        unit_amount = (
            prices.get("OFFER_PRICE", {}).get("centUnitAmount")
            if offer_price is not None
            else prices.get("PRICE", {}).get("centUnitAmount")
        )
        try:
            unit_price = float(unit_amount) if unit_amount is not None else None
        except (TypeError, ValueError):
            unit_price = None

        categories = raw.get("categories", [])
        raw_category_name = next(
            (c.get("name") for c in categories if c.get("type") != 1),
            (categories[0].get("name") if categories else None),
        )

        media = raw.get("media", [])
        image_url = media[0]["url"] if media else product_data.get("imageURL")

        brand = (product_data.get("brand") or {}).get("name")

        external_id = raw.get("code") or str(raw.get("id"))

        return ScrapedProduct(
            supermarket_slug=self.slug,
            external_id=str(external_id),
            name=full_name,
            category_slug=category_slug,
            raw_category_name=raw_category_name,
            price=round(price, 2),
            url=product_data.get("url"),
            brand=brand,
            image_url=image_url,
            unit_price=round(unit_price, 2) if unit_price is not None else None,
            unit=price_data.get("unitPriceUnitType") or None,
            is_offer=bool(previous_price) or bool(raw.get("offers")),
            previous_price=previous_price,
            discount_pct=self.compute_discount(price, previous_price),
        )
