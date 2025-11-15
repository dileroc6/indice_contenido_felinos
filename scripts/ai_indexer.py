import json
import os
import re
from typing import Any, Dict, Optional

from openai import OpenAI


class AIIndexer:
    """Genera metadata SEO a partir del contenido usando OpenAI."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4.1-mini") -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY no está configurada.")
        self.model = model
        self.client = OpenAI(api_key=self.api_key)

    @staticmethod
    def build_prompt(post: Dict) -> str:
        categories = ", ".join(post.get("category_names", [])) or "Sin categoría"
        return (
            "Eres un estratega SEO especializado en resúmenes ejecutivos. "
            "Analiza el siguiente artículo y responde únicamente en formato JSON válido. "
            "Incluye exactamente las claves: Extracto_200, Keyword_Principal, Keywords_Secundarias, "
            "Intento_de_Búsqueda, Contenido_Relevante, Score_IA. "
            "El campo Keywords_Secundarias debe ser una lista de strings. "
            "El campo Contenido_Relevante debe listar los H2/H3 relevantes como lista. "
            "Score_IA debe ser un número entero entre 0 y 100. "
            "Intento_de_Búsqueda debe ser Informacional, Comercial o Transaccional. "
            "Extracto_200 debe contener máximo 200 caracteres.\n\n"
            f"Título: {post.get('title', '')}\n"
            f"Categorías: {categories}\n"
            f"URL: {post.get('link', '')}\n"
            "Contenido HTML completo:\n"
            f"{post.get('content', '')}"
        )

    @staticmethod
    def _sanitize_response(raw_text: str) -> str:
        content = raw_text.strip()
        if not content:
            raise ValueError("La respuesta de OpenAI llegó vacía.")

        if content.startswith("```"):
            content = content[3:]
            if content.lower().startswith("json"):
                content = content[4:]
            content = content.strip()
            if content.endswith("```"):
                content = content[:-3].strip()

        content = content.replace("***", "").strip()

        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            content = content[start : end + 1]

        return content

    @staticmethod
    def _normalise_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        score = payload.get("Score_IA")
        if isinstance(score, str):
            score = score.strip()
            match = re.search(r"\d+", score)
            if match:
                payload["Score_IA"] = int(match.group())
        elif isinstance(score, (int, float)):
            payload["Score_IA"] = int(score)
        return payload

    def generate_index_fields(self, post: Dict) -> Dict:
        prompt = self.build_prompt(post)
        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": "Eres un analista SEO experto en clasificación de contenido y redacción breve.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        raw_text = response.output_text or ""
        content = self._sanitize_response(raw_text)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"La respuesta de OpenAI no es JSON válido: {content}") from exc
        return self._normalise_payload(parsed)
