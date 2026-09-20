from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from .db import engine, init_db
from .ingest import run_daily_scrape, sync_static_tables
from .routers import categories, insights, offers, products, purchases, supermarkets
from .scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with Session(engine) as session:
        sync_static_tables(session)
    start_scheduler()
    yield


app = FastAPI(title="PrecioFácil API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(supermarkets.router)
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(offers.router)
app.include_router(purchases.router)
app.include_router(insights.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/admin/scrape-now")
async def scrape_now():
    """Lanza manualmente el mismo scraping que corre cada día a las 8:00."""
    summary = await run_daily_scrape()
    return {"summary": summary}
