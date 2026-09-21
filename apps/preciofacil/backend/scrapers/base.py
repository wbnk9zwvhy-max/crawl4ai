"""Interfaz común que debe implementar cada scraper de supermercado.

Todos los scrapers usan Crawl4AI (``crawl4ai.AsyncWebCrawler``) para obtener el
HTML/JSON de la tienda online real del supermercado y devuelven una lista de
``ScrapedProduct`` normalizados, listos para persistir en la base de datos.

El código postal de referencia para toda la app es 46022 (Valencia), tal y
como pidió el usuario. Cuando el supermercado necesita fijar una tienda /
almacén a partir del código postal, cada scraper documenta cómo lo resuelve.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


DEFAULT_POSTAL_CODE = "46022"


@dataclass
class ScrapedProduct:
    supermarket_slug: str
    external_id: str
    name: str
    category_slug: Optional[str]
    price: float
    url: Optional[str] = None
    brand: Optional[str] = None
    image_url: Optional[str] = None
    #: ruta relativa dentro de app/media/products una vez descargada la
    #: imagen original del producto (ver app/media.py); la rellena el
    #: pipeline de ingesta, no el scraper.
    local_image_path: Optional[str] = None
    unit_price: Optional[float] = None
    unit: Optional[str] = None
    is_offer: bool = False
    previous_price: Optional[float] = None
    discount_pct: Optional[float] = None
    scraped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_category_name: Optional[str] = None


class BaseSupermarketScraper(ABC):
    slug: str
    display_name: str
    color: str  # color de marca en hex, usado en la UI
    postal_code: str = DEFAULT_POSTAL_CODE
    online_store_url: str = ""
    #: True si la fuente de datos ha sido verificada como accesible en vivo
    #: desde este entorno en la fecha de implementación del scraper.
    live_verified: bool = False
    notes: str = ""

    @abstractmethod
    async def fetch_products(self) -> list[ScrapedProduct]:
        """Descarga y normaliza los productos disponibles para las categorías
        canónicas soportadas. Debe usar Crawl4AI para el fetch."""
        raise NotImplementedError

    def compute_discount(self, price: float, previous_price: Optional[float]) -> Optional[float]:
        if not previous_price or previous_price <= 0 or previous_price <= price:
            return None
        return round((previous_price - price) / previous_price * 100, 1)
