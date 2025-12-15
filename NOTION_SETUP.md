# 📝 Configuración de Integración con Notion

Esta guía te ayudará a conectar tu Price Tracker con Notion para visualizar los precios en una base de datos de Notion.

## 🎯 Lo Que Obtendrás

Una base de datos en Notion con:
- **Nombre**: Nombre del producto
- **Plataforma**: Amazon o Mercado Libre
- **URL**: Link directo al producto
- **Fecha Actualización**: Última vez que se revisó el precio
- **Precio Actual**: Precio más reciente
- **Fecha Descuento**: Cuándo tuvo el precio más bajo
- **Precio Descuento**: El precio más bajo registrado
- **Moneda**: MXN, USD, etc.

### 📊 Ejemplo Visual:

```
┌─────────────────┬────────────┬────────────────┬─────────────┬────────────┐
│ Nombre          │ Plataforma │ Precio Actual  │ Precio Desc │ Moneda     │
├─────────────────┼────────────┼────────────────┼─────────────┼────────────┤
│ iPhone 15 256GB │ ML         │ 13,435.80      │ 13,435.80   │ MXN        │
│ OPPO A5 Pro     │ ML         │ 4,999.00       │ 4,999.00    │ MXN        │
└─────────────────┴────────────┴────────────────┴─────────────┴────────────┘
```

## 📋 Pasos de Configuración

### 1️⃣ Crear Integración en Notion

1. Ve a: https://www.notion.so/my-integrations
2. Haz clic en **"+ New integration"**
3. Configura:
   - **Name**: `Price Tracker` (o el nombre que prefieras)
   - **Associated workspace**: Selecciona tu workspace
   - **Type**: Internal
4. Haz clic en **"Submit"**
5. **COPIA EL TOKEN** que aparece (comienza con `secret_...`)
   - ⚠️ Guárdalo en un lugar seguro, lo necesitarás después

### 2️⃣ Crear Base de Datos en Notion

1. Abre Notion y crea una nueva página
2. Escribe `/database` y selecciona **"Table - Inline"**
3. Nombra la tabla: **"Price Tracker"** (o como prefieras)

### 3️⃣ Configurar Propiedades de la Base de Datos

Necesitas crear exactamente estas columnas (respeta mayúsculas/minúsculas):

| Nombre de Columna | Tipo de Propiedad | Notas |
|-------------------|-------------------|-------|
| `Nombre` | Title | Ya existe por defecto |
| `Plataforma` | Select | Añade opciones: "Amazon", "Mercado Libre" |
| `URL` | URL | |
| `Fecha Actualización` | Date | |
| `Precio Actual` | Number | |
| `Fecha Descuento` | Date | |
| `Precio Descuento` | Number | |
| `Moneda` | Text | |

#### Cómo Añadir Columnas:

1. Haz clic en el **"+"** a la derecha de la última columna
2. Escribe el nombre exacto
3. Selecciona el tipo de propiedad

### 4️⃣ Conectar la Integración a la Base de Datos

1. En tu base de datos de Notion, haz clic en los **tres puntos** (⋯) arriba a la derecha
2. Selecciona **"Connect to"**
3. Busca y selecciona tu integración **"Price Tracker"**

### 5️⃣ Obtener el Database ID

El Database ID está en la URL de tu base de datos:

```
https://www.notion.so/miworkspace/1234567890abcdef1234567890abcdef?v=...
                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                 Este es tu DATABASE_ID
```

**Ejemplo completo:**
```
URL: https://www.notion.so/myworkspace/32charDatabaseID?v=viewID
Database ID: 32charDatabaseID (32 caracteres hexadecimales)
```

### 6️⃣ Configurar Variables de Entorno

Edita tu archivo `.env` y añade:

```env
# Notion Integration
NOTION_ENABLED=true
NOTION_TOKEN=secret_tu_token_aqui_que_copiaste_en_paso_1
NOTION_DATABASE_ID=tu_database_id_de_32_caracteres
```

**Ejemplo real:**
```env
NOTION_ENABLED=true
NOTION_TOKEN=secret_1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9S0T1U2V3W4X
NOTION_DATABASE_ID=1234567890abcdef1234567890abcdef
```

### 7️⃣ Instalar Dependencias

```bash
pip install notion-client
```

O reinstala todo:

```bash
pip install -r requirements.txt
```

### 8️⃣ Reiniciar el Servidor

```bash
# Detén el servidor actual (Ctrl+C)
# Inicia de nuevo
python run.py
```

## ✅ Verificar que Funciona

### Opción 1: Scraping Manual

1. Abre el dashboard: http://localhost:8000
2. Haz clic en **"🔄 Actualizar Todos"**
3. Ve a tu base de datos de Notion
4. ¡Deberías ver tus productos aparecer! 🎉

### Opción 2: Añadir Producto Nuevo

1. Añade un producto desde el dashboard
2. Automáticamente se sincronizará con Notion

## 🔄 Sincronización Automática

Una vez configurado, la sincronización ocurre automáticamente:

✅ **Después del scraping diario** (8:00 AM por defecto)
✅ **Cuando añades un nuevo producto**
✅ **Cuando actualizas manualmente un producto**

## 🎨 Personalización en Notion

Puedes personalizar la vista en Notion:

### Crear Vista de Tabla
- Ordena por "Precio Actual" (descendente)
- Filtra por "Plataforma"
- Agrupa por "Plataforma"

### Crear Vista de Galería
- Muestra las imágenes de productos
- Tarjetas con precio actual

### Crear Vista de Calendario
- Por "Fecha Actualización"
- Ver cuándo se actualizaron precios

## 🐛 Solución de Problemas

### Error: "Could not connect to Notion"

**Causa**: Token o Database ID incorrectos

**Solución:**
1. Verifica que el token comience con `secret_`
2. Verifica que el Database ID tenga exactamente 32 caracteres
3. Asegúrate de que la integración esté conectada a la base de datos

### Error: "Property not found"

**Causa**: Los nombres de las columnas no coinciden exactamente

**Solución:**
1. Ve a tu base de datos en Notion
2. Verifica que TODOS los nombres sean exactos (con mayúsculas/minúsculas)
3. Propiedades requeridas:
   - `Nombre` (Title)
   - `Plataforma` (Select)
   - `URL` (URL)
   - `Fecha Actualización` (Date)
   - `Precio Actual` (Number)
   - `Fecha Descuento` (Date)
   - `Precio Descuento` (Number)
   - `Moneda` (Text)

### Los productos no aparecen en Notion

**Verifica:**

1. ¿Está `NOTION_ENABLED=true` en `.env`?
2. ¿Reiniciaste el servidor después de configurar?
3. Revisa los logs del servidor para errores de Notion
4. Verifica que la integración tenga permisos en la base de datos

## 📊 Ver Logs de Sincronización

Los logs mostrarán:

```
✓ Notion connection validated successfully
Starting Notion sync for 3 products
✓ Updated product in Notion: iPhone 15 256GB
✓ Updated product in Notion: OPPO A5 Pro
✓ Notion sync completed: 3/3 synced
```

## 🎯 Ventajas de la Integración

✅ **Visualización intuitiva** - Ve todos tus productos en un solo lugar
✅ **Historial de precio más bajo** - Siempre sabes cuál fue el mejor precio
✅ **Acceso desde cualquier lugar** - Notion en web, móvil, desktop
✅ **Vistas personalizables** - Crea tablas, galerías, calendarios
✅ **Compartible** - Puedes compartir la base de datos con otros
✅ **Sincronización automática** - Sin intervención manual

## 🔐 Seguridad

- ⚠️ **NUNCA compartas tu NOTION_TOKEN**
- ⚠️ El token es sensible, manténlo en `.env` (que está en `.gitignore`)
- ✅ Si comprometes el token, genera uno nuevo en Notion

## 📚 Recursos Adicionales

- [Notion API Docs](https://developers.notion.com/)
- [Crear Integraciones](https://www.notion.so/help/create-integrations-with-the-notion-api)
- [notion-client Python](https://github.com/ramnes/notion-sdk-py)

## 💡 Tips Avanzados

### Fórmulas en Notion

Puedes añadir columnas calculadas:

**% de Descuento desde Precio Más Bajo:**
```
round(((prop("Precio Descuento") - prop("Precio Actual")) / prop("Precio Descuento")) * 100)
```

**Ahorro:**
```
prop("Precio Descuento") - prop("Precio Actual")
```

### Notificaciones

Configura notificaciones en Notion para cuando:
- Un producto baje de precio
- Se actualice un producto
- El precio alcance un objetivo

---

¿Necesitas ayuda? Revisa los logs del servidor o abre un issue en GitHub.

