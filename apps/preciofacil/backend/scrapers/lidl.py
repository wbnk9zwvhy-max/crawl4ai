"""Scraper de Lidl España.

INVESTIGACIÓN REALIZADA (2026-09-20): Lidl España **no opera una tienda de
comestibles online con reparto a domicilio** (a diferencia de Mercadona).
``https://www.lidl.es`` es la tienda online de catálogo "no-food" de Lidl
(electrónica, bricolaje, hogar, moda, mascotas...), la misma plataforma que
en otros países usa el dominio ``lidl-shop.com``. No existe una API JSON
pública de catálogo de supermercado ni páginas de categoría de alimentación
con listado completo de productos (``/c/alimentacion/...`` redirige a la
página de folletos semanales, que es contenido editorial en PDF/imagen, no
datos estructurados).

Lo que SÍ existe y es real y en vivo: la tienda de catálogo tiene un motor de
búsqueda (``/q/search?q=<término>``) que renderiza en servidor (Nuxt/Vue SSR)
un payload JSON embebido (``<script id="__NUXT_DATA__">``) con hasta ~48
resultados por búsqueda. La mayoría son artículos no alimentarios (el propio
catálogo de Lidl), pero la búsqueda intercala, de forma no estrictamente
literal (usa relevancia semántica, no coincidencia exacta de texto), algunos
artículos de alimentación/bebida real ("Food"/"F+V") con precio, packaging
(peso/formato) e imagen reales — p. ej. buscando "queso" aparece
"Queso cheddar" a 1,25 € (200 g), buscando "cerveza" aparece "PERLENBACHER
Cerveza Pils" a 3,99 € (12x33 cl), buscando "pan" aparece "La Cestera Pan
rústico" a 0,79 € (450 g). Estos SÍ son precios reales de la web de Lidl en
el momento de ejecutar el scraper.

Verificado en vivo: 2026-09-20 (ver notes de la clase para el detalle de la
ejecución y sus limitaciones).

Gestión del código postal 46022 (Valencia):
Este catálogo no es una tienda de proximidad con reparto por código postal:
los precios que devuelve son precios de catálogo nacional (envío a
domicilio para todo el país), no varían por tienda/almacén como en
Mercadona. Por eso no hace falta resolver ningún almacén a partir del CP;
se documenta aquí en vez de simular un paso que la propia web no requiere.

Estrategia de fetch: NO existe una API JSON abierta reutilizable de forma
directa (la probamos con ``AsyncHTTPCrawlerStrategy``, la estrategia HTTP
ligera de Crawl4AI, pero Lidl envía una cabecera Content-Security-Policy de
más de 8 KB que hace que el cliente HTTP interno de Crawl4AI, basado en
aiohttp, falle con ``Got more than 8190 bytes when reading``). Así que
usamos la estrategia de navegador real de Crawl4AI (``AsyncWebCrawler`` con
Playwright/Chromium, que sí soporta esas cabeceras) para obtener el HTML
renderizado del buscador y extraemos el JSON SSR embebido (formato interno
tipo "devalue" de Nuxt: un array plano donde los valores de diccionarios y
listas son índices a otras posiciones del array) con un resolver casero.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Optional
from urllib.parse import quote

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

from .base import BaseSupermarketScraper, ScrapedProduct
from .taxonomy import CANONICAL_CATEGORIES, match_category_for_product_name

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.lidl.es/q/search?q={query}"

# Marcadores de "reactividad" que usa el payload SSR de Nuxt para envolver
# referencias a otra posición del array (equivalente a lo que en la librería
# `devalue` serían los tipos especiales).
_REACTIVE_MARKERS = {"ShallowReactive", "Reactive", "Ref", "ShallowRef", "EmptyRef"}

# Solo tomamos como máximo estos términos de búsqueda por categoría canónica
# para no disparar decenas de crawls de navegador por categoría: Lidl no
# tiene navegación por categoría de alimentación, así que cada término es una
# búsqueda de página completa con Chromium.
MAX_TERMS_PER_CATEGORY = 2

# Lidl etiqueta internamente algunos artículos de cosmética/higiene como
# category="Food" (dato real observado: "Agua micelar" sale como "Food" con
# packaging "400 ml"), lo que produce falsos positivos con el matching por
# texto de la taxonomía (p.ej. "agua micelar" contiene "agua "). Se filtran
# por nombre como último resguardo de calidad.
NON_FOOD_NAME_HINTS = (
    "micelar", "facial", "corporal", "maquillaje", "cosmetic", "crema",
    "champu", "champú", "gel de ducha", "gel de baño", "desodorante",
    "hidratante", "exfoliante", "mascarilla facial", "contorno de ojos",
)


def _resolve_nuxt_value(data: list, idx: int, depth: int = 0, seen: Optional[frozenset] = None) -> Any:
    """Resuelve recursivamente el payload __NUXT_DATA__ (array plano tipo
    'devalue' donde los valores de dict/list son índices a otras posiciones)."""
    if seen is None:
        seen = frozenset()
    if depth > 20 or idx in seen or idx < 0 or idx >= len(data):
        return None
    val = data[idx]
    next_seen = seen | {idx}
    if isinstance(val, dict):
        return {
            k: (_resolve_nuxt_value(data, v, depth + 1, next_seen) if isinstance(v, int) else v)
            for k, v in val.items()
        }
    if isinstance(val, list):
        if (
            len(val) == 2
            and isinstance(val[0], str)
            and val[0] in _REACTIVE_MARKERS
            and isinstance(val[1], int)
        ):
            return _resolve_nuxt_value(data, val[1], depth + 1, next_seen)
        return [
            (_resolve_nuxt_value(data, v, depth + 1, next_seen) if isinstance(v, int) else v)
            for v in val
        ]
    return val


def _extract_nuxt_data(html: str) -> Optional[list]:
    match = re.search(
        r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL
    )
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except (json.JSONDecodeError, ValueError):
        logger.warning("No se pudo parsear el payload __NUXT_DATA__ de Lidl")
        return None


def _iter_product_candidates(data: list):
    """Encuentra en el array plano las entradas dict que tienen pinta de
    tarjeta de producto (tienen 'price' y 'fullTitle') y las resuelve."""
    for i, entry in enumerate(data):
        if isinstance(entry, dict) and "price" in entry and "fullTitle" in entry:
            resolved = _resolve_nuxt_value(data, i)
            if isinstance(resolved, dict):
                yield resolved


class LidlScraper(BaseSupermarketScraper):
    slug = "lidl"
    display_name = "Lidl"
    color = "#0050AA"
    online_store_url = "https://www.lidl.es"
    live_verified = True
    notes = (
        "www.lidl.es es el catalogo NO-FOOD de Lidl (no hay reparto de "
        "supermercado a domicilio en España); no existe API JSON de "
        "catalogo de alimentacion ni paginas de categoria de comestibles "
        "navegables. Se usan los resultados reales de "
        "https://www.lidl.es/q/search?q=<termino> (renderizado en "
        "servidor, HTML obtenido con AsyncWebCrawler/Playwright de "
        "Crawl4AI porque la estrategia HTTP ligera de Crawl4AI, basada en "
        "aiohttp, falla con la cabecera Content-Security-Policy de Lidl "
        "de mas de 8KB) y se extrae el payload JSON SSR embebido "
        "(__NUXT_DATA__). Solo se conservan como productos reales los "
        "resultados cuya categoria interna de Lidl es 'Food' o 'F+V' y que "
        "tienen informacion de formato/peso (packaging), lo que descarta "
        "ruido como articulos de catalogo no alimentario, mas un filtro por "
        "nombre para descartar cosmetica/higiene mal etiquetada como 'Food' "
        "en los datos de Lidl (caso real detectado: 'Agua micelar' con "
        "categoria Food y packaging '400 ml', descartado por nombre). La "
        "cobertura es "
        "parcial e irregular porque el buscador de Lidl no hace matching "
        "literal del termino (es semantico/cross-sell), asi que algunas "
        "categorias canonicas (p.ej. leche, aceite de oliva) pueden no "
        "devolver ningun resultado en una ejecucion dada; lo que se "
        "devuelve son precios reales verificados en vivo, no inventados."
    )

    def __init__(self, postal_code: str = "46022"):
        # Documentado arriba: el catálogo de Lidl.es no varía por código
        # postal (precio de catálogo nacional), se guarda solo por
        # compatibilidad con la interfaz.
        self.postal_code = postal_code

    async def fetch_products(self) -> list[ScrapedProduct]:
        terms_by_category: dict[str, list[str]] = {
            category.slug: list(category.search_terms[:MAX_TERMS_PER_CATEGORY])
            for category in CANONICAL_CATEGORIES
        }
        all_terms = sorted({t for terms in terms_by_category.values() for t in terms})

        browser_config = BrowserConfig(headless=True, ignore_https_errors=True)
        results_by_term: dict[str, list[dict]] = {}
        async with AsyncWebCrawler(config=browser_config) as crawler:
            sem = asyncio.Semaphore(4)

            async def fetch_one(term: str) -> None:
                async with sem:
                    url = SEARCH_URL.format(query=quote(term))
                    try:
                        result = await crawler.arun(
                            url,
                            config=CrawlerRunConfig(
                                cache_mode=CacheMode.BYPASS,
                                wait_until="domcontentloaded",
                                page_timeout=60000,
                            ),
                        )
                    except Exception:
                        logger.warning("Fallo al descargar busqueda Lidl para %r", term)
                        return
                    if not result.success or not result.html:
                        logger.warning("Busqueda Lidl sin exito para %r", term)
                        return
                    data = _extract_nuxt_data(result.html)
                    if not data:
                        return
                    results_by_term[term] = list(_iter_product_candidates(data))

            await asyncio.gather(*(fetch_one(term) for term in all_terms))

        products: list[ScrapedProduct] = []
        seen_ids: set[str] = set()
        for category in CANONICAL_CATEGORIES:
            for term in terms_by_category[category.slug]:
                for item in results_by_term.get(term, []):
                    product = self._to_product(item, category.slug)
                    if product is None or product.external_id in seen_ids:
                        continue
                    seen_ids.add(product.external_id)
                    products.append(product)
        return products

    def _to_product(self, item: dict, hinted_category_slug: str) -> Optional[ScrapedProduct]:
        category_tag = item.get("category")
        if category_tag not in ("Food", "F+V"):
            return None
        price_info = item.get("price") or {}
        packaging = price_info.get("packaging") or {}
        if not packaging.get("text"):
            # Sin formato/peso: en la práctica descarta ítems mal
            # etiquetados como "Food" que no son alimentación real
            # (p.ej. cosmética).
            return None
        price = price_info.get("price")
        if not isinstance(price, (int, float)) or price <= 0:
            return None
        name = (item.get("fullTitle") or "").strip()
        if not name:
            return None
        name_lower = name.lower()
        if any(hint in name_lower for hint in NON_FOOD_NAME_HINTS):
            return None
        # Confirmamos con el matcher genérico de la taxonomía; si no
        # coincide con ninguna categoría (incluida la que motivó la
        # búsqueda) lo descartamos para evitar falsos positivos del motor
        # de búsqueda semántico de Lidl.
        matched_slug = match_category_for_product_name(name)
        if matched_slug is None:
            return None

        external_id = str(item.get("itemId") or item.get("erpNumber") or item.get("canonicalUrl"))
        previous_price = price_info.get("oldPrice")
        try:
            previous_price = float(previous_price) if previous_price else None
        except (TypeError, ValueError):
            previous_price = None
        is_offer = "discount" in price_info or previous_price is not None
        canonical_url = item.get("canonicalUrl") or item.get("canonicalPath")
        url = f"https://www.lidl.es{canonical_url}" if canonical_url and canonical_url.startswith("/") else canonical_url
        brand = None
        brand_info = item.get("brand")
        if isinstance(brand_info, dict):
            brand = brand_info.get("name")

        return ScrapedProduct(
            supermarket_slug=self.slug,
            external_id=external_id,
            name=name,
            category_slug=matched_slug,
            raw_category_name=category_tag,
            price=float(price),
            url=url,
            brand=brand,
            image_url=item.get("image"),
            unit=packaging.get("text"),
            is_offer=is_offer,
            previous_price=previous_price,
            discount_pct=self.compute_discount(float(price), previous_price),
        )
