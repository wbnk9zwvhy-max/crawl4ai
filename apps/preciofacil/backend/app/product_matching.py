"""Reconocimiento de "mismo producto" entre supermercados.

No tenemos EAN/código de barras homogéneo entre cadenas (y aunque lo
tuviéramos, la mayoría de productos de gran consumo — huevos, pasta,
detergente... — son marca blanca de cada supermercado, así que ni el EAN
resolvería "es literalmente el mismo producto"). Lo que sí podemos hacer,
y es lo que pidió el usuario con el ejemplo de "media docena de huevos", es
reconocer que dos productos son del mismo TIPO y FORMATO (misma categoría +
misma cantidad/tamaño de envase: docena, media docena, 500 g, 1 L...) y
compararlos como equivalentes.

Estrategia:
1. ``parse_pack_size`` extrae cantidad + unidad ("ud", "g", "ml") del texto
   del nombre del producto o del campo de unidad que ya capturan los
   scrapers (docena, media docena, "X unidades", "500 g", "1 L", "pack de
   4 x 100 g"...).
2. ``is_plausible_match`` es una red de seguridad barata para no juntar dos
   productos del mismo formato pero de tipo claramente distinto dentro de
   la misma categoría (el caso real que nos encontramos: "Huevo de
   Chocolate con Sorpresa" cae en la categoría "huevos" por contener la
   palabra "huevo", pero no es el mismo producto que huevos frescos).
"""
from __future__ import annotations

import re
import unicodedata

STOPWORDS = {
    "de", "la", "el", "los", "las", "con", "sin", "en", "para", "y", "del",
    "al", "a", "un", "una", "unas", "unos", "o", "por",
    "paquete", "botella", "bandeja", "bote", "lata", "tarrina", "garrafa",
    "pack", "unidad", "unidades", "ud", "uds", "docena", "decena", "gr",
    "g", "kg", "ml", "l", "x", "tetrabrik", "brik",
}

_MEDIA_DOCENA_RE = re.compile(r"media\s+docena|1\s*/\s*2\s*docena", re.I)
_DOCENA_RE = re.compile(r"\bdocena\b", re.I)
_DECENA_RE = re.compile(r"\bdecena\b", re.I)
_UNIDADES_RE = re.compile(r"(\d+)\s*(?:unidades|uds?\.?)\b", re.I)
_PACK_MULTI_RE = re.compile(
    r"(?:pack\s+de\s+)?(\d+)\s*x\s*(\d+(?:[.,]\d+)?)\s*(kg|g|gr|gramos|ml|l|litros?)\b", re.I
)
_KG_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*kg\b", re.I)
_G_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:g|gr|gramos)\b", re.I)
_L_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:l|litros?)\b", re.I)
_ML_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*ml\b", re.I)


def _num(s: str) -> float:
    return float(s.replace(",", "."))


def parse_pack_size(*texts: str | None) -> tuple[float, str] | None:
    """Prueba a extraer (cantidad, unidad) del primer texto que dé un
    resultado; ``unidad`` es "ud", "g" o "ml"."""
    for text in texts:
        if not text:
            continue
        result = _parse_one(text)
        if result:
            return result
    return None


def _parse_one(text: str) -> tuple[float, str] | None:
    if _MEDIA_DOCENA_RE.search(text):
        return (6.0, "ud")
    m = _PACK_MULTI_RE.search(text)
    if m:
        count = float(m.group(1))
        each = _num(m.group(2))
        unit = m.group(3).lower()
        if unit == "kg":
            return (count * each * 1000, "g")
        if unit in ("l", "litro", "litros"):
            return (count * each * 1000, "ml")
        if unit == "ml":
            return (count * each, "ml")
        return (count * each, "g")
    m = _UNIDADES_RE.search(text)
    if m:
        return (float(m.group(1)), "ud")
    if _DOCENA_RE.search(text):
        return (12.0, "ud")
    if _DECENA_RE.search(text):
        return (10.0, "ud")
    m = _KG_RE.search(text)
    if m:
        return (_num(m.group(1)) * 1000, "g")
    m = _L_RE.search(text)
    if m:
        return (_num(m.group(1)) * 1000, "ml")
    m = _ML_RE.search(text)
    if m:
        return (_num(m.group(1)), "ml")
    m = _G_RE.search(text)
    if m:
        return (_num(m.group(1)), "g")
    return None


def round_pack(qty: float, unit: str) -> float:
    """Redondeo para que envases casi idénticos (499 g vs 500 g) agrupen
    igual; docenas de huevos se dejan exactas."""
    if unit == "ud":
        return round(qty)
    step = 5 if qty < 200 else (10 if qty < 1000 else 50)
    return round(qty / step) * step


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def _normalize_word(word: str) -> str:
    if len(word) > 4 and word.endswith("s"):
        return word[:-1]
    return word


def normalize_tokens(text: str, extra_stopwords: set[str] = frozenset()) -> set[str]:
    text = _strip_accents(text.lower())
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = set()
    for raw in text.split():
        if not raw or raw.isdigit() or len(raw) <= 2:
            continue
        word = _normalize_word(raw)
        if word in STOPWORDS or word in extra_stopwords:
            continue
        tokens.add(word)
    return tokens


def is_plausible_match(name_a: str, name_b: str, category_search_terms: tuple[str, ...]) -> bool:
    """Filtro barato para no juntar productos del mismo formato pero de tipo
    claramente distinto (p.ej. huevos de chocolate vs huevos frescos).

    Si tras quitar las palabras propias de la categoría (p.ej. "huevo",
    "huevos") a alguno de los dos nombres no le queda ningún token
    distintivo, no hay señal suficiente para descartar el match y se acepta
    (caso típico: Mercadona llama a un producto simplemente "Huevos").
    Si a ambos les quedan tokens y no comparten ninguno, se descarta.
    """
    category_tokens: set[str] = set()
    for term in category_search_terms:
        category_tokens |= normalize_tokens(term)

    tokens_a = normalize_tokens(name_a) - category_tokens
    tokens_b = normalize_tokens(name_b) - category_tokens
    if not tokens_a or not tokens_b:
        return True
    return bool(tokens_a & tokens_b)


def format_pack(qty: float, unit: str) -> str:
    """Texto legible del formato, para mostrar por qué dos productos de
    supermercados distintos se consideran "el mismo producto"."""
    if unit == "ud":
        if qty == 12:
            return "docena"
        if qty == 6:
            return "media docena"
        if qty == 10:
            return "decena"
        return f"{int(qty)} uds"
    if unit == "g":
        if qty >= 1000:
            kg = qty / 1000
            return f"{kg:g} kg"
        return f"{int(qty)} g"
    if unit == "ml":
        if qty >= 1000:
            liters = qty / 1000
            return f"{liters:g} L"
        return f"{int(qty)} ml"
    return f"{qty:g} {unit}"


def resolve_pack_for_item(name: str, unit_hint: str | None, pack_qty: float | None, pack_unit: str | None) -> tuple[float, str] | None:
    """Cantidad/unidad final de un producto: usa la que haya fijado el
    propio scraper (más fiable cuando la tienda no la escribe en el nombre,
    como Mercadona) o, si no, intenta extraerla del nombre / del texto de
    unidad."""
    if pack_qty is not None and pack_unit is not None:
        return (round_pack(pack_qty, pack_unit), pack_unit)
    parsed = parse_pack_size(name, unit_hint)
    if not parsed:
        return None
    qty, unit = parsed
    return (round_pack(qty, unit), unit)
