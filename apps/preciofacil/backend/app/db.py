from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "preciofacil.db"
DB_PATH = Path(os.environ.get("PRECIOFACIL_DB_PATH", DEFAULT_DB_PATH))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

#: columnas añadidas a tablas ya existentes en despliegues previos.
#: SQLModel.metadata.create_all() solo crea tablas que faltan, nunca altera
#: una tabla existente, así que las columnas nuevas necesitan este pequeño
#: parche manual para no perder los datos ya ingeridos.
_ADDED_COLUMNS = {
    "pricewatch": [("last_notified_price", "REAL")],
}


def _apply_light_migrations() -> None:
    with engine.connect() as conn:
        for table, columns in _ADDED_COLUMNS.items():
            existing = {
                row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))
            }
            for name, sql_type in columns:
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))
        conn.commit()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _apply_light_migrations()


def get_session():
    with Session(engine) as session:
        yield session
