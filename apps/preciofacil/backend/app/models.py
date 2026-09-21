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
    #: ruta relativa servida bajo /media una vez descargada la imagen
    #: original del producto (ver app/media.py); None si aún no se ha
    #: descargado o la descarga falló.
    image_path: Optional[str] = None
    url: Optional[str] = None
    unit: Optional[str] = None
    #: cantidad/tamaño de envase normalizado (ver app/product_matching.py),
    #: usado para reconocer "el mismo producto" en otros supermercados:
    #: docena de huevos -> (12, "ud"), paquete de pasta 500 g -> (500, "g")...
    pack_qty: Optional[float] = Field(default=None, index=True)
    pack_unit: Optional[str] = Field(default=None, index=True)

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
    #: ruta relativa bajo /media de la foto del ticket, si esta compra vino
    #: de un ticket escaneado (ver app/receipt_analysis.py).
    receipt_image_path: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class ShoppingListItem(SQLModel, table=True):
    """Un tipo de producto (categoría canónica) que el usuario quiere
    comprar. La app calcula en qué supermercado sale más barato cada uno y
    el reparto óptimo de toda la lista (ver app/shopping_list.py)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_email: str = Field(index=True)
    category_slug: str = Field(foreign_key="category.slug", index=True)
    created_at: datetime = Field(default_factory=utcnow)


class Favorite(SQLModel, table=True):
    """Categoría marcada como favorita por el usuario: sus ofertas aparecen
    primero en la portada."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_email: str = Field(index=True)
    category_slug: str = Field(foreign_key="category.slug", index=True)
    created_at: datetime = Field(default_factory=utcnow)


class PriceWatch(SQLModel, table=True):
    """Un producto que el usuario quiere vigilar: se avisa en la app cuando
    su precio baja del que tenía cuando se empezó a seguir, o toca mínimo
    histórico (ver app/price_alerts.py)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_email: str = Field(index=True)
    product_id: int = Field(foreign_key="product.id", index=True)
    watched_price: float
    #: último precio por el que ya se envió una notificación push para este
    #: seguimiento, para no reenviar el mismo aviso cada vez que corre el
    #: scraping (ver app/push.py). None si aún no se ha notificado nunca.
    last_notified_price: Optional[float] = None
    created_at: datetime = Field(default_factory=utcnow)


class PushSubscription(SQLModel, table=True):
    """Suscripción push del navegador de un usuario (Web Push API), guardada
    para poder enviarle notificaciones de alertas de precio aunque no tenga
    la app abierta. No hay servidor de push propio: se envía a través del
    servicio de push del navegador (FCM, Mozilla push, etc.) usando claves
    VAPID (ver app/push.py)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_email: str = Field(index=True)
    endpoint: str = Field(index=True, unique=True)
    p256dh: str
    auth: str
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
