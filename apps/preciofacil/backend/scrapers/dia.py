"""Scraper de Día.

``www.dia.es`` es una SPA server-renderizada (framework Vike/Vue) sin API
JSON pública documentada de cara al cliente para listados de producto: las
llamadas XHR que dispara el navegador al navegar por una categoría son en
su mayoría de analítica (Google Analytics, DoubleClick) y de un
recolector de telemetría anti-bot (Akamai Bot Manager, endpoint ofuscado
tipo ``/j6mlq/...``), no del catálogo en sí.

Sin embargo, cada página de categoría (``https://www.dia.es/<categoria>/
<subcategoria>/c/<id>``) se sirve ya renderizada en el HTML e incluye un
``<script id="vike_pageContext">`` con el estado inicial completo de la
página en JSON (``INITIAL_STATE``), incluido ``l2.plp_items``: la lista de
productos de esa categoría con nombre, marca, precio, precio tachado de
oferta, porcentaje de descuento, precio por unidad de medida, imagen y URL
— exactamente los mismos datos que usa la SPA para pintar la grilla de
producto. Esto se descubrió primero inspeccionando con el navegador real
de Crawl4AI (``capture_network_requests=True``) qué llamadas hacía la app
al cargar una categoría (ninguna XHR de catálogo relevante) y después
comprobando, con una petición HTTP simple, que ese JSON ya viene en el
HTML servido por el propio servidor (SSR) sin necesidad de ejecutar
JavaScript ni de sesión/login. Por eso, igual que en ``mercadona.py``,
usamos la estrategia HTTP ligera de Crawl4AI (``AsyncHTTPCrawlerStrategy``)
para descargar esas páginas de categoría (no un navegador Playwright):
es más rápido y evita el bloqueo por bot-detection que sí dispara la
navegación con navegador real en la home de dia.es.

Verificado en vivo: 2026-09-20. Se ejecutó contra internet desde este
entorno y devolvió productos y precios reales (p.ej. Leche semidesnatada
Asturiana botella 1,5 L en oferta a 1,67€ frente a 1,79€ de PVP, Fuet/
salchichón y detergentes con precios de mercado reales).

Gestión del código postal 46022 (Valencia):
Se localizó en la home el selector "Elige código postal" y se investigó,
con Playwright, qué llamada de red dispara al introducir un código
postal; solo se observaron envíos al recolector de telemetría anti-bot
(Akamai), no una llamada JSON directa y estable a un endpoint de
tienda/zona que se pudiera reproducir de forma fiable sin sesión de
navegador real. Las peticiones anónimas (sin cookie de dirección)
devuelven en ``INITIAL_STATE.header.cartData.postal_code`` un código
postal por defecto (se observó "28041", Madrid) que Día asigna a
cualquier visitante sin ubicación guardada — es decir, el catálogo/precio
que ve un visitante anónimo es un listado nacional único para la venta
online, no segmentado por código postal a nivel de estas páginas de
categoría (se comprobó repitiendo peticiones y confirmando los mismos
precios). No se ha podido, por tanto, fijar explícitamente 46022 a nivel
de petición HTTP, pero los precios obtenidos son los mismos que vería
cualquier comprador online de Día, incluido uno en Valencia capital.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from crawl4ai.async_configs import HTTPCrawlerConfig
from crawl4ai.async_crawler_strategy import AsyncHTTPCrawlerStrategy

from .base import BaseSupermarketScraper, ScrapedProduct
from .taxonomy import match_category_for_product_name

logger = logging.getLogger(__name__)

SITE_BASE = "https://www.dia.es"
MAX_PAGES_PER_CATEGORY = 2

PAGE_CONTEXT_RE = re.compile(
    r'<script id="vike_pageContext"[^>]*>(.*?)</script>', re.S
)

UNIT_LABELS = {
    "KILO": "1 Kg",
    "LITRO": "1 L",
    "UNIDAD": "unidad",
}

# Mapeo manual (categoría canónica -> páginas de categoría reales de Día),
# construido a partir del sitemap.xml público del sitio, ya que Día no
# expone una búsqueda de texto libre server-rendered reutilizable.
CATEGORY_URLS: dict[str, list[str]] = {
    "pasta": [
        "/arroz-pastas-y-legumbres/macarrones-espaguetis-y-pastas-secas/c/L2044",
        "/arroz-pastas-y-legumbres/fideos/c/L2270",
        "/arroz-pastas-y-legumbres/noodles/c/L2273",
    ],
    "arroz": [
        "/arroz-pastas-y-legumbres/arroz/c/L2042",
    ],
    "leche": [
        "/huevos-leche-y-mantequilla/leche/c/L2051",
    ],
    "huevos": [
        "/huevos-leche-y-mantequilla/huevos/c/L2055",
    ],
    "aceite-oliva": [
        "/aceites-salsas-y-especias/aceites/c/L2046",
    ],
    "fuet-embutido": [
        "/charcuteria/fuet-y-salchichon/c/L2343",
        "/charcuteria/jamon-serrano/c/L2004",
        "/charcuteria/jamon-cocido/c/L2001",
        "/charcuteria/lomo-y-chorizo/c/L2005",
    ],
    "queso": [
        "/quesos/en-lonchas/c/L2205",
        "/quesos/tierno/c/L2346",
        "/quesos/curado/c/L2007",
        "/quesos/fresco/c/L2008",
        "/quesos/semicurado/c/L2345",
        "/quesos/rallado/c/L2347",
        "/quesos/untable-y-en-porciones/c/L2010",
        "/quesos/azul-y-de-cabra/c/L2009",
    ],
    "pan": [
        "/panaderia/pan-de-molde-y-especiales/c/L2069",
        "/panaderia/pan-recien-horneado/c/L2070",
    ],
    "cafe": [
        "/cafe-cacao-e-infusiones/cafe-soluble/c/L2278",
        "/cafe-cacao-e-infusiones/cafe-en-grano/c/L2279",
        "/cafe-cacao-e-infusiones/cafe-molido/c/L2277",
    ],
    "agua": [
        "/agua-y-refrescos/agua/c/L2107",
    ],
    "yogures": [
        "/yogures-y-postres/yogures-naturales-y-desnatados/c/L2079",
        "/yogures-y-postres/yogures-griegos/c/L2082",
        "/yogures-y-postres/yogures-de-sabores-y-frutas/c/L2081",
        "/yogures-y-postres/yogures-liquidos/c/L2248",
    ],
    "detergente-lavadora": [
        "/limpieza-y-hogar/detergentes/c/L2170",
    ],
    "papel-higienico": [
        "/limpieza-y-hogar/papel-higienico-cocina-y-servilletas/c/L2168",
    ],
    "lejia-limpieza": [
        "/limpieza-y-hogar/lejia-y-desinfectantes/c/L2161",
    ],
    "frutos-secos-snacks": [
        "/aperitivos-y-frutos-secos/frutos-secos/c/L2097",
        "/aperitivos-y-frutos-secos/patatas-fritas/c/L2098",
        "/aperitivos-y-frutos-secos/mix-de-frutos-secos/c/L2283",
    ],
    "cerveza": [
        "/cervezas-vinos-y-licores/cervezas/c/L2115",
        "/cervezas-vinos-y-licores/cervezas-sin-alcohol/c/L2118",
        "/cervezas-vinos-y-licores/packs-de-cervezas/c/L2293",
    ],
}


class DiaScraper(BaseSupermarketScraper):
    slug = "dia"
    display_name = "Día"
    color = "#E30613"
    online_store_url = "https://www.dia.es"
    postal_code = "46022"
    live_verified = True
    notes = (
        "HTML server-renderizado de las páginas de categoría de dia.es, "
        "con el JSON de productos ya embebido en <script id=vike_pageContext> "
        "(INITIAL_STATE.l2.plp_items). No se encontró una API JSON de "
        "catálogo aparte reutilizable por el cliente; el propio HTML "
        "renderizado en servidor hace de 'API'. Precios verificados en vivo."
    )

    def __init__(self, postal_code: str = "46022"):
        self.postal_code = postal_code

    async def fetch_products(self) -> list[ScrapedProduct]:
        jobs: list[tuple[str, str]] = [
            (slug, path)
            for slug, paths in CATEGORY_URLS.items()
            for path in paths
        ]

        strategy = AsyncHTTPCrawlerStrategy(
            browser_config=HTTPCrawlerConfig(
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "es-ES,es;q=0.9",
                },
            )
        )
        products_by_id: dict[str, ScrapedProduct] = {}
        async with AsyncWebCrawler(crawler_strategy=strategy) as crawler:
            # Un grado de concurrencia bajo evita el bloqueo por
            # bot-detection (Akamai) que se observó al lanzar muchas
            # peticiones HTTP en paralelo contra dia.es.
            sem = asyncio.Semaphore(2)

            async def fetch_category(assigned_slug: str, path: str) -> None:
                async with sem:
                    total_pages = 1
                    for page_number in range(1, MAX_PAGES_PER_CATEGORY + 1):
                        if page_number > total_pages:
                            break
                        url = f"{SITE_BASE}{path}"
                        if page_number > 1:
                            url += f"?page={page_number}"
                        result = await crawler.arun(url, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
                        if not result.success:
                            logger.warning("Fallo al descargar categoría Día %s (pag %s)", path, page_number)
                            return
                        state = self._extract_initial_state(result.html)
                        if state is None:
                            logger.warning("No se encontró vike_pageContext para %s", url)
                            return
                        pagination = (state.get("pagination") or {}).get("pagination", {})
                        total_pages = pagination.get("total_pages", 1) or 1
                        items = (state.get("l2") or {}).get("plp_items", [])
                        for raw in items:
                            product = self._parse_product(raw, assigned_slug)
                            if product is not None:
                                products_by_id[product.external_id] = product

            await asyncio.gather(*(fetch_category(slug, path) for slug, path in jobs))
        return list(products_by_id.values())

    @staticmethod
    def _extract_initial_state(html: str) -> dict | None:
        match = PAGE_CONTEXT_RE.search(html or "")
        if not match:
            return None
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
        return data.get("INITIAL_STATE")

    def _parse_product(self, raw: dict, assigned_slug: str) -> ScrapedProduct | None:
        name = (raw.get("display_name") or "").strip()
        if not name:
            return None
        prices = raw.get("prices")
        if not prices:
            return None
        try:
            price = float(prices["price"])
        except (KeyError, TypeError, ValueError):
            return None
        if price <= 0:
            return None

        previous_price = None
        strikethrough = prices.get("strikethrough_price")
        if strikethrough is not None:
            try:
                strikethrough = float(strikethrough)
            except (TypeError, ValueError):
                strikethrough = None
            if strikethrough is not None and strikethrough > price:
                previous_price = strikethrough

        try:
            unit_price = float(prices["price_per_unit"]) if prices.get("price_per_unit") is not None else None
        except (TypeError, ValueError):
            unit_price = None

        measure_unit = prices.get("measure_unit")
        unit = UNIT_LABELS.get(measure_unit, measure_unit)

        category_slug = match_category_for_product_name(name) or assigned_slug

        product_url = raw.get("url") or ""
        url_parts = [p for p in product_url.split("/") if p]
        raw_category_name = url_parts[1].replace("-", " ") if len(url_parts) > 1 else assigned_slug

        image = raw.get("image")
        image_url = f"{SITE_BASE}{image}" if image and image.startswith("/") else image

        url = f"{SITE_BASE}{product_url}" if product_url.startswith("/") else (product_url or None)

        external_id = str(raw.get("object_id") or raw.get("sku_id") or "")
        if not external_id:
            return None

        is_offer = bool(previous_price) or bool(prices.get("is_promo_price")) or bool(prices.get("discount_percentage"))

        return ScrapedProduct(
            supermarket_slug=self.slug,
            external_id=external_id,
            name=name,
            category_slug=category_slug,
            raw_category_name=raw_category_name,
            price=round(price, 2),
            url=url,
            brand=raw.get("brand"),
            image_url=image_url,
            unit_price=round(unit_price, 2) if unit_price is not None else None,
            unit=unit,
            is_offer=is_offer,
            previous_price=previous_price,
            discount_pct=self.compute_discount(price, previous_price),
        )
