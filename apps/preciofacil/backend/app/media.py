"""Descarga y cachea en disco la imagen original de cada producto.

En vez de enlazar en caliente (hotlink) la imagen del CDN de cada
supermercado —que puede bloquear referrers, caducar la URL o simplemente
no estar disponible sin conexión—, descargamos una copia local la primera
vez que vemos un producto y servimos esa copia desde el propio backend
(ver el mount de ``/media`` en app/main.py). Si el producto ya tiene la
imagen descargada de un día anterior, no se vuelve a descargar.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

MEDIA_DIR = Path(__file__).resolve().parent.parent / "media"
PRODUCTS_DIR = MEDIA_DIR / "products"
PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)
RECEIPTS_DIR = MEDIA_DIR / "receipts"
RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)


def save_receipt_image(content: bytes, content_type: str | None) -> str:
    """Guarda la foto de un ticket subida por el usuario y devuelve su ruta
    relativa dentro de MEDIA_DIR (servible bajo /media/<ruta>)."""
    ext = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/heic": ".heic",
    }.get((content_type or "").lower(), ".jpg")
    filename = f"{uuid.uuid4().hex}{ext}"
    (RECEIPTS_DIR / filename).write_bytes(content)
    return f"receipts/{filename}"

_DEFAULT_EXT = ".jpg"
_ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_DOWNLOAD_CONCURRENCY = 12

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}


def _guess_extension(url: str) -> str:
    ext = Path(urlsplit(url).path).suffix.lower()
    return ext if ext in _ALLOWED_EXT else _DEFAULT_EXT


def _safe_filename(external_id: str, url: str) -> str:
    safe_id = "".join(c if c.isalnum() or c in "-_." else "_" for c in external_id)
    return f"{safe_id}{_guess_extension(url)}"


async def ensure_local_image(
    client: httpx.AsyncClient, supermarket_slug: str, external_id: str, image_url: str | None
) -> str | None:
    """Descarga la imagen de un producto si no la teníamos ya. Devuelve la
    ruta relativa dentro de MEDIA_DIR (servible bajo /media/<ruta>) o None
    si no hay imagen o la descarga falla."""
    if not image_url:
        return None

    rel_path = f"{supermarket_slug}/{_safe_filename(external_id, image_url)}"
    abs_path = PRODUCTS_DIR / rel_path

    if abs_path.exists() and abs_path.stat().st_size > 0:
        return f"products/{rel_path}"

    try:
        response = await client.get(image_url, headers=_HEADERS, timeout=15, follow_redirects=True)
        response.raise_for_status()
        content = response.content
        if not content:
            return None
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_bytes(content)
        return f"products/{rel_path}"
    except Exception as exc:
        logger.debug("No se pudo descargar imagen de %s/%s: %s", supermarket_slug, external_id, exc)
        return None


async def download_product_images(products: list) -> None:
    """Descarga en paralelo (con límite de concurrencia) las imágenes de una
    lista de ScrapedProduct, rellenando su ``local_image_path``."""
    semaphore = asyncio.Semaphore(_DOWNLOAD_CONCURRENCY)

    async with httpx.AsyncClient(http2=False) as client:

        async def _one(product) -> None:
            async with semaphore:
                product.local_image_path = await ensure_local_image(
                    client, product.supermarket_slug, product.external_id, product.image_url
                )

        await asyncio.gather(*(_one(p) for p in products))
