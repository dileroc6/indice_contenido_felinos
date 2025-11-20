import logging
from typing import Dict, List

from ai_indexer import AIIndexer
from google_sheets_client import GoogleSheetsClient
from notifier import TelegramNotifier
from wordpress_client import WordPressClient


logger = logging.getLogger(__name__)


def build_rows(posts: List[Dict], ai_indexer: AIIndexer) -> List[Dict]:
    rows: List[Dict] = []
    for index, post in enumerate(posts, start=1):
        ai_fields = ai_indexer.generate_index_fields(post)
        keywords_sec = ai_fields.get("Keywords_Secundarias", [])
        if isinstance(keywords_sec, str):
            keywords_sec = [item.strip() for item in keywords_sec.split(",") if item.strip()]

        contenido_relevante = ai_fields.get("Contenido_Relevante", [])
        if isinstance(contenido_relevante, str):
            contenido_relevante = [item.strip() for item in contenido_relevante.split("\n") if item.strip()]

        rows.append(
            {
                "URL": post.get("link", ""),
                "Post_ID": post.get("id", ""),
                "Título": post.get("title", ""),
                "Keyword_Principal": ai_fields.get("Keyword_Principal", ""),
                "Keywords_Secundarias": keywords_sec,
                "Categoría": post.get("category_names", []),
                "Extracto_200": ai_fields.get("Extracto_200", ""),
                "Intento_de_Búsqueda": ai_fields.get("Intento_de_Búsqueda", ""),
                "Score_IA": ai_fields.get("Score_IA", ""),
                "Contenido_Relevante": contenido_relevante,
            }
        )
        if index % 10 == 0:
            logger.info("Metadatos generados para %s posts", index)
    return rows


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("Inicio del proceso de construcción de índice")
    notifier = TelegramNotifier()
    posts_count = 0
    inserted_count = 0

    try:
        wordpress_client = WordPressClient()
        ai_indexer = AIIndexer()
        sheets_client = GoogleSheetsClient()

        logger.info("Recuperando posts desde WordPress")
        posts = wordpress_client.fetch_all_posts()
        posts_count = len(posts)
        logger.info("Posts recuperados desde WordPress: %s", posts_count)

        logger.info("Generando metadata con OpenAI")
        rows = build_rows(posts, ai_indexer)
        logger.info("Filas listas para sincronizar en Google Sheets: %s", len(rows))

        logger.info("Sincronizando información en Google Sheets")
        _, inserted_count = sheets_client.upsert_posts(rows)
        logger.info("Proceso completado correctamente")

        notifier.notify(True, posts_count, inserted_count)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error durante la construcción del índice")
        notifier.notify(False, posts_count, inserted_count, str(exc))
        raise


if __name__ == "__main__":
    main()
