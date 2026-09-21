"""Análisis de fotos de tickets de compra con Claude (visión).

El usuario sube una foto del ticket desde "Mis compras"; se la pasamos a
Claude pidiéndole que extraiga cada línea de producto con su precio, y
mapeamos el resultado a nuestra taxonomía de categorías y a uno de los
supermercados soportados antes de devolvérselo al frontend como un
borrador editable (nunca se guardan compras sin que el usuario las
confirme, por si el modelo se equivoca en algo).

Requiere la variable de entorno ANTHROPIC_API_KEY (o cualquier mecanismo de
credenciales que resuelva el SDK de Anthropic). Si no está configurada, el
endpoint devuelve un error explicando cómo activarla en vez de fallar de
forma críptica.
"""
from __future__ import annotations

import os
import unicodedata

from pydantic import BaseModel

from scrapers.taxonomy import match_category_for_product_name

# Se puede sustituir por un modelo más barato (p.ej. "claude-haiku-4-5")
# vía variable de entorno si el volumen de tickets lo justifica; por
# defecto usamos el modelo más capaz para maximizar la precisión leyendo
# tickets de supermercado a menudo borrosos o con letra pequeña.
RECEIPT_MODEL = os.environ.get("RECEIPT_ANALYSIS_MODEL", "claude-opus-5")

_MEDIA_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


class ReceiptAnalysisError(RuntimeError):
    """Fallo al analizar un ticket (API no configurada, imagen ilegible...)."""


class ExtractedItem(BaseModel):
    name: str
    unit_price: float
    quantity: float = 1


class ReceiptExtraction(BaseModel):
    supermarket_guess: str
    purchase_date: str | None = None
    items: list[ExtractedItem]
    total: float | None = None


EXTRACTION_PROMPT = """\
Esta imagen es la foto de un ticket de compra de un supermercado español. \
Extrae:

- supermarket_guess: el nombre del supermercado tal y como aparece impreso \
en la cabecera del ticket (p.ej. "Mercadona", "Consum", "Lidl", \
"Carrefour", "Aldi", "Dia"). Si no se lee con claridad, pon "desconocido".
- purchase_date: la fecha de la compra en formato YYYY-MM-DD si aparece \
impresa en el ticket, o null si no se lee.
- items: una línea por cada producto comprado, con su nombre tal y como \
aparece impreso (puedes desarrollar abreviaturas obvias), el precio \
unitario pagado por ese producto (si el ticket ya muestra el precio total \
de la línea y una cantidad, usa precio_total/cantidad) y la cantidad \
comprada (1 si no se indica lo contrario). NO incluyas líneas que no sean \
productos: subtotales, IVA, total, cambio, forma de pago, puntos de \
fidelización, mensajes promocionales, etc.
- total: el importe total del ticket si aparece impreso, o null.

Si la imagen no es legible o no parece un ticket de compra, devuelve items \
como una lista vacía.
"""


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def guess_supermarket_slug(free_text: str, supermarket_names: dict[str, str]) -> str | None:
    """Empareja el texto libre que ha leído el modelo en la cabecera del
    ticket con uno de los slugs de supermercado que soporta la app."""
    normalized = _strip_accents(free_text.lower())
    for slug, name in supermarket_names.items():
        if _strip_accents(name.lower()) in normalized or normalized in _strip_accents(name.lower()):
            return slug
    # alias comunes que no coinciden literalmente con el nombre mostrado
    aliases = {
        "dia": "dia",
        "mercadona": "mercadona",
        "consum": "consum",
        "lidl": "lidl",
        "carrefour": "carrefour",
        "aldi": "aldi",
    }
    for alias, slug in aliases.items():
        if alias in normalized and slug in supermarket_names:
            return slug
    return None


def analyze_receipt_bytes(image_bytes: bytes, media_type: str) -> ReceiptExtraction:
    """Llama a Claude para extraer los productos y precios de una foto de
    ticket. Lanza ReceiptAnalysisError si no se puede completar."""
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - dependencia declarada en requirements.txt
        raise ReceiptAnalysisError(
            "Falta instalar el SDK de Anthropic en el backend (pip install anthropic)."
        ) from exc

    # El SDK, si no encuentra credenciales, no falla hasta construir la
    # petición real (con un TypeError interno poco descriptivo), así que
    # comprobamos nosotros antes de intentar nada para dar un mensaje claro.
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        raise ReceiptAnalysisError(
            "El análisis de tickets con IA no está activado en este backend: falta la variable "
            "de entorno ANTHROPIC_API_KEY. Añádela a la configuración del servidor para poder "
            "escanear tickets (ver README)."
        )

    client = anthropic.Anthropic()

    import base64

    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    try:
        response = client.messages.parse(
            model=RECEIPT_MODEL,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": media_type, "data": image_b64},
                        },
                        {"type": "text", "text": EXTRACTION_PROMPT},
                    ],
                }
            ],
            output_format=ReceiptExtraction,
        )
    except anthropic.AuthenticationError as exc:
        raise ReceiptAnalysisError(
            "La clave de la API de Anthropic no es válida. Revisa ANTHROPIC_API_KEY en el backend."
        ) from exc
    except anthropic.APIStatusError as exc:
        raise ReceiptAnalysisError(f"Claude no pudo analizar el ticket: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise ReceiptAnalysisError(
            "No se pudo conectar con la API de Anthropic para analizar el ticket."
        ) from exc
    except Exception as exc:
        raise ReceiptAnalysisError(f"No se pudo analizar el ticket: {exc}") from exc

    return response.parsed_output


def category_slug_for_item_name(name: str) -> str | None:
    return match_category_for_product_name(name)


def media_type_for_extension(ext: str) -> str:
    return _MEDIA_TYPES.get(ext.lower(), "image/jpeg")
