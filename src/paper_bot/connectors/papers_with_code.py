"""Papers With Code connector."""

from __future__ import annotations

from datetime import datetime

import requests

from paper_bot.connectors.base import Connector
from paper_bot.models.paper import Paper


class PapersWithCodeConnector(Connector):
    source_name = "papers_with_code"

    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg

    def fetch(self) -> list[Paper]:
        params = {"page": 1, "items_per_page": int(self.cfg.get("limit", 100))}
        resp = requests.get(self.cfg["base_url"], params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        results = payload.get("results", [])
        papers: list[Paper] = []
        for item in results:
            title = item.get("title", "")
            if not title:
                continue
            published_at = None
            date_raw = item.get("published")
            if isinstance(date_raw, str):
                try:
                    published_at = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
                except ValueError:
                    published_at = None
            papers.append(
                Paper(
                    paper_id=str(item.get("id", title)),
                    source=self.source_name,
                    title=title,
                    abstract=item.get("abstract", "") or "",
                    url=item.get("url_abs", "") or "",
                    published_at=published_at,
                    authors=[],
                    venue=item.get("proceeding", "") or "",
                    code_url=item.get("url", "") or "",
                )
            )
        return papers
