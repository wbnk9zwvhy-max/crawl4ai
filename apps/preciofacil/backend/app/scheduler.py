from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session

from .db import engine
from .ingest import run_daily_scrape
from .push import notify_triggered_alerts_for_all_users

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Europe/Madrid")


async def _scheduled_job() -> None:
    logger.info("Ejecutando scraping diario programado (08:00 Europe/Madrid)")
    summary = await run_daily_scrape()
    logger.info("Scraping diario completado: %s", summary)
    with Session(engine) as session:
        sent = notify_triggered_alerts_for_all_users(session)
    if sent:
        logger.info("Notificaciones push de alertas de precio enviadas: %s", sent)


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        _scheduled_job,
        trigger=CronTrigger(hour=8, minute=0),
        id="daily_price_scrape",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler iniciado: scraping diario a las 08:00 (Europe/Madrid)")
