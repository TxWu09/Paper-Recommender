"""Ingest and dedup pipeline."""

from __future__ import annotations

from collections.abc import Iterable

from paper_bot.models.paper import Paper
from paper_bot.topic_taxonomy import TopicTaxonomy
from paper_bot.utils.text import title_similarity


def deduplicate_papers(papers: Iterable[Paper], similarity_threshold: float = 0.95) -> list[Paper]:
    unique: list[Paper] = []
    seen_ids: set[str] = set()
    for paper in papers:
        key = _identity_key(paper)
        if key and key in seen_ids:
            continue
        near_dup = False
        for existing in unique:
            if title_similarity(paper.title, existing.title) >= similarity_threshold:
                near_dup = True
                break
        if near_dup:
            continue
        if key:
            seen_ids.add(key)
        unique.append(paper)
    return unique


def tag_topics(papers: Iterable[Paper], taxonomy: TopicTaxonomy) -> list[Paper]:
    tagged: list[Paper] = []
    for paper in papers:
        text = f"{paper.title}\n{paper.abstract}"
        paper.topics = taxonomy.match_topics(text)
        tagged.append(paper)
    return tagged


def _identity_key(paper: Paper) -> str:
    pid = (paper.paper_id or "").lower().strip()
    url = (paper.url or "").lower().strip()
    if "arxiv.org/abs/" in url:
        return url.split("arxiv.org/abs/")[-1]
    return pid
