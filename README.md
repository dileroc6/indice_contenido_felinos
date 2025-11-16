# indice_contenido_felinos

Pipeline automatizado que, cada semana o a demanda, toma todos los posts de tu WordPress, usa OpenAI para generar resumen y metadata SEO, y actualiza la hoja `SEOMasterDashboard_Felinos/indice_contenido` en Google Sheets duplicando/actualizando filas según `Post_ID`; todo corre vía GitHub Actions con Python 3.11 y depende de secretos para WordPress, OpenAI y el service account de Google.

## Estructura del proyecto

- `.github/workflows/build-indice.yml`: Workflow de GitHub Actions responsable de ejecutar el pipeline de manera programada o manual.
- `requirements.txt`: Dependencias necesarias para ejecutar los scripts en Python.
- `scripts/`
	- `build_index.py`: Script orquestador que coordina la obtención de posts, enriquecimiento con IA y escritura en Google Sheets.
	- `wordpress_client.py`: Cliente para consumir la API REST de WordPress y manejar la paginación.
	- `ai_indexer.py`: Encapsula la llamada a OpenAI y la generación del prompt por post.
	- `google_sheets_client.py`: Gestiona la inserción y actualización de filas en la hoja de cálculo.

## Flujo general

1. El workflow se activa cada lunes a las `04:00 UTC` (`domingo 23:00` hora de Bogotá) o mediante `workflow_dispatch`.
2. Se instalan las dependencias listadas en `requirements.txt`.
3. `build_index.py` crea clientes para WordPress, OpenAI y Google Sheets.
4. Se consultan todos los posts vía `/wp-json/wp/v2/posts?per_page=100`, gestionando la paginación con `X-WP-TotalPages`.
5. Por cada post se solicita a OpenAI el siguiente JSON:

```json
{
	"Extracto_200": "<máx. 200 caracteres>",
	"Keyword_Principal": "<keyword foco>",
	"Keywords_Secundarias": ["..."],
	"Intento_de_Búsqueda": "Informacional | Comercial | Transaccional",
	"Contenido_Relevante": ["Listado de H2/H3"],
	"Score_IA": 0
}
```

### Prompt completo utilizado con OpenAI

```text
Eres un estratega SEO especializado en resúmenes ejecutivos. Analiza el siguiente artículo y responde únicamente en formato JSON válido. Incluye exactamente las claves: Extracto_200, Keyword_Principal, Keywords_Secundarias, Intento_de_Búsqueda, Contenido_Relevante, Score_IA. El campo Keywords_Secundarias debe ser una lista de strings. El campo Contenido_Relevante debe listar los H2/H3 relevantes como lista. Score_IA debe ser un número entero entre 0 y 100. Intento_de_Búsqueda debe ser Informacional, Comercial o Transaccional. Extracto_200 debe contener máximo 200 caracteres.

Título: {{title}}
Categorías: {{categories}}
URL: {{url}}
Contenido HTML completo:
{{content}}
```

6. Se genera la fila con las columnas requeridas:
   - `URL`
   - `Post_ID`
   - `Título`
   - `Keyword_Principal`
   - `Keywords_Secundarias`
   - `Categoría`
   - `Extracto_200`
   - `Fecha_Última_Actualización` (ISO UTC)
   - `Intento_de_Búsqueda`
   - `Score_IA`
   - `Contenido_Relevante`
7. `google_sheets_client.py` actualiza la fila existente si el `Post_ID` ya está en la hoja o agrega una nueva si no existe.

## Variables de entorno / Secrets

Configura los siguientes secretos en el repositorio de GitHub (`Settings` → `Secrets and variables` → `Actions`):

- `WORDPRESS_URL`
- `WORDPRESS_USERNAME`
- `WORDPRESS_APPLICATION_PASSWORD`
- `GOOGLE_SERVICE_ACCOUNT_KEY` (JSON completo del service account)
- `OPENAI_API_KEY`

Asegúrate de compartir la hoja `SEOMasterDashboard_Felinos` con el correo del service account.

## Ejecución local

1. Clona el repositorio y crea/activa un entorno virtual de Python 3.11.
2. Instala dependencias: `pip install -r requirements.txt`.
3. Exporta las variables de entorno necesarias:

```bash
export WORDPRESS_URL="https://tu-sitio.com"
export WORDPRESS_USERNAME="usuario"
export WORDPRESS_APPLICATION_PASSWORD="app-password"
export GOOGLE_SERVICE_ACCOUNT_KEY='{"type":"service_account",...}'
export OPENAI_API_KEY="sk-..."
```

4. Ejecuta el pipeline: `python scripts/build_index.py`.

## Workflow de GitHub Actions

El archivo `.github/workflows/build-indice.yml` incluye:

- Programación con cron `0 9 1 * *` (primer día de cada mes 09:00 UTC / 04:00 Bogotá).
- Activación manual con `workflow_dispatch`.
- Instalación automática de dependencias.
- Ejecución del script principal con los secretos expuestos como variables de entorno.

## Próximos pasos sugeridos

- Añadir manejo de reintentos o colas para llamadas a OpenAI ante errores transitorios.
- Implementar registros más detallados y almacenamiento intermedio para auditoría.
- Programar pruebas unitarias y automatizarlas dentro del workflow.
