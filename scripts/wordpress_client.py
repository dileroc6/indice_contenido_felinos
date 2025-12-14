import logging
import os
from typing import Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class WordPressClient:
    """Cliente para interactuar con la API REST de WordPress."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        application_password: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("WORDPRESS_URL", "")).rstrip("/")
        self.username = username or os.getenv("WORDPRESS_USERNAME")
        self.application_password = application_password or os.getenv(
            "WORDPRESS_APPLICATION_PASSWORD"
        )
        self.logger = logging.getLogger(__name__)
        self.timeout = timeout
        if not self.base_url:
            raise ValueError("WORDPRESS_URL no está configurado.")
        if not self.username or not self.application_password:
            raise ValueError("Credenciales de WordPress incompletas.")

        self.session = requests.Session()
        retry_strategy = Retry(
            total=5,
            connect=5,
            read=3,
            backoff_factor=2,
            status_forcelist=(500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _get(self, endpoint: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(
                url,
                auth=(self.username, self.application_password),
                timeout=self.timeout,
                **kwargs,
            )
        except requests.RequestException as exc:
            self.logger.warning("Fallo al conectar con WordPress: %s", exc)
            raise
        response.raise_for_status()
        return response

    def fetch_all_posts(self, per_page: int = 100) -> List[Dict]:
        endpoint = "/wp-json/wp/v2/posts"
        page = 1
        total_pages = 1
        posts: List[Dict] = []
        category_ids: set[int] = set()

        while page <= total_pages:
            params = {"per_page": per_page, "page": page}
            self.logger.info("Solicitando página %s de WordPress", page)
            response = self._get(endpoint, params=params)
            raw_total = response.headers.get("X-WP-TotalPages")
            if raw_total:
                try:
                    total_pages = max(int(raw_total), 1)
                except ValueError:
                    total_pages = 1
            data = response.json()
            for post in data:
                raw_categories = post.get("categories", []) or []
                category_ids.update(raw_categories)
                posts.append(
                    {
                        "id": post.get("id"),
                        "slug": post.get("slug"),
                        "link": post.get("link"),
                        "title": (post.get("title") or {}).get("rendered", ""),
                        "categories": raw_categories,
                        "content": (post.get("content") or {}).get("rendered", ""),
                    }
                )
            page += 1

        category_map = self._fetch_category_map(list(category_ids))
        for post in posts:
            post["category_names"] = [
                category_map.get(category_id, str(category_id))
                for category_id in post.get("categories", [])
            ]
        return posts

    def _fetch_category_map(self, category_ids: List[int]) -> Dict[int, str]:
        if not category_ids:
            return {}
        endpoint = "/wp-json/wp/v2/categories"
        mapping: Dict[int, str] = {}
        chunk_size = 100
        for index in range(0, len(category_ids), chunk_size):
            chunk = category_ids[index : index + chunk_size]
            ids = ",".join(str(category_id) for category_id in chunk)
            response = self._get(endpoint, params={"include": ids, "per_page": len(chunk)})
            categories = response.json()
            for category in categories:
                mapping[category.get("id")] = category.get("name", "")
        return mapping
