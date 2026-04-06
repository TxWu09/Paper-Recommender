"""Exports recommendations to an Obsidian vault as Markdown notes."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

from paper_bot.models.paper import ScoredPaper


class ObsidianExporter:
    def __init__(self, cfg: dict) -> None:
        obs_cfg = cfg.get("export", {}).get("obsidian", {})
        self.enabled = bool(obs_cfg.get("enabled", False))
        self.vault_path = obs_cfg.get("vault_path", "")
        self.folder = obs_cfg.get("folder", "Papers")
        self.one_note_per_paper = bool(obs_cfg.get("one_note_per_paper", True))
        self.index_file = obs_cfg.get("index_file", "paper_digest.md")

    def export(self, scored: list[ScoredPaper]) -> None:
        if not self.enabled:
            return
        if not self.vault_path:
            print("[WARN] Obsidian enabled but vault_path is empty, skipping.")
            return
        base_dir = Path(self.vault_path) / self.folder
        base_dir.mkdir(parents=True, exist_ok=True)
        if self.one_note_per_paper:
            self._export_per_paper(base_dir, scored)
        self._write_index(base_dir, scored)

    def _export_per_paper(self, base_dir: Path, scored: list[ScoredPaper]) -> None:
        day = datetime.now().strftime("%Y-%m-%d")
        day_dir = base_dir / day
        day_dir.mkdir(parents=True, exist_ok=True)
        for item in scored:
            p = item.paper
            safe_id = _slugify(p.paper_id or p.title)[:80]
            path = day_dir / f"{safe_id}.md"
            path.write_text(self._paper_note(item), encoding="utf-8")

    def _write_index(self, base_dir: Path, scored: list[ScoredPaper]) -> None:
        day = datetime.now().strftime("%Y-%m-%d")
        index_path = base_dir / self.index_file
        lines = [f"# Paper Digest - {day}", ""]
        for idx, item in enumerate(scored, start=1):
            p = item.paper
            tags = " ".join(_tagify_topics(p.topics))
            lines.append(f"## {idx}. {p.title}")
            lines.append(f"- URL: {p.url}")
            lines.append(f"- Score: {item.final_score:.3f} ({item.confidence})")
            lines.append(f"- Topics: {', '.join(p.topics) if p.topics else 'N/A'}")
            if tags:
                lines.append(f"- Tags: {tags}")
            lines.append(f"- Why selected: {item.why_selected}")
            if item.risk_flags:
                lines.append(f"- Risks: {', '.join(item.risk_flags)}")
            lines.append("")
        index_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    def _paper_note(self, item: ScoredPaper) -> str:
        p = item.paper
        tags = _tagify_topics(p.topics)
        frontmatter = [
            "---",
            f'title: "{_escape_yaml(p.title)}"',
            f'url: "{_escape_yaml(p.url)}"',
            f'paper_id: "{_escape_yaml(p.paper_id)}"',
            f'date: "{p.published_at.isoformat() if p.published_at else ""}"',
            f'venue: "{_escape_yaml(p.venue)}"',
            f"score: {item.final_score:.3f}",
            f'confidence: "{item.confidence}"',
            f"topics: [{', '.join([f'\"{_escape_yaml(t)}\"' for t in p.topics])}]",
            f"authors: [{', '.join([f'\"{_escape_yaml(a)}\"' for a in p.authors])}]",
            f"tags: [{', '.join([f'\"{_escape_yaml(t)}\"' for t in tags])}]",
            "---",
            "",
        ]
        body = [
            f"# {p.title}",
            "",
            f"- URL: {p.url}",
            f"- Venue: {p.venue or 'N/A'}",
            f"- Score: {item.final_score:.3f} ({item.confidence})",
            f"- Why selected: {item.why_selected}",
            "",
            "## Summary",
            "",
            item.summary or "N/A",
            "",
            "## Risk Flags",
            "",
            ", ".join(item.risk_flags) if item.risk_flags else "none",
            "",
            "## Code URL",
            "",
            p.code_url or "N/A",
            "",
            "## Topic Tags",
            "",
            " ".join(tags) if tags else "N/A",
            "",
        ]
        return "\n".join(frontmatter + body)


def _slugify(text: str) -> str:
    value = (text or "paper").strip().lower()
    value = re.sub(r"[^a-z0-9\-_]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-") or "paper"


def _tagify_topics(topics: list[str]) -> list[str]:
    tags: list[str] = ["#paper/recommendation"]
    for topic in topics or []:
        clean = re.sub(r"[^a-z0-9\-_]+", "-", topic.lower()).strip("-")
        if clean:
            tags.append(f"#topic/{clean}")
    return tags


def _escape_yaml(text: str) -> str:
    return (text or "").replace('"', '\\"')
