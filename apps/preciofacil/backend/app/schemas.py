from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class SupermarketOut(BaseModel):
    slug: str
    name: str
    color: str
    logo_emoji: str
    online_store_url: str
    live_verified: bool
    notes: str


class CategoryOut(BaseModel):
    slug: str
    label: str
    icon: str


class ProductPriceOut(BaseModel):
    product_id: int
    supermarket_slug: str
    supermarket_name: str
    supermarket_color: str
    supermarket_emoji: str
    name: str
    brand: Optional[str]
    image_url: Optional[str]
    url: Optional[str]
    unit: Optional[str]
    pack_label: Optional[str]
    price: float
    unit_price: Optional[float]
    is_offer: bool
    previous_price: Optional[float]
    discount_pct: Optional[float]
    scraped_at: datetime


class CategoryComparisonOut(BaseModel):
    category: CategoryOut
    cheapest_price: Optional[float]
    cheapest_supermarket: Optional[str]
    products: list[ProductPriceOut]


class TopOfferOut(BaseModel):
    category: CategoryOut
    product: ProductPriceOut


class PurchaseIn(BaseModel):
    user_email: str
    category_slug: str
    supermarket_slug: str
    product_name: str
    price: float
    quantity: float = 1
    purchased_at: date


class PurchaseOut(BaseModel):
    id: int
    user_email: str
    category_slug: str
    supermarket_slug: str
    product_name: str
    price: float
    quantity: float
    purchased_at: date
    receipt_image_path: Optional[str] = None
    created_at: datetime


class SavingsInsightOut(BaseModel):
    id: int
    category_slug: str
    bought_supermarket_slug: str
    bought_price: float
    cheaper_supermarket_slug: str
    cheaper_price: float
    savings_amount: float
    savings_pct: float
    message: str
    created_at: datetime


class ScrapeSummaryOut(BaseModel):
    summary: dict


class PriceHistoryPointOut(BaseModel):
    scraped_at: datetime
    price: float
    is_offer: bool


class FavoriteIn(BaseModel):
    user_email: str
    category_slug: str


class PriceWatchIn(BaseModel):
    user_email: str
    product_id: int


class TriggeredAlertOut(BaseModel):
    watch_id: int
    product_id: int
    product_name: str
    supermarket_slug: str
    supermarket_name: str
    supermarket_color: str
    supermarket_emoji: str
    watched_price: float
    current_price: float
    savings_amount: float
    is_historic_low: bool


class PriceAlertsStateOut(BaseModel):
    watched_product_ids: list[int]
    triggered: list[TriggeredAlertOut]


class ShoppingListItemIn(BaseModel):
    user_email: str
    category_slug: str


class ShoppingListItemOut(BaseModel):
    id: int
    category_slug: str
    category_label: str
    category_icon: str
    best_supermarket_slug: Optional[str]
    best_supermarket_name: Optional[str]
    best_supermarket_color: Optional[str]
    best_supermarket_emoji: Optional[str]
    best_price: Optional[float]


class ReceiptDraftItemOut(BaseModel):
    name: str
    unit_price: float
    quantity: float
    category_slug: Optional[str]
    category_label: Optional[str]


class ReceiptDraftOut(BaseModel):
    receipt_image_path: str
    supermarket_slug: Optional[str]
    supermarket_name: Optional[str]
    purchase_date: Optional[str]
    total: Optional[float]
    items: list[ReceiptDraftItemOut]
    warning: Optional[str] = None


class ReceiptConfirmItemIn(BaseModel):
    product_name: str
    category_slug: str
    price: float
    quantity: float = 1


class ReceiptConfirmIn(BaseModel):
    user_email: str
    supermarket_slug: str
    purchased_at: date
    receipt_image_path: Optional[str] = None
    items: list[ReceiptConfirmItemIn]


class SupermarketBasketTotalOut(BaseModel):
    supermarket_slug: str
    supermarket_name: str
    supermarket_color: str
    supermarket_emoji: str
    total: float
    items_covered: int
    items_total: int


class ShoppingListPlanOut(BaseModel):
    items: list[ShoppingListItemOut]
    total_optimal: float
    single_stop_supermarket_slug: Optional[str]
    single_stop_supermarket_name: Optional[str]
    single_stop_total: Optional[float]
    savings_amount: Optional[float]
    savings_pct: Optional[float]
    totals_by_supermarket: list[SupermarketBasketTotalOut] = []
