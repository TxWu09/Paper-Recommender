"""Quality scoring engine."""

from __future__ import annotations

import math

from paper_bot.models.paper import Paper, ScoredPaper

TOP_VENUE_HINTS = {
    "iclr",
    "neurips",
    "icml",
    "acl",
    "emnlp",
    "naacl",
    "tmlr",
    "nature",
    "science",
}

STRONG_ORG_HINTS = {
    "openai",
    "google",
    "deepmind",
    "meta",
    "microsoft",
    "stanford",
    "mit",
    "cmu",
    "tsinghua",
    "pku",
}


class QualityEngine:
    def __init__(self, config: dict, feedback_adjustments: dict[str, float] | None = None) -> None:
        self.weights = config.get("scoring", {}).get("weights", {})
        self.feedback_adjustments = feedback_adjustments or {}

    def score_many(self, papers: list[Paper]) -> list[ScoredPaper]:
        out = [self.score_one(p) for p in papers]
        return sorted(out, key=lambda x: x.final_score, reverse=True)

    def score_one(self, paper: Paper) -> ScoredPaper:
        breakdown = {
            "topic_fit": self.topic_fit(paper),
            "venue_signal": self.venue_signal(paper),
            "author_org_signal": self.author_org_signal(paper),
            "impact_signal": self.impact_signal(paper),
            "method_novelty": self.method_novelty(paper),
            "evidence_strength": self.evidence_strength(paper),
        }
        final_score = 0.0
        for key, score in breakdown.items():
            w = float(self.weights.get(key, 0))
            adjust = self.feedback_adjustments.get(key, 0.0)
            final_score += max(w + adjust, 0.0) * score
        final_score = max(min(final_score, 1.0), 0.0)
        confidence = self.confidence_level(final_score, breakdown)
        risk_flags = self.risk_flags(paper, breakdown)
        why_selected = self.explain(paper, breakdown, confidence)
        return ScoredPaper(
            paper=paper,
            final_score=final_score,
            confidence=confidence,
            score_breakdown=breakdown,
            why_selected=why_selected,
            risk_flags=risk_flags,
        )

    def topic_fit(self, paper: Paper) -> float:
        if not paper.topics:
            return 0.1
        return min(1.0, 0.25 * len(paper.topics) + 0.25)

    def venue_signal(self, paper: Paper) -> float:
        venue = (paper.venue or "").lower()
        if not venue:
            return 0.3
        if any(v in venue for v in TOP_VENUE_HINTS):
            return 0.95
        if "workshop" in venue or "arxiv" in venue:
            return 0.45
        return 0.65

    def author_org_signal(self, paper: Paper) -> float:
        text = " ".join([*paper.authors, *paper.orgs]).lower()
        if not text:
            return 0.4
        hits = sum(1 for hint in STRONG_ORG_HINTS if hint in text)
        return min(1.0, 0.45 + 0.2 * hits)

    def impact_signal(self, paper: Paper) -> float:
        citation_score = 1 - math.exp(-(paper.citation_count or 0) / 20)
        social_score = max(min(paper.social_signal, 1.0), 0.0)
        return max(min(0.7 * citation_score + 0.3 * social_score, 1.0), 0.0)

    def method_novelty(self, paper: Paper) -> float:
        text = f"{paper.title}\n{paper.abstract}".lower()
        novelty_keywords = ["new", "novel", "first", "unified", "scaling", "inference-time"]
        hits = sum(1 for k in novelty_keywords if k in text)
        return min(0.4 + 0.1 * hits, 0.95)

    def evidence_strength(self, paper: Paper) -> float:
        text = paper.abstract.lower()
        pos = ["benchmark", "ablation", "state-of-the-art", "evaluation", "comparison"]
        neg = ["preliminary", "position paper", "opinion"]
        score = 0.35 + 0.1 * sum(1 for p in pos if p in text) - 0.15 * sum(1 for n in neg if n in text)
        return min(max(score, 0.05), 0.95)

    @staticmethod
    def confidence_level(final_score: float, breakdown: dict[str, float]) -> str:
        if final_score >= 0.78 and breakdown["evidence_strength"] >= 0.45:
            return "A"
        if final_score >= 0.58:
            return "B"
        return "C"

    @staticmethod
    def risk_flags(paper: Paper, breakdown: dict[str, float]) -> list[str]:
        flags: list[str] = []
        text = paper.abstract.lower()
        if breakdown["evidence_strength"] <= 0.3:
            flags.append("weak_evidence")
        if "we show" in text and "benchmark" not in text:
            flags.append("strong_claim_without_clear_eval")
        if breakdown["impact_signal"] > 0.65 and breakdown["venue_signal"] < 0.5:
            flags.append("hype_over_academic_signal")
        return flags

    @staticmethod
    def explain(paper: Paper, breakdown: dict[str, float], confidence: str) -> str:
        top_dims = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)[:3]
        reasons = ", ".join([f"{k}={v:.2f}" for k, v in top_dims])
        topic_str = "/".join(paper.topics) if paper.topics else "uncategorized"
        return f"Matched topics [{topic_str}], confidence {confidence}, strongest signals: {reasons}."
