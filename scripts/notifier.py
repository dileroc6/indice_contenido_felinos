import logging
import os
from datetime import datetime
from typing import Optional

import requests
from zoneinfo import ZoneInfo

LOGGER = logging.getLogger(__name__)


class TelegramNotifier:
    """Envía notificaciones de estado vía Telegram si hay configuración."""

    def __init__(self) -> None:
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def notify(
        self,
        success: bool,
        total_posts: int,
        updated_posts: int,
        inserted_posts: int,
        error_message: Optional[str] = None,
    ) -> None:
        if not self.is_configured():
            LOGGER.info("Notificador de Telegram no configurado, se omite el envío.")
            return

        timestamp = self._formatted_now()
        status_icon = "✅" if success else "❌"
        status_text = "Éxito" if success else "Error"
        lines = [
            "🚀 Pipeline Indice Contenido",
            f"📅 Ejecución: {timestamp}",
            f"📝 Posts totales: {total_posts}",
            f"♻️ Filas actualizadas: {updated_posts}",
            f"➕ Nuevos insertados: {inserted_posts}",
            f"{status_icon} Estado: {status_text}",
        ]
        if error_message:
            lines.append(f"⚠️ Detalle: {error_message}")
        message = "\n".join(lines)
        self._send_message(message)

    @staticmethod
    def _formatted_now() -> str:
        bogota_zone = ZoneInfo("America/Bogota")
        now = datetime.now(bogota_zone)
        time_part = now.strftime("%I:%M%p").lstrip("0").lower()
        date_part = now.strftime("%d/%m/%Y")
        return f"{time_part} {date_part}"

    def _send_message(self, message: str) -> None:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message}
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            LOGGER.info("Notificación de Telegram enviada correctamente.")
        except requests.RequestException as exc:
            LOGGER.warning("No se pudo enviar la notificación de Telegram: %s", exc)
