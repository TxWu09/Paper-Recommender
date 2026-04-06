"""Push digest generation."""

from __future__ import annotations

from pathlib import Path

from paper_bot.models.paper import ScoredPaper


class PushDispatcher:
    def __init__(self, cfg: dict) -> None:
        push_cfg = cfg.get("push", {})
        self.report_path = push_cfg.get("markdown_report_path", "data/daily_digest.md")

    def write_markdown_digest(self, scored: list[ScoredPaper], title: str = "Daily Paper Digest") -> str:
        lines = [f"# {title}", ""]
        for i, item in enumerate(scored, start=1):
            p = item.paper
            lines.append(f"## {i}. {p.title}")
            lines.append(f"- URL: {p.url}")
            lines.append(f"- Score: {item.final_score:.3f} ({item.confidence})")
            lines.append(f"- Topics: {', '.join(p.topics) if p.topics else 'N/A'}")
            lines.append(f"- Why selected: {item.why_selected}")
            if item.risk_flags:
                lines.append(f"- Risks: {', '.join(item.risk_flags)}")
            lines.append("")
            lines.append("Summary:")
            lines.append("")
            lines.append(item.summary)
            lines.append("")
        report = "\n".join(lines).strip() + "\n"
        path = Path(self.report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report, encoding="utf-8")
        return report
