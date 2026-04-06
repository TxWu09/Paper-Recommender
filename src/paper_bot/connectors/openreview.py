"""OpenReview connector."""

from __future__ import annotations

from datetime import datetime, timezone

import requests

from paper_bot.connectors.base import Connector
from paper_bot.models.paper import Paper


class OpenReviewConnector(Connector):
    source_name = "openreview"

    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg

    def fetch(self) -> list[Paper]:
        limit = int(self.cfg.get("limit", 100))
        params = {"limit": limit}
        resp = requests.get(self.cfg["base_url"], params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        notes = payload.get("notes", [])
        papers: list[Paper] = []
        for note in notes:
            content = note.get("content", {})
            title = _pick(content.get("title"))
            abstract = _pick(content.get("abstract"))
            if not title:
                continue
            ts_ms = note.get("cdate") or note.get("tcdate")
            published_at = None
            if isinstance(ts_ms, (int, float)):
                published_at = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
            venue = _pick(content.get("venue"))
            authors = content.get("authors", [])
            if not isinstance(authors, list):
                authors = []
            paper_id = str(note.get("id", title))
            url = f"https://openreview.net/forum?id={paper_id}"
            papers.append(
                Paper(
                    paper_id=paper_id,
                    source=self.source_name,
                    title=title,
                    abstract=abstract,
                    url=url,
                    published_at=published_at,
                    authors=[str(a) for a in authors],
                    venue=venue,
                    metadata={"openreview_note": note},
                )
            )
        return papers


def _pick(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # OpenReview can use {"value": "..."} shape.
        v = value.get("value")
        if isinstance(v, str):
            return v
    return ""
