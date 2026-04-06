"""arXiv connector."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote_plus
from xml.etree import ElementTree

import requests

from paper_bot.connectors.base import Connector
from paper_bot.models.paper import Paper


class ArxivConnector(Connector):
    source_name = "arxiv"

    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg

    def fetch(self) -> list[Paper]:
        cats = self.cfg.get("categories", [])
        if not cats:
            return []
        query = " OR ".join(f"cat:{c}" for c in cats)
        max_results = int(self.cfg.get("max_results", 100))
        url = (
            f'{self.cfg["base_url"]}?search_query={quote_plus(query)}'
            f"&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
        )
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        root = ElementTree.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        papers: list[Paper] = []
        for entry in root.findall("atom:entry", ns):
            pid = (entry.findtext("atom:id", default="", namespaces=ns) or "").strip()
            title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
            abstract = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
            published_raw = entry.findtext("atom:published", default="", namespaces=ns)
            published_at = None
            if published_raw:
                try:
                    published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
                except ValueError:
                    published_at = None
            authors = [a.findtext("atom:name", default="", namespaces=ns) for a in entry.findall("atom:author", ns)]
            papers.append(
                Paper(
                    paper_id=pid,
                    source=self.source_name,
                    title=title,
                    abstract=abstract,
                    url=pid,
                    published_at=published_at,
                    authors=[a for a in authors if a],
                )
            )
        return papers
