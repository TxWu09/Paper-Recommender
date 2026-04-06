"""Semantic Scholar connector."""

from __future__ import annotations

from datetime import datetime

import requests

from paper_bot.connectors.base import Connector
from paper_bot.models.paper import Paper


class SemanticScholarConnector(Connector):
    source_name = "semantic_scholar"

    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg

    def fetch(self) -> list[Paper]:
        params = {
            "query": self.cfg.get("query", "large language model"),
            "limit": int(self.cfg.get("limit", 100)),
            "fields": "title,abstract,url,year,authors,venue,citationCount,externalIds",
        }
        resp = requests.get(self.cfg["base_url"], params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data", [])
        papers: list[Paper] = []
        for item in data:
            title = item.get("title", "")
            if not title:
                continue
            year = item.get("year")
            published_at = None
            if isinstance(year, int):
                published_at = datetime(year, 1, 1)
            authors = [a.get("name", "") for a in item.get("authors", []) if isinstance(a, dict)]
            ext = item.get("externalIds", {}) or {}
            pid = str(ext.get("ArXiv") or ext.get("CorpusId") or title)
            papers.append(
                Paper(
                    paper_id=pid,
                    source=self.source_name,
                    title=title,
                    abstract=item.get("abstract", "") or "",
                    url=item.get("url", "") or "",
                    published_at=published_at,
                    authors=[a for a in authors if a],
                    venue=item.get("venue", "") or "",
                    citation_count=int(item.get("citationCount", 0) or 0),
                )
            )
        return papers
