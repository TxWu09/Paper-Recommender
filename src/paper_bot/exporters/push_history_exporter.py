"""Append pushed papers to a CSV (optional Excel-friendly backup)."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from paper_bot.models.paper import ScoredPaper


class PushHistoryExporter:
    """One row per push event; safe to open in Excel."""

    COLUMNS = [
        "pushed_at",
        "paper_id",
        "title",
        "url",
        "final_score",
        "confidence",
        "topics",
    ]

    def __init__(self, cfg: dict) -> None:
        path = (cfg.get("export", {}) or {}).get("push_history_csv", "")
        self.path = (path or "").strip()

    def append(self, scored: list[ScoredPaper]) -> None:
        if not self.path or not scored:
            return
        p = Path(self.path)
        p.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.utcnow().isoformat()
        write_header = not p.exists()
        with p.open("a", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self.COLUMNS)
            if write_header:
                w.writeheader()
            for item in scored:
                pobj = item.paper
                w.writerow(
                    {
                        "pushed_at": now,
                        "paper_id": pobj.paper_id,
                        "title": pobj.title,
                        "url": pobj.url,
                        "final_score": f"{item.final_score:.4f}",
                        "confidence": item.confidence,
                        "topics": ",".join(pobj.topics),
                    }
                )
