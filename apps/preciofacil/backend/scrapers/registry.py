"""Registro central de supermercados soportados por la app.

Cada entrada apunta a la clase scraper (o a ``None`` si el supermercado no
tiene tienda online scrapeable, como Kuups) más los metadatos de marca usados
por el backend y el frontend.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Type

from .base import BaseSupermarketScraper

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SupermarketEntry:
    slug: str
    name: str
    color: str
    logo_emoji: str
    online_store_url: str
    scraper_cls: Optional[Type[BaseSupermarketScraper]]
    notes: str = ""


def _load_registry() -> list[SupermarketEntry]:
    entries: list[SupermarketEntry] = []

    from .mercadona import MercadonaScraper

    entries.append(
        SupermarketEntry(
            slug="mercadona",
            name="Mercadona",
            color="#00A19A",
            logo_emoji="🟢",
            online_store_url="https://tienda.mercadona.es",
            scraper_cls=MercadonaScraper,
        )
    )

    def _try(slug: str, module: str, cls_name: str, name: str, color: str, emoji: str, url: str) -> None:
        try:
            mod = __import__(f"scrapers.{module}", fromlist=[cls_name])
            cls = getattr(mod, cls_name)
        except Exception:  # pragma: no cover - degradación elegante
            logger.exception("No se pudo cargar el scraper de %s", slug)
            entries.append(
                SupermarketEntry(
                    slug=slug,
                    name=name,
                    color=color,
                    logo_emoji=emoji,
                    online_store_url=url,
                    scraper_cls=None,
                    notes="Todavía estamos preparando la conexión con la tienda online de este supermercado.",
                )
            )
            return
        entries.append(
            SupermarketEntry(
                slug=slug,
                name=name,
                color=color,
                logo_emoji=emoji,
                online_store_url=url,
                scraper_cls=cls,
                notes=getattr(cls, "notes", ""),
            )
        )

    _try("consum", "consum", "ConsumScraper", "Consum", "#E30613", "🔴", "https://www.consum.es")
    _try("lidl", "lidl", "LidlScraper", "Lidl", "#0050AA", "🔵", "https://www.lidl.es")
    _try("carrefour", "carrefour", "CarrefourScraper", "Carrefour", "#004E9F", "🔷", "https://www.carrefour.es")
    _try("aldi", "aldi", "AldiScraper", "Aldi", "#FF6600", "🟠", "https://www.aldi.es")
    _try("dia", "dia", "DiaScraper", "Día", "#E2001A", "🅳", "https://www.dia.es")

    entries.append(
        SupermarketEntry(
            slug="kuups",
            name="Kuups",
            color="#6B4EFF",
            logo_emoji="🟣",
            online_store_url="",
            scraper_cls=None,
            notes=(
                "Kuups (antes Economy Cash / Vidal Tiendas) es una cadena valenciana de "
                "supermercado de proximidad sin tienda online pública accesible en este "
                "momento (dominio no resuelve). Se incluye en la app para que puedas "
                "registrar tus compras manualmente y compararlas, pero sus precios no se "
                "actualizan automáticamente."
            ),
        )
    )

    return entries


REGISTRY: list[SupermarketEntry] = _load_registry()
REGISTRY_BY_SLUG: dict[str, SupermarketEntry] = {e.slug: e for e in REGISTRY}
