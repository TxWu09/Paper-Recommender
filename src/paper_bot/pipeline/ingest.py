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


def filter_by_selected_topics(papers: Iterable[Paper], selected_topics: list[str] | None) -> list[Paper]:
    if not selected_topics:
        return list(papers)
    selected = {x.strip().lower() for x in selected_topics if x.strip()}
    filtered: list[Paper] = []
    for paper in papers:
        paper.topics = [t for t in paper.topics if t.lower() in selected]
        if paper.topics:
            filtered.append(paper)
    return filtered


def filter_by_keyword_substrings(papers: Iterable[Paper], keywords: list[str] | None) -> list[Paper]:
    """Keep papers whose title+abstract contains any of the given phrases (case-insensitive)."""
    if not keywords:
        return list(papers)
    needles = [k.strip().lower() for k in keywords if k.strip()]
    if not needles:
        return list(papers)
    filtered: list[Paper] = []
    for paper in papers:
        text = f"{paper.title}\n{paper.abstract}".lower()
        if any(n in text for n in needles):
            filtered.append(paper)
    return filtered


def _identity_key(paper: Paper) -> str:
    pid = (paper.paper_id or "").lower().strip()
    url = (paper.url or "").lower().strip()
    if "arxiv.org/abs/" in url:
        return url.split("arxiv.org/abs/")[-1]
    return pid
