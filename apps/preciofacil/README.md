# PrecioFácil

App móvil (PWA instalable) para comparar precios de supermercados online en
Valencia (CP 46022) y descubrir cuánto puedes ahorrar según lo que compras.

Supermercados soportados: **Mercadona, Consum, Lidl, Carrefour, Aldi y Día**
(más **Kuups**, cadena valenciana sin tienda online pública, que se puede
registrar manualmente). El usuario pidió "Kikos" como sexto supermercado,
pero no existe ninguna cadena española con ese nombre — es un snack de maíz
tostado — así que tras aclararlo se sustituyó por Día y se añadió Kuups.

## Qué hace

- **Crawl4AI analiza los precios reales cada día a las 8:00** (Europe/Madrid,
  vía APScheduler dentro del backend) y guarda un snapshot histórico de
  precios por producto.
- **Ofertas de hoy**: las ofertas más destacadas agrupadas por tipo de
  producto (pasta, leche, fuet, detergente de lavadora, café, huevos...).
- **Comparador**: elige un tipo de producto y ve el precio en todos los
  supermercados, ordenado de más barato a más caro.
- **Mis compras**: registra lo que compras (producto, supermercado, precio,
  fecha).
- **Imágenes reales de producto**: cada producto muestra su foto de
  paquete/envase real. En vez de enlazar en caliente el CDN de cada
  supermercado, el backend descarga y cachea una copia local de la imagen
  de cada producto la primera vez que lo ve (`app/media.py`), y la sirve
  desde `/media/...`. 3.407 de 3.410 productos reales tienen ya su imagen
  descargada.
- **Ahorros**: a partir de tu historial, la app calcula si podrías haber
  ahorrado comprando esa categoría en otro supermercado y te lo dice en
  lenguaje llano ("Compraste pasta en Consum por 1.50€. En Mercadona lo
  tienen desde 0.65€ · ahorrarías 0.85€ (57%) la próxima vez").

## Estado real del scraping en vivo (verificado en este entorno)

| Supermercado | Estado | Técnica | Productos reales |
|---|---|---|---|
| Mercadona | ✅ En vivo | API JSON pública oficial | 957 (59 ofertas) |
| Consum | ✅ En vivo | API JSON pública del buscador | 966 (165 ofertas) |
| Aldi | ✅ En vivo | JSON embebido (Algolia) en páginas de categoría | 561 (29 ofertas) |
| Día | ✅ En vivo | JSON embebido en HTML server-side de categoría | 920 (21 ofertas) |
| Lidl | ⚠️ En vivo, cobertura parcial | Búsqueda renderizada (Playwright) | 7 (3 ofertas) — lidl.es no es un súper online completo, es sobre todo catálogo no-alimentario |
| Carrefour | ❌ Bloqueado desde este sandbox | Cloudflare Turnstile bloquea el acceso automatizado | 0 — código listo, pendiente de ejecutarse desde una IP no bloqueada |
| Kuups | — | Sin tienda online pública | Solo registro manual de compras |

**Total: 3.411 productos reales, 277 ofertas reales**, obtenidos en vivo con
Crawl4AI contra las tiendas online reales, sin datos inventados.

CP 46022 (Valencia): Mercadona resuelve un almacén regional distinto por
código postal (usado en su scraper); Consum, Aldi, Día y Lidl sirven un
catálogo/tarifa nacional único para la venta online, así que el CP no
cambia sus precios (documentado en cada scraper).

## Arquitectura

```
backend/   FastAPI + SQLite + Crawl4AI + APScheduler
  scrapers/    un módulo por supermercado + taxonomía de categorías + registro
  app/         modelos, API REST, motor de recomendación, scheduler diario
frontend/  React + Vite + Tailwind v4, PWA instalable (vite-plugin-pwa)
```

## Cómo ejecutarlo

### Con Docker (recomendado)

```bash
docker compose up --build
```

- Backend: http://localhost:8000 (docs interactivas en `/docs`)
- Frontend: http://localhost:5173

### En local

```bash
# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
python -m app.ingest        # primera carga de precios (opcional, se hace sola a las 8:00)
uvicorn app.main:app --reload

# Frontend (en otra terminal)
cd frontend
npm install
npm run dev
```

El backend arranca su propio scheduler (APScheduler) que ejecuta el scraping
completo cada día a las 8:00 hora de Madrid mientras el proceso esté vivo.
Si prefieres un cron de sistema como alternativa/backup, hay un ejemplo en
`backend/cron/preciofacil-cron`.

Para forzar un scraping manual (por ejemplo para probar): botón
"↻ Actualizar" en la pestaña "Hoy" de la app, o `POST /api/admin/scrape-now`.

## Próximos pasos sugeridos

- Ejecutar el backend desde una IP residencial/no-bloqueada para activar
  también Carrefour (el scraper ya está implementado).
- Afinar la cobertura de Lidl si en el futuro amplía su catálogo de
  alimentación online.
- Sustituir el `user_email` fijo por autenticación real si la app va a tener
  varios usuarios.
