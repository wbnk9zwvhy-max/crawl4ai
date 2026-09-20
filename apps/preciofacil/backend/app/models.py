from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Supermarket(SQLModel, table=True):
    slug: str = Field(primary_key=True)
    name: str
    color: str
    logo_emoji: str = "🛒"
    online_store_url: str = ""
    live_verified: bool = False
    notes: str = ""


class Category(SQLModel, table=True):
    slug: str = Field(primary_key=True)
    label: str
    icon: str


class Product(SQLModel, table=True):
    """Un producto concreto de un supermercado (no está unificado entre
    cadenas: la unificación para comparar ocurre a nivel de categoría)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    supermarket_slug: str = Field(foreign_key="supermarket.slug", index=True)
    external_id: str = Field(index=True)
    category_slug: Optional[str] = Field(default=None, foreign_key="category.slug", index=True)
    name: str
    brand: Optional[str] = None
    image_url: Optional[str] = None
    url: Optional[str] = None
    unit: Optional[str] = None

    __table_args__ = ({"sqlite_autoincrement": True},)


class PriceSnapshot(SQLModel, table=True):
    """Precio de un producto en un momento dado (histórico diario)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id", index=True)
    price: float
    unit_price: Optional[float] = None
    is_offer: bool = False
    previous_price: Optional[float] = None
    discount_pct: Optional[float] = None
    scraped_at: datetime = Field(default_factory=utcnow, index=True)


class Purchase(SQLModel, table=True):
    """Compra registrada manualmente por el usuario para alimentar las
    recomendaciones de ahorro."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_email: str = Field(index=True)
    category_slug: str = Field(foreign_key="category.slug", index=True)
    supermarket_slug: str = Field(foreign_key="supermarket.slug")
    product_name: str
    price: float
    quantity: float = 1
    purchased_at: date
    created_at: datetime = Field(default_factory=utcnow)


class SavingsInsight(SQLModel, table=True):
    """Insight de ahorro generado por el motor de recomendación a partir del
    historial de compras del usuario."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_email: str = Field(index=True)
    category_slug: str = Field(foreign_key="category.slug")
    bought_supermarket_slug: str
    bought_price: float
    cheaper_supermarket_slug: str
    cheaper_price: float
    savings_amount: float
    savings_pct: float
    message: str
    created_at: datetime = Field(default_factory=utcnow, index=True)
