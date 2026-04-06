"""Connector registry and orchestration."""

from __future__ import annotations

from paper_bot.connectors.arxiv import ArxivConnector
from paper_bot.connectors.openreview import OpenReviewConnector
from paper_bot.connectors.papers_with_code import PapersWithCodeConnector
from paper_bot.connectors.semantic_scholar import SemanticScholarConnector
from paper_bot.models.paper import Paper


def fetch_all_sources(cfg: dict) -> list[Paper]:
    source_cfg = cfg.get("sources", {})
    connectors = []
    if source_cfg.get("arxiv", {}).get("enabled"):
        connectors.append(ArxivConnector(source_cfg["arxiv"]))
    if source_cfg.get("openreview", {}).get("enabled"):
        connectors.append(OpenReviewConnector(source_cfg["openreview"]))
    if source_cfg.get("semantic_scholar", {}).get("enabled"):
        connectors.append(SemanticScholarConnector(source_cfg["semantic_scholar"]))
    if source_cfg.get("papers_with_code", {}).get("enabled"):
        connectors.append(PapersWithCodeConnector(source_cfg["papers_with_code"]))
    papers: list[Paper] = []
    for connector in connectors:
        try:
            papers.extend(connector.fetch())
        except Exception as exc:  # noqa: BLE001
            # Keep pipeline resilient to temporary source failures.
            print(f"[WARN] connector {connector.source_name} failed: {exc}")
    return papers
