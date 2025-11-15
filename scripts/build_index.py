from typing import Dict, List

from ai_indexer import AIIndexer
from google_sheets_client import GoogleSheetsClient
from wordpress_client import WordPressClient


def build_rows(posts: List[Dict], ai_indexer: AIIndexer) -> List[Dict]:
    rows: List[Dict] = []
    for post in posts:
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
    return rows


def main() -> None:
    wordpress_client = WordPressClient()
    ai_indexer = AIIndexer()
    sheets_client = GoogleSheetsClient()

    posts = wordpress_client.fetch_all_posts()
    print(f"Posts recuperados desde WordPress: {len(posts)}")
    rows = build_rows(posts, ai_indexer)
    print(f"Filas a sincronizar en Google Sheets: {len(rows)}")
    sheets_client.upsert_posts(rows)
    print("Proceso completado correctamente.")


if __name__ == "__main__":
    main()
