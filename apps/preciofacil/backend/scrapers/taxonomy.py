"""Taxonomía canónica de categorías de producto usada para comparar precios
entre supermercados que, cada uno, organiza su propio catálogo de forma distinta.

Cada categoría canónica lleva:
- ``label``: nombre visible en la app.
- ``icon``: emoji usado en la UI (evita depender de un set de iconos externo).
- ``search_terms``: términos usados para buscar/matchear productos de esa
  categoría dentro del catálogo de cada supermercado (nombre de producto en
  minúsculas, sin acentos, debe contener alguno de estos términos).
- ``mercadona_category_ids``: ids reales de la API pública de Mercadona
  (ver ``mercadona.py``) que caen dentro de esta categoría canónica.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CanonicalCategory:
    slug: str
    label: str
    icon: str
    search_terms: tuple[str, ...]
    mercadona_category_ids: tuple[int, ...] = field(default_factory=tuple)


CANONICAL_CATEGORIES: list[CanonicalCategory] = [
    CanonicalCategory(
        slug="pasta",
        label="Pasta y fideos",
        icon="🍝",
        search_terms=("pasta", "espagueti", "espaguetis", "macarron", "macarrones", "fideo", "fideos", "tallarin", "tallarines", "penne", "lasagna", "lasaña"),
        mercadona_category_ids=(120,),
    ),
    CanonicalCategory(
        slug="arroz",
        label="Arroz",
        icon="🍚",
        search_terms=("arroz",),
        mercadona_category_ids=(118,),
    ),
    CanonicalCategory(
        slug="leche",
        label="Leche",
        icon="🥛",
        search_terms=("leche",),
        mercadona_category_ids=(72,),
    ),
    CanonicalCategory(
        slug="huevos",
        label="Huevos",
        icon="🥚",
        search_terms=("huevo", "huevos"),
        mercadona_category_ids=(77,),
    ),
    CanonicalCategory(
        slug="aceite-oliva",
        label="Aceite de oliva",
        icon="🫒",
        search_terms=("aceite de oliva", "aceite oliva"),
        mercadona_category_ids=(112,),
    ),
    CanonicalCategory(
        slug="fuet-embutido",
        label="Fuet y embutido curado",
        icon="🥓",
        search_terms=("fuet", "salchichon", "salchichón", "chorizo", "longaniza", "embutido", "lomo embuchado", "jamon", "jamón"),
        mercadona_category_ids=(51, 43),
    ),
    CanonicalCategory(
        slug="queso",
        label="Queso",
        icon="🧀",
        search_terms=("queso",),
        mercadona_category_ids=(54, 56, 53),
    ),
    CanonicalCategory(
        slug="pan",
        label="Pan",
        icon="🍞",
        search_terms=("pan ", "pan de molde", "barra de pan", "pan integral"),
        mercadona_category_ids=(59, 60),
    ),
    CanonicalCategory(
        slug="cafe",
        label="Café",
        icon="☕",
        search_terms=("cafe", "café"),
        mercadona_category_ids=(81, 83, 84),
    ),
    CanonicalCategory(
        slug="agua",
        label="Agua",
        icon="💧",
        search_terms=("agua mineral", "agua "),
        mercadona_category_ids=(156,),
    ),
    CanonicalCategory(
        slug="yogures",
        label="Yogures",
        icon="🍦",
        search_terms=("yogur", "yogures"),
        mercadona_category_ids=(103, 104, 108, 109),
    ),
    CanonicalCategory(
        slug="detergente-lavadora",
        label="Detergente de lavadora",
        icon="🧺",
        search_terms=("detergente", "capsulas lavadora", "cápsulas lavadora", "suavizante"),
        mercadona_category_ids=(226,),
    ),
    CanonicalCategory(
        slug="papel-higienico",
        label="Papel higiénico",
        icon="🧻",
        search_terms=("papel higienico", "papel higiénico"),
        mercadona_category_ids=(238,),
    ),
    CanonicalCategory(
        slug="lejia-limpieza",
        label="Lejía y limpiahogar",
        icon="🧴",
        search_terms=("lejia", "lejía", "limpiahogar", "friegasuelos"),
        mercadona_category_ids=(234, 233),
    ),
    CanonicalCategory(
        slug="frutos-secos-snacks",
        label="Frutos secos y snacks",
        icon="🥜",
        search_terms=("frutos secos", "patatas fritas", "kikos", "cacahuete", "pipas"),
        mercadona_category_ids=(133, 132),
    ),
    CanonicalCategory(
        slug="cerveza",
        label="Cerveza",
        icon="🍺",
        search_terms=("cerveza",),
        mercadona_category_ids=(164,),
    ),
]

CATEGORY_BY_SLUG: dict[str, CanonicalCategory] = {c.slug: c for c in CANONICAL_CATEGORIES}


def match_category_for_product_name(name: str) -> str | None:
    """Best-effort matching de un nombre de producto libre a una categoría canónica."""
    normalized = name.lower()
    for category in CANONICAL_CATEGORIES:
        for term in category.search_terms:
            if term in normalized:
                return category.slug
    return None
