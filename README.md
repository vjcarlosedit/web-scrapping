# Price Scraper Dashboard

Sistema de web scraping para rastrear precios de productos en Amazon y Mercado Libre con visualización de tendencias históricas.

## Características

- 🔍 Scraping de precios de Amazon y Mercado Libre
- 📊 Dashboard web con gráficos de tendencia de precios
- 💾 Almacenamiento histórico en base de datos SQLite
- ⏰ Ejecución automática diaria programada
- 🚀 API REST con FastAPI
- 📈 Visualización con Chart.js

## Tecnologías Utilizadas

**Backend:**
- Python 3.10+
- FastAPI - API REST
- SQLAlchemy - ORM
- BeautifulSoup4 - Web scraping
- APScheduler - Tareas programadas
- SQLite - Base de datos

**Frontend:**
- HTML/CSS/JavaScript
- Chart.js - Gráficos

## Instalación

### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd web-scrapping
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Copia el archivo `.env.example` y renómbralo a `.env`, luego ajusta los valores según tus necesidades.

## Uso

### Iniciar el servidor

```bash
python -m uvicorn backend.api.main:app --reload
```

El servidor estará disponible en `http://localhost:8000`

### Acceder al dashboard

Abre tu navegador y visita:
- Dashboard: `http://localhost:8000/`
- API Docs (Swagger): `http://localhost:8000/docs`

### Añadir productos para rastrear

1. Abre el dashboard
2. Usa el formulario "Añadir Producto"
3. Ingresa la URL del producto (Amazon o Mercado Libre)
4. El sistema detectará automáticamente la plataforma y comenzará a rastrear

### Scraping manual

Puedes ejecutar el scraping manualmente desde:
- Dashboard: Botón "Ejecutar Scraping Ahora"
- API: `POST http://localhost:8000/scrape/run`

### Scraping automático

El sistema está configurado para ejecutar scraping automáticamente todos los días a las 8:00 AM (configurable en `.env`).

## Estructura del Proyecto

```
web-scrapping/
├── backend/
│   ├── scraper/
│   │   ├── base.py            # Clase base para scrapers
│   │   ├── mercadolibre.py    # Scraper de Mercado Libre
│   │   └── amazon.py          # Scraper de Amazon
│   ├── database/
│   │   ├── models.py          # Modelos SQLAlchemy
│   │   └── db.py              # Conexión y operaciones
│   ├── api/
│   │   └── main.py            # FastAPI endpoints
│   ├── scheduler/
│   │   └── jobs.py            # Tareas programadas
│   └── config.py              # Configuración
├── frontend/
│   ├── index.html             # Dashboard principal
│   ├── styles.css             # Estilos
│   └── app.js                 # Lógica del frontend
├── data/
│   └── prices.db              # Base de datos SQLite
└── requirements.txt           # Dependencias Python
```

## API Endpoints

- `GET /` - Dashboard web
- `GET /products` - Listar productos rastreados
- `POST /products` - Añadir nuevo producto
- `DELETE /products/{id}` - Eliminar producto
- `GET /products/{id}/history` - Histórico de precios
- `POST /scrape/run` - Ejecutar scraping manual
- `GET /stats` - Estadísticas generales

## Consideraciones Legales

- **Mercado Libre**: Este proyecto usa la API oficial pública de Mercado Libre
- **Amazon**: El scraping de Amazon debe usarse solo para fines educativos y personales
- **Rate Limiting**: El sistema respeta delays entre requests para no sobrecargar los servidores
- **Robots.txt**: Se respetan las directivas de cada sitio

## Mejoras Futuras

- [ ] Sistema de alertas por email/Telegram
- [ ] Comparador de precios entre plataformas
- [ ] Exportar datos a CSV/Excel
- [ ] Autenticación de usuarios
- [ ] Soporte para más plataformas (eBay, AliExpress)

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue primero para discutir los cambios que te gustaría hacer.

## Licencia

Este proyecto es solo para fines educativos y uso personal.

