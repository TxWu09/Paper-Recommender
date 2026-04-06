"""Core data model for papers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Paper:
    paper_id: str
    source: str
    title: str
    abstract: str
    url: str
    published_at: datetime | None = None
    authors: list[str] = field(default_factory=list)
    orgs: list[str] = field(default_factory=list)
    venue: str = ""
    topics: list[str] = field(default_factory=list)
    code_url: str = ""
    citation_count: int = 0
    social_signal: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class ScoredPaper:
    paper: Paper
    final_score: float
    confidence: str
    score_breakdown: dict[str, float]
    why_selected: str
    risk_flags: list[str]
    summary: str = ""
