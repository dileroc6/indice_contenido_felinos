import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple

import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = "1Hwues5snSJFqJRTzEXFmts3N3OpO0Tgpejub_nosl40"
WORKSHEET_NAME = "indice_contenido"

COLUMNS = [
    "URL",
    "Post_ID",
    "Título",
    "Keyword_Principal",
    "Keywords_Secundarias",
    "Categoría",
    "Extracto_200",
    "Fecha_Última_Actualización",
    "Intento_de_Búsqueda",
    "Score_IA",
    "Contenido_Relevante",
]

logger = logging.getLogger(__name__)


class GoogleSheetsClient:
    """Gestiona la escritura y actualización de filas en Google Sheets."""

    def __init__(
        self,
        service_account_info: Optional[Dict] = None,
        sheet_id: str = SHEET_ID,
        worksheet_name: str = WORKSHEET_NAME,
    ) -> None:
        raw_key = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
        info = service_account_info or (json.loads(raw_key) if raw_key else None)
        if not info:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_KEY no está configurada o es inválida.")
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials.from_service_account_info(info, scopes=scopes)
        self.client = gspread.authorize(credentials)
        self.sheet_id = sheet_id
        self.worksheet_name = worksheet_name

    def _get_worksheet(self) -> gspread.Worksheet:
        spreadsheet = self.client.open_by_key(self.sheet_id)
        return spreadsheet.worksheet(self.worksheet_name)

    def upsert_posts(self, rows: List[Dict]) -> Tuple[int, int]:
        if not rows:
            return (0, 0)
        worksheet = self._get_worksheet()
        self._ensure_header(worksheet)
        existing_records = worksheet.get_all_records()
        index_by_post: Dict[str, int] = {}
        for idx, record in enumerate(existing_records, start=2):
            post_id = str(record.get("Post_ID"))
            if post_id:
                index_by_post[post_id] = idx

        timestamp = datetime.now(timezone.utc).isoformat()

        updates: List[Tuple[int, List[str]]] = []
        new_rows: List[List[str]] = []
        next_row = len(existing_records) + 2

        for row in rows:
            post_id = str(row.get("Post_ID"))
            formatted_row = self._format_row(row, timestamp)
            if post_id in index_by_post:
                row_number = index_by_post[post_id]
                updates.append((row_number, formatted_row))
            else:
                new_rows.append(formatted_row)
                index_by_post[post_id] = next_row
                next_row += 1

        updated_count = 0
        for chunk in self._chunk_updates(updates, size=50):
            data = [
                {
                    "range": f"A{row}:K{row}",
                    "values": [values],
                }
                for row, values in chunk
            ]
            if data:
                worksheet.spreadsheet.values_batch_update(
                    spreadsheetId=worksheet.spreadsheet.id,
                    valueInputOption="USER_ENTERED",
                    body={"data": data},
                )
                updated_count += len(chunk)

        inserted_count = len(new_rows)
        if new_rows:
            worksheet.append_rows(new_rows, value_input_option="USER_ENTERED")

        logger.info(
            "Google Sheets sincronizado: %s filas actualizadas, %s filas insertadas",
            updated_count,
            inserted_count,
        )
        return (updated_count, inserted_count)

    @staticmethod
    def _format_row(row: Dict, timestamp: str) -> List[str]:
        keywords_secundarias = row.get("Keywords_Secundarias", [])
        if isinstance(keywords_secundarias, list):
            keywords_secundarias_str = ", ".join(kw.strip() for kw in keywords_secundarias if kw)
        else:
            keywords_secundarias_str = str(keywords_secundarias)

        contenido_relevante = row.get("Contenido_Relevante", [])
        if isinstance(contenido_relevante, list):
            contenido_relevante_str = "\n".join(block.strip() for block in contenido_relevante if block)
        else:
            contenido_relevante_str = str(contenido_relevante)

        category = row.get("Categoría", [])
        if isinstance(category, list):
            category_str = ", ".join(cat.strip() for cat in category if cat)
        else:
            category_str = str(category) if category else ""

        ordered = {
            "URL": row.get("URL", ""),
            "Post_ID": row.get("Post_ID", ""),
            "Título": row.get("Título", ""),
            "Keyword_Principal": row.get("Keyword_Principal", ""),
            "Keywords_Secundarias": keywords_secundarias_str,
            "Categoría": category_str,
            "Extracto_200": row.get("Extracto_200", ""),
            "Fecha_Última_Actualización": timestamp,
            "Intento_de_Búsqueda": row.get("Intento_de_Búsqueda", ""),
            "Score_IA": row.get("Score_IA", ""),
            "Contenido_Relevante": contenido_relevante_str,
        }
        return [str(ordered[column]) for column in COLUMNS]

    def _ensure_header(self, worksheet: gspread.Worksheet) -> None:
        current_header = worksheet.row_values(1)
        if current_header != COLUMNS:
            worksheet.update("A1:K1", [COLUMNS], value_input_option="RAW")

    @staticmethod
    def _chunk_updates(
        updates: Iterable[Tuple[int, List[str]]], size: int
    ) -> Iterable[List[Tuple[int, List[str]]]]:
        chunk: List[Tuple[int, List[str]]] = []
        for item in sorted(updates, key=lambda pair: pair[0]):
            chunk.append(item)
            if len(chunk) >= size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk
