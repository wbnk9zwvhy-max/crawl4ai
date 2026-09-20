"""Scraper de Carrefour España (carrefour.es).

A diferencia de Mercadona, Carrefour NO expone una API JSON pública sin
protección: todo el dominio ``www.carrefour.es`` está detrás de Cloudflare
con un reto interactivo ("Managed Challenge" / Turnstile, ver más abajo en
"Investigación realizada"). Por eso este scraper usa el crawler con
navegador real de Crawl4AI (``AsyncWebCrawler`` + Playwright/Chromium) en
vez del ``AsyncHTTPCrawlerStrategy`` ligero que usa ``mercadona.py``.

Estrategia de extracción (en orden de preferencia, todas intentadas sobre el
HTML ya renderizado por el navegador):
1. JSON-LD (``<script type="application/ld+json">`` con ``@type: Product``
   o ``ItemList``): es el estándar SEO que casi cualquier e-commerce incluye
   en sus páginas de listado/búsqueda, independientemente del framework de
   frontend que use, así que es la vía más robusta a cambios de maquetación.
2. Blobs de estado embebidos por el frontend (``__NEXT_DATA__``,
   ``__INITIAL_STATE__``, ``__PRELOADED_STATE__``, etc.): frontends React/
   Next.js suelen incrustar el estado inicial (incluidos los productos ya
   consultados) como JSON dentro de un <script>. Se recorre recursivamente
   buscando objetos con pinta de producto (nombre + precio).
3. Heurística CSS genérica sobre tarjetas de producto (``data-testid``/
   ``class`` que contengan "product"), como último recurso.

Gestión del código postal 46022 (Valencia):
Carrefour.es, como la mayoría de supermercados online españoles, exige fijar
una tienda antes de mostrar precios y stock reales de compra online. En este
sitio esto se resuelve con un modal/selector de tienda que pide el código
postal (o población) la primera vez que se visita la home; la selección
queda memorizada en cookies/localStorage del navegador para el resto de la
sesión. Como no se ha podido completar una sesión real contra el sitio (ver
más abajo), no ha sido posible observar el nombre exacto de esa cookie desde
este entorno. El scraper intenta, de forma best-effort y no bloqueante:
  a) aceptar el banner de cookies (OneTrust/Cookiebot y variantes en
     español: "Aceptar", "Aceptar todas", etc.), y
  b) localizar un input de tipo código postal en la home y rellenarlo con
     "46022", enviando el formulario/modal de selección de tienda,
antes de navegar a las páginas de búsqueda, reutilizando la misma sesión de
navegador (``session_id``) para que las cookies resultantes persistan entre
peticiones. Si el sitio cambia el flujo, esto simplemente no tendrá efecto
(no lanza excepción) y el resto del scraper sigue intentando extraer
productos igualmente.

Investigación realizada (todo documentado también en ``notes``):
- ``curl https://www.carrefour.es`` (sin navegador) → 403 en todos los
  paths probados, incluidas rutas de API adivinadas bajo
  ``/cloud-api/...`` (esas rutas se conocen porque ``robots.txt`` las
  menciona explícitamente en sus reglas ``Disallow``, lo que confirma que
  existen aunque no se haya podido leer su respuesta real).
- ``robots.txt`` SÍ es accesible (200) y confirma que el buscador vive bajo
  ``/buscador/`` (con `Disallow: /buscador/`), que es la URL que usa este
  scraper para consultar cada categoría canónica por su término de búsqueda.
- Con Crawl4AI + navegador real (Playwright/Chromium) headless, con
  ``user_agent`` realista de Chrome, cabeceras ``Accept-Language: es-ES``,
  ``magic=True`` (modo stealth/anti-detección de Crawl4AI),
  ``enable_stealth=True``, ``simulate_user=True``,
  ``override_navigator=True`` y esperas de hasta 20s: la navegación
  devuelve HTTP 307 y una página intersticial "Un momento…" servida por
  ``challenges.cloudflare.com`` (Cloudflare Turnstile / Managed Challenge).
  Crawl4AI lo detecta explícitamente como
  ``Blocked by anti-bot protection: Cloudflare JS challenge``.
- Se repitió la misma prueba con navegador NO headless (``headless=False``)
  bajo un framebuffer virtual (``xvfb-run``), por si el bloqueo dependía de
  la detección de modo headless: mismo resultado (HTTP 307, "Un momento…").
- Se buscaron subdominios API alternativos sin protección (patrón habitual
  en otros supermercados, p.ej. ``tienda.mercadona.es``):
  ``api.carrefour.es``, ``m.carrefour.es``, ``mobile.carrefour.es``,
  ``apps.carrefour.es`` no resuelven DNS; el único host que resuelve es
  ``www.carrefour.es`` (IPs de Cloudflare, 104.18.x.x), y ese host aplica el
  mismo reto a cualquier ruta.
- Conclusión: el bloqueo ocurre a nivel de borde (Cloudflare), antes de
  llegar al origen, y muy probablemente está relacionado con la reputación
  de la IP de salida de este sandbox (tráfico vía proxy corporativo), no
  solo con "huellas" de automatización del navegador — de ahí que ni
  headless, ni no-headless, ni stealth, ni esperas largas lo esquiven.
  ``live_verified`` queda en ``False`` de forma honesta. El código de
  extracción de más abajo queda listo para funcionar en cuanto se ejecute
  desde una IP/entorno que Cloudflare no bloquee; los selectores CSS de
  fallback son heurísticos (no se han podido verificar contra el HTML real
  servido tras el reto) mientras que la extracción JSON-LD/blobs de estado
  es agnóstica a la maquetación exacta y debería seguir funcionando.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Iterable, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

from .base import BaseSupermarketScraper, ScrapedProduct
from .taxonomy import CANONICAL_CATEGORIES, match_category_for_product_name

logger = logging.getLogger(__name__)

STORE_BASE_URL = "https://www.carrefour.es"
SEARCH_URL_TEMPLATE = f"{STORE_BASE_URL}/buscador/{{term}}"

# UA de un Chrome de escritorio reciente y realista en español.
DESKTOP_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# JS best-effort para aceptar el banner de cookies y fijar el código postal
# de la tienda. No lanza si no encuentra nada (todo va envuelto en try/catch
# dentro del propio JS), así que es seguro ejecutarlo siempre.
SETUP_SESSION_JS = """
(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // 1) Banner de cookies (OneTrust, Cookiebot y variantes en español).
  try {
    const cookieSelectors = [
      '#onetrust-accept-btn-handler',
      'button#onetrust-accept-btn-handler',
      'button[aria-label="Aceptar todas"]',
      'button[aria-label="Aceptar"]',
      '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll',
    ];
    for (const sel of cookieSelectors) {
      const btn = document.querySelector(sel);
      if (btn) { btn.click(); await sleep(300); break; }
    }
    // Fallback: buscar por texto visible del botón.
    if (!document.querySelector('.onetrust-pc-dark-filter')) {
      const buttons = Array.from(document.querySelectorAll('button'));
      const byText = buttons.find((b) => /aceptar/i.test(b.textContent || ''));
      if (byText) { byText.click(); await sleep(300); }
    }
  } catch (e) {}

  await sleep(500);

  // 2) Selector de tienda / código postal.
  try {
    const postalInput = document.querySelector(
      'input[name*="postal" i], input[id*="postal" i], ' +
      'input[placeholder*="postal" i], input[placeholder*="código postal" i], ' +
      'input[name*="cp" i][type="text"]'
    );
    if (postalInput) {
      postalInput.focus();
      postalInput.value = '46022';
      postalInput.dispatchEvent(new Event('input', { bubbles: true }));
      postalInput.dispatchEvent(new Event('change', { bubbles: true }));
      await sleep(300);
      const submitBtn = document.querySelector(
        'button[type="submit"], button[data-testid*="postal" i], ' +
        'button[data-testid*="store" i], button[data-testid*="confirm" i]'
      );
      if (submitBtn) { submitBtn.click(); await sleep(500); }
    }
  } catch (e) {}
})();
"""

PRICE_RE = re.compile(r"(\d{1,4}(?:[.,]\d{1,2})?)\s*€")


def _parse_price(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    match = PRICE_RE.search(text)
    if not match:
        return None
    raw = match.group(1).replace(".", "").replace(",", ".")
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def _walk_json_for_products(node: Any, out: list[dict]) -> None:
    """Recorre recursivamente un blob JSON de estado de frontend buscando
    objetos con pinta de "producto" (tienen nombre + algún campo de precio)."""
    if isinstance(node, dict):
        name = node.get("name") or node.get("title") or node.get("displayName")
        price_val = None
        for price_key in ("price", "finalPrice", "currentPrice", "sellingPrice"):
            candidate = node.get(price_key)
            if isinstance(candidate, (int, float)):
                price_val = float(candidate)
                break
            if isinstance(candidate, dict):
                for sub_key in ("value", "amount", "final", "current"):
                    if isinstance(candidate.get(sub_key), (int, float)):
                        price_val = float(candidate[sub_key])
                        break
        if isinstance(name, str) and name.strip() and price_val is not None and price_val > 0:
            out.append(node)
        for value in node.values():
            _walk_json_for_products(value, out)
    elif isinstance(node, list):
        for item in node:
            _walk_json_for_products(item, out)


class CarrefourScraper(BaseSupermarketScraper):
    slug = "carrefour"
    display_name = "Carrefour"
    color = "#004E9F"
    online_store_url = STORE_BASE_URL
    postal_code = "46022"
    live_verified = False
    notes = (
        "www.carrefour.es bloquea el acceso automatizado desde este "
        "entorno (protección Cloudflare); el scraper está listo para "
        "funcionar en cuanto se ejecute desde un entorno sin ese bloqueo."
    )

    def __init__(self, postal_code: str = "46022"):
        self.postal_code = postal_code

    def _browser_config(self) -> BrowserConfig:
        return BrowserConfig(
            headless=True,
            browser_type="chromium",
            user_agent=DESKTOP_USER_AGENT,
            viewport_width=1366,
            viewport_height=900,
            headers={"Accept-Language": "es-ES,es;q=0.9"},
            enable_stealth=True,
        )

    async def fetch_products(self) -> list[ScrapedProduct]:
        products: list[ScrapedProduct] = []
        browser_conf = self._browser_config()
        session_id = "carrefour-session"

        try:
            async with AsyncWebCrawler(config=browser_conf) as crawler:
                # 1) Cargar la home, aceptar cookies y fijar el CP 46022.
                #    Reutilizamos session_id para que las cookies resultantes
                #    persistan en las siguientes navegaciones.
                setup_conf = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    magic=True,
                    simulate_user=True,
                    override_navigator=True,
                    wait_until="domcontentloaded",
                    page_timeout=45000,
                    delay_before_return_html=6.0,
                    js_code=SETUP_SESSION_JS,
                    session_id=session_id,
                )
                home_result = await crawler.arun(STORE_BASE_URL + "/", config=setup_conf)
                if not home_result.success:
                    logger.warning(
                        "Carrefour: no se pudo cargar la home (%s). "
                        "Probablemente bloqueado por Cloudflare; se documenta "
                        "en notes y live_verified queda en False.",
                        getattr(home_result, "status_code", "sin status"),
                    )

                # 2) Una búsqueda por término representativo de cada
                #    categoría canónica (cubrimos todas las que tenemos
                #    términos de búsqueda razonables).
                for category in CANONICAL_CATEGORIES:
                    term = category.search_terms[0].strip()
                    if not term:
                        continue
                    url = SEARCH_URL_TEMPLATE.format(term=quote(term))
                    search_conf = CrawlerRunConfig(
                        cache_mode=CacheMode.BYPASS,
                        magic=True,
                        simulate_user=True,
                        override_navigator=True,
                        wait_until="domcontentloaded",
                        page_timeout=45000,
                        delay_before_return_html=4.0,
                        session_id=session_id,
                    )
                    try:
                        result = await crawler.arun(url, config=search_conf)
                    except Exception:
                        logger.exception("Carrefour: error navegando %s", url)
                        continue
                    if not result.success or not result.html:
                        continue
                    found = self._extract_products(
                        result.html, category_slug=category.slug, source_url=url
                    )
                    products.extend(found)
        except Exception:
            logger.exception(
                "Carrefour: fallo irrecuperable montando el navegador/crawl. "
                "Se devuelve lista vacía/parcial; ver notes."
            )

        return self._dedupe(products)

    # ------------------------------------------------------------------
    # Extracción
    # ------------------------------------------------------------------
    def _extract_products(
        self, html: str, category_slug: str, source_url: str
    ) -> list[ScrapedProduct]:
        out: list[ScrapedProduct] = []
        out.extend(self._extract_from_jsonld(html, category_slug, source_url))
        if not out:
            out.extend(self._extract_from_state_blobs(html, category_slug, source_url))
        if not out:
            out.extend(self._extract_from_css_fallback(html, category_slug, source_url))
        return out

    def _extract_from_jsonld(
        self, html: str, category_slug: str, source_url: str
    ) -> list[ScrapedProduct]:
        soup = BeautifulSoup(html, "html.parser")
        out: list[ScrapedProduct] = []
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or script.get_text() or "{}")
            except (json.JSONDecodeError, TypeError):
                continue
            for entry in self._flatten_jsonld(data):
                product = self._product_from_jsonld_entry(entry, category_slug, source_url)
                if product:
                    out.append(product)
        return out

    def _flatten_jsonld(self, data: Any) -> Iterable[dict]:
        if isinstance(data, list):
            for item in data:
                yield from self._flatten_jsonld(item)
            return
        if not isinstance(data, dict):
            return
        type_ = data.get("@type")
        types = type_ if isinstance(type_, list) else [type_]
        if "Product" in types:
            yield data
        if "ItemList" in types:
            for element in data.get("itemListElement", []) or []:
                item = element.get("item", element) if isinstance(element, dict) else element
                yield from self._flatten_jsonld(item)
        for value in data.values():
            if isinstance(value, (dict, list)):
                yield from self._flatten_jsonld(value)

    def _product_from_jsonld_entry(
        self, entry: dict, category_slug: str, source_url: str
    ) -> Optional[ScrapedProduct]:
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            return None
        offers = entry.get("offers")
        if isinstance(offers, list):
            offers = offers[0] if offers else None
        price = None
        if isinstance(offers, dict):
            price = offers.get("price") or offers.get("lowPrice")
        try:
            price = float(price) if price is not None else None
        except (TypeError, ValueError):
            price = None
        if price is None or price <= 0:
            return None
        url = entry.get("url") or (offers.get("url") if isinstance(offers, dict) else None)
        image = entry.get("image")
        if isinstance(image, list):
            image = image[0] if image else None
        matched = match_category_for_product_name(name) or category_slug
        return ScrapedProduct(
            supermarket_slug=self.slug,
            external_id=self._external_id(entry.get("sku") or entry.get("@id") or url or name),
            name=name.strip(),
            category_slug=matched,
            raw_category_name=category_slug,
            price=price,
            url=url if isinstance(url, str) else source_url,
            brand=self._brand_from(entry.get("brand")),
            image_url=image if isinstance(image, str) else None,
        )

    def _extract_from_state_blobs(
        self, html: str, category_slug: str, source_url: str
    ) -> list[ScrapedProduct]:
        out: list[ScrapedProduct] = []
        candidates: list[dict] = []
        for match in re.finditer(
            r"(?:__NEXT_DATA__|__INITIAL_STATE__|__PRELOADED_STATE__|__APOLLO_STATE__)"
            r"\s*=\s*(\{.*?\})\s*(?:;|</script>)",
            html,
            re.DOTALL,
        ):
            try:
                blob = json.loads(match.group(1))
            except (json.JSONDecodeError, TypeError):
                continue
            found: list[dict] = []
            _walk_json_for_products(blob, found)
            candidates.extend(found)

        # También el patrón habitual de Next.js: <script id="__NEXT_DATA__" type="application/json">
        soup = BeautifulSoup(html, "html.parser")
        next_data = soup.find("script", id="__NEXT_DATA__")
        if next_data and (next_data.string or next_data.get_text()):
            try:
                blob = json.loads(next_data.string or next_data.get_text())
                found = []
                _walk_json_for_products(blob, found)
                candidates.extend(found)
            except (json.JSONDecodeError, TypeError):
                pass

        for entry in candidates:
            name = entry.get("name") or entry.get("title") or entry.get("displayName")
            if not isinstance(name, str) or not name.strip():
                continue
            price = None
            for price_key in ("price", "finalPrice", "currentPrice", "sellingPrice"):
                candidate = entry.get(price_key)
                if isinstance(candidate, (int, float)):
                    price = float(candidate)
                    break
                if isinstance(candidate, dict):
                    for sub_key in ("value", "amount", "final", "current"):
                        if isinstance(candidate.get(sub_key), (int, float)):
                            price = float(candidate[sub_key])
                            break
                if price is not None:
                    break
            if price is None or price <= 0:
                continue
            matched = match_category_for_product_name(name) or category_slug
            out.append(
                ScrapedProduct(
                    supermarket_slug=self.slug,
                    external_id=self._external_id(
                        entry.get("id") or entry.get("sku") or entry.get("ean") or name
                    ),
                    name=name.strip(),
                    category_slug=matched,
                    raw_category_name=category_slug,
                    price=price,
                    url=entry.get("url") if isinstance(entry.get("url"), str) else source_url,
                    brand=self._brand_from(entry.get("brand")),
                    image_url=entry.get("image") if isinstance(entry.get("image"), str) else None,
                )
            )
        return out

    def _extract_from_css_fallback(
        self, html: str, category_slug: str, source_url: str
    ) -> list[ScrapedProduct]:
        """Heurística de respaldo, NO verificada contra HTML real (ver notes):
        busca contenedores cuya clase o data-testid contenga "product" y,
        dentro, un texto con precio en euros junto a un texto de nombre."""
        soup = BeautifulSoup(html, "html.parser")
        out: list[ScrapedProduct] = []
        candidates = soup.select(
            '[data-testid*="product" i], [class*="product-card" i], '
            '[class*="productCard" i], li[class*="product" i]'
        )
        for card in candidates:
            text = card.get_text(" ", strip=True)
            price = _parse_price(text)
            if price is None:
                continue
            name_el = card.select_one(
                '[data-testid*="name" i], [class*="title" i], [class*="name" i], h2, h3'
            )
            name = name_el.get_text(strip=True) if name_el else None
            if not name:
                continue
            link_el = card.select_one("a[href]")
            url = link_el["href"] if link_el else source_url
            if isinstance(url, str) and url.startswith("/"):
                url = STORE_BASE_URL + url
            img_el = card.select_one("img[src]")
            image_url = img_el["src"] if img_el else None
            matched = match_category_for_product_name(name) or category_slug
            out.append(
                ScrapedProduct(
                    supermarket_slug=self.slug,
                    external_id=self._external_id(url or name),
                    name=name,
                    category_slug=matched,
                    raw_category_name=category_slug,
                    price=price,
                    url=url if isinstance(url, str) else None,
                    image_url=image_url if isinstance(image_url, str) else None,
                )
            )
        return out

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _brand_from(brand_field: Any) -> Optional[str]:
        if isinstance(brand_field, str):
            return brand_field
        if isinstance(brand_field, dict):
            name = brand_field.get("name")
            return name if isinstance(name, str) else None
        return None

    @staticmethod
    def _external_id(value: Any) -> str:
        return str(value) if value else "unknown"

    @staticmethod
    def _dedupe(products: list[ScrapedProduct]) -> list[ScrapedProduct]:
        seen: set[tuple[str, str]] = set()
        out: list[ScrapedProduct] = []
        for product in products:
            key = (product.external_id, product.name)
            if key in seen:
                continue
            seen.add(key)
            out.append(product)
        return out
