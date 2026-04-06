"""Summary engine with pluggable providers."""

from __future__ import annotations

import os

import requests

from paper_bot.models.paper import ScoredPaper


class SummaryEngine:
    def __init__(self, cfg: dict) -> None:
        summary_cfg = cfg.get("summary", {})
        self.provider = summary_cfg.get("provider", "local_template")
        self.api_provider = summary_cfg.get("api_provider", "openai")
        self.model = summary_cfg.get("model", "gpt-4o-mini")

    def summarize_many(self, scored: list[ScoredPaper]) -> list[ScoredPaper]:
        for item in scored:
            item.summary = self.summarize_one(item)
        return scored

    def summarize_one(self, item: ScoredPaper) -> str:
        if self.provider == "api":
            try:
                return self._summarize_with_api(item)
            except Exception as exc:  # noqa: BLE001
                return self._template_summary(item, extra=f"API fallback due to error: {exc}")
        return self._template_summary(item)

    def _template_summary(self, item: ScoredPaper, extra: str = "") -> str:
        p = item.paper
        topics = ", ".join(p.topics) if p.topics else "unknown"
        risks = ", ".join(item.risk_flags) if item.risk_flags else "none"
        return (
            f"Problem: {p.title}\n"
            f"Core idea: {p.abstract[:320]}...\n"
            f"Key results: confidence={item.confidence}, score={item.final_score:.2f}\n"
            f"Relation to your track: topics={topics}\n"
            f"Reviewer view: risks={risks}; evidence={item.score_breakdown.get('evidence_strength', 0):.2f}\n"
            f"Repro suggestion: inspect code_url + rerun strongest benchmark settings first.\n"
            f"{extra}".strip()
        )

    def _summarize_with_api(self, item: ScoredPaper) -> str:
        if self.api_provider != "openai":
            raise ValueError(f"Unsupported API provider: {self.api_provider}")
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        p = item.paper
        prompt = (
            "You are summarizing a research paper for a graduate student working on LLM reasoning, agents, "
            "post-training and RL. Return concise sections: Problem, Method, Results, Risks, WhyItMatters."
            f"\nTitle: {p.title}\nAbstract: {p.abstract}\nVenue: {p.venue}\nAuthors: {', '.join(p.authors)}"
        )
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
            timeout=60,
        )
        resp.raise_for_status()
        payload = resp.json()
        return payload["choices"][0]["message"]["content"]
