"""Scraper de ALDI España.

INVESTIGACIÓN REALIZADA (2026-09-20): a diferencia de Lidl España (ver
``lidl.py``), ALDI España **sí publica un catálogo completo de supermercado**
en ``https://www.aldi.es``, con una página propia por producto
(``/producto/<slug>-<id>.html``, ~2100 productos según
``https://www.aldi.es/sitemaps/.aldi-nord-sitemap-products.xml``) y páginas
de categoría navegables (``/productos/<categoria>/<subcategoria>.html``) que
listan todos los productos de esa categoría.

La web está construida con Next.js sobre contenido de Magnolia CMS, y usa
Algolia como motor de búsqueda/listado de producto. Cada página de categoría
incluye en el HTML servido por el servidor (sin necesidad de ejecutar
JavaScript ni de credenciales de Algolia) un bloque
``<script id="__NEXT_DATA__">`` con el resultado ya resuelto de Algolia para
esa categoría (``props.pageProps.algoliaState.initialResults``), con
``hitsPerPage: 1000`` y ``exhaustiveNbHits: true`` — es decir, en una sola
petición HTTP se obtiene el listado completo (nombre, precio actual, precio
anterior/tachado si hay oferta, formato/peso, marca, imagen, categoría,
slug del producto) de todos los productos de esa categoría, sin paginar.
Es una API de facto embebida en HTML renderizado en servidor, así que la
descargamos con la estrategia HTTP ligera de Crawl4AI
(``AsyncHTTPCrawlerStrategy``, igual que ``mercadona.py``): no hace falta
navegador porque no depende de JavaScript en el cliente para tener los datos
(a diferencia de Lidl, cuyas cabeceras rompen esa estrategia; ALDI no tiene
ese problema).

Verificado en vivo: 2026-09-20, devuelve precios reales y actualizados
(ejemplos reales observados: "Fuet extra" LA TABLA® a 1,79 €/175 g,
"Jamón serrano" LA TABLA® a 2,99 €/180 g).

Gestión del código postal 46022 (Valencia):
El índice de Algolia que sirve estas páginas se llama
``an_prd_es_es_pen_products2`` — "pen" = Península. ALDI España tiene precios
distintos para Península, Baleares y Canarias (el propio pie de página del
sitio lo advierte: "el precio puede variar para tiendas ubicadas en las Islas
Baleares/Canarias", y ``robots.txt`` excluye explícitamente las variantes
regionales ``/bal/`` y ``/can/`` de rastreo). 46022 es Valencia (España
peninsular), así que el dominio principal ``www.aldi.es`` sin ningún prefijo
regional ya sirve el índice/precio correcto para ese código postal; no hace
falta resolver tienda/almacén ni fijar ninguna cookie adicional.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Optional

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from crawl4ai.async_configs import HTTPCrawlerConfig
from crawl4ai.async_crawler_strategy import AsyncHTTPCrawlerStrategy

from .base import BaseSupermarketScraper, ScrapedProduct
from .taxonomy import match_category_for_product_name

logger = logging.getLogger(__name__)

BASE_URL = "https://www.aldi.es"

# Mapeo manual categoría canónica -> páginas de categoría reales de
# aldi.es/productos/... (confirmado navegando el sitemap de páginas de
# aldi.es: https://www.aldi.es/sitemaps/.aldi-nord-sitemap-pages.xml).
# Cada página de categoría trae en una sola petición TODOS sus productos
# (ver docstring del módulo), así que no hace falta buscar por texto como en
# Lidl: usamos directamente la propia taxonomía de ALDI, que es fiable.
CATEGORY_PAGES: dict[str, list[str]] = {
    "pasta": ["/productos/despensa/pasta.html"],
    "arroz": ["/productos/despensa/arroz.html"],
    "leche": ["/productos/lacteos-y-huevos/leche-y-bebidas-vegetales.html"],
    "huevos": ["/productos/lacteos-y-huevos/huevos.html"],
    "aceite-oliva": ["/productos/despensa/aceites-y-vinagres.html"],
    "fuet-embutido": [
        "/productos/charcuteria/embutidos-curados.html",
        "/productos/charcuteria/pollo-pavo-y-jamon-cocido.html",
    ],
    "queso": [
        "/productos/quesos/queso-curado-semicurado-y-tierno.html",
        "/productos/quesos/queso-de-untar.html",
        "/productos/quesos/queso-en-lonchas.html",
        "/productos/quesos/queso-fresco-y-blando.html",
        "/productos/quesos/queso-fundido.html",
        "/productos/quesos/queso-rallado.html",
    ],
    "pan": [
        "/productos/panaderia-y-bolleria/pan-de-horno.html",
        "/productos/panaderia-y-bolleria/pan-de-molde-y-otras-especialidades.html",
    ],
    "cafe": ["/productos/cafe-cacao-e-infusiones/cafe.html"],
    "agua": ["/productos/bebidas/agua.html"],
    "yogures": ["/productos/lacteos-y-huevos/yogures-y-postres-lacteos.html"],
    "detergente-lavadora": ["/productos/limpieza-y-hogar/cuidado-de-la-ropa.html"],
    "papel-higienico": ["/productos/limpieza-y-hogar/papel-higienico-y-celulosa.html"],
    "lejia-limpieza": ["/productos/limpieza-y-hogar/productos-de-limpieza.html"],
    "frutos-secos-snacks": [
        "/productos/aperitivos/frutos-secos-y-semillas.html",
        "/productos/aperitivos/patatas-fritas-y-snacks.html",
    ],
    "cerveza": ["/productos/bebidas-alcoholicas/cerveza.html"],
}


def _extract_algolia_hits(html: str) -> list[dict]:
    match = re.search(
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL
    )
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
    except (json.JSONDecodeError, ValueError):
        logger.warning("No se pudo parsear __NEXT_DATA__ de aldi.es")
        return []
    try:
        initial_results = data["props"]["pageProps"]["algoliaState"]["initialResults"]
        index_payload = next(iter(initial_results.values()))
        return index_payload["results"][0]["hits"]
    except (KeyError, IndexError, StopIteration, TypeError):
        return []


class AldiScraper(BaseSupermarketScraper):
    slug = "aldi"
    display_name = "Aldi"
    color = "#00447C"
    online_store_url = "https://www.aldi.es"
    live_verified = True
    notes = (
        "www.aldi.es publica un catalogo de supermercado real y navegable "
        "por categoria (https://www.aldi.es/productos/...) que, a "
        "diferencia de Lidl, SI corresponde a los productos que se venden "
        "en tienda (con foto, marca, formato y precio actual/anterior "
        "reales). Cada pagina de categoria trae en su HTML "
        "renderizado en servidor un bloque __NEXT_DATA__ con el resultado "
        "ya resuelto de la busqueda Algolia de esa categoria completa "
        "(hitsPerPage=1000, exhaustiveNbHits=true), asi que una sola "
        "peticion HTTP por categoria basta para tener el listado completo, "
        "sin necesidad de navegador ni de credenciales de Algolia. Se "
        "descarga con AsyncHTTPCrawlerStrategy de Crawl4AI (como "
        "mercadona.py); a diferencia de Lidl, aldi.es no dispara el limite "
        "de cabeceras del cliente HTTP interno de Crawl4AI. El mapeo "
        "categoria canonica -> URL de categoria de aldi.es se hizo a mano "
        "revisando el sitemap real de paginas del sitio."
    )

    def __init__(self, postal_code: str = "46022"):
        # Documentado arriba: 46022 (Valencia, España peninsular) usa el
        # dominio principal sin prefijo regional (Baleares/Canarias tienen
        # variantes de precio propias que no aplican aquí).
        self.postal_code = postal_code

    async def fetch_products(self) -> list[ScrapedProduct]:
        page_to_categories: dict[str, list[str]] = {}
        for category_slug, pages in CATEGORY_PAGES.items():
            for page in pages:
                page_to_categories.setdefault(page, []).append(category_slug)

        strategy = AsyncHTTPCrawlerStrategy(browser_config=HTTPCrawlerConfig())
        hits_by_page: dict[str, list[dict]] = {}
        async with AsyncWebCrawler(crawler_strategy=strategy) as crawler:
            sem = asyncio.Semaphore(6)

            async def fetch_one(page: str) -> None:
                async with sem:
                    url = BASE_URL + page
                    try:
                        result = await crawler.arun(url, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
                    except Exception:
                        logger.warning("Fallo al descargar categoria Aldi %s", page)
                        return
                    if not result.success or not result.html:
                        logger.warning("Categoria Aldi sin exito: %s", page)
                        return
                    hits_by_page[page] = _extract_algolia_hits(result.html)

            await asyncio.gather(*(fetch_one(page) for page in page_to_categories))

        products: list[ScrapedProduct] = []
        seen_ids: set[str] = set()
        for page, category_slugs in page_to_categories.items():
            for hit in hits_by_page.get(page, []):
                # Cuando una URL de categoría cubre varias categorías
                # canónicas (no ocurre en el mapeo actual, pero por si se
                # amplía) o cuando queremos confirmar el match, usamos el
                # matcher de texto de la taxonomía como criterio primario y
                # caemos al slug de la propia página de categoría si no
                # matchea ningún término (la taxonomía de ALDI es fiable,
                # así que esto es solo una comprobación adicional de
                # robustez, no la fuente principal de la categoría).
                name = (hit.get("name") or "").strip()
                if not name:
                    continue
                matched_slug = match_category_for_product_name(name) or (
                    category_slugs[0] if len(category_slugs) == 1 else None
                )
                if matched_slug is None:
                    continue
                product = self._to_product(hit, matched_slug)
                if product is None or product.external_id in seen_ids:
                    continue
                seen_ids.add(product.external_id)
                products.append(product)
        return products

    def _to_product(self, hit: dict, category_slug: str) -> Optional[ScrapedProduct]:
        name = (hit.get("name") or "").strip()
        if not name:
            return None
        current_price = hit.get("currentPrice") or {}
        price = current_price.get("priceValue")
        if not isinstance(price, (int, float)) or price <= 0:
            return None

        previous_price = None
        strike = current_price.get("strikePrice")
        if isinstance(strike, dict) and strike.get("strikePriceValue"):
            try:
                previous_price = float(strike["strikePriceValue"])
            except (TypeError, ValueError):
                previous_price = None
        is_offer = previous_price is not None or bool(current_price.get("priceTagLabels"))

        base_price = None
        base_price_list = current_price.get("basePrice")
        if isinstance(base_price_list, list) and base_price_list:
            try:
                base_price = float(base_price_list[0].get("basePriceValue"))
            except (TypeError, ValueError):
                base_price = None

        product_slug = hit.get("productSlug")
        url = f"{BASE_URL}/producto/{product_slug}.html" if product_slug else None

        image_url = None
        for asset in hit.get("assets") or []:
            if isinstance(asset, dict) and asset.get("type") == "primary" and asset.get("url"):
                image_url = asset["url"]
                break

        external_id = hit.get("objectID")
        if not external_id:
            refs = hit.get("productReferences") or []
            for ref in refs:
                if isinstance(ref, dict) and ref.get("type") == "KVArticleNumber":
                    external_id = ref.get("value")
                    break
        if not external_id:
            external_id = product_slug or name
        external_id = str(external_id)

        raw_category = None
        hierarchical = hit.get("hierarchicalCategories") or {}
        lvl1 = hierarchical.get("lvl1")
        if isinstance(lvl1, list) and lvl1:
            raw_category = lvl1[0]
        elif isinstance(hierarchical.get("lvl0"), list) and hierarchical["lvl0"]:
            raw_category = hierarchical["lvl0"][0]

        return ScrapedProduct(
            supermarket_slug=self.slug,
            external_id=external_id,
            name=name,
            category_slug=category_slug,
            raw_category_name=raw_category,
            price=float(price),
            url=url,
            brand=hit.get("brandName"),
            image_url=image_url,
            unit=hit.get("salesUnit"),
            unit_price=base_price,
            is_offer=is_offer,
            previous_price=previous_price,
            discount_pct=self.compute_discount(float(price), previous_price),
        )
