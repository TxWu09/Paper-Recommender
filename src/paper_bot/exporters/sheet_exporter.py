"""Exports recommendations to CSV and XLSX."""

from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook

from paper_bot.models.paper import ScoredPaper


class SheetExporter:
    COLUMNS = [
        "title",
        "url",
        "date",
        "topics",
        "venue",
        "authors",
        "org",
        "score",
        "confidence",
        "summary",
        "risks",
        "code_url",
        "read_status",
        "why_selected",
    ]

    def __init__(self, cfg: dict) -> None:
        export_cfg = cfg.get("export", {})
        self.csv_path = export_cfg.get("csv_path", "data/recommendations.csv")
        self.xlsx_path = export_cfg.get("excel_path", "data/recommendations.xlsx")

    def export(self, scored_papers: list[ScoredPaper]) -> None:
        rows = [self._row(x) for x in scored_papers]
        self._write_csv(rows)
        self._write_xlsx(rows)

    def _row(self, item: ScoredPaper) -> dict[str, str]:
        p = item.paper
        return {
            "title": p.title,
            "url": p.url,
            "date": p.published_at.isoformat() if p.published_at else "",
            "topics": ",".join(p.topics),
            "venue": p.venue,
            "authors": ",".join(p.authors),
            "org": ",".join(p.orgs),
            "score": f"{item.final_score:.3f}",
            "confidence": item.confidence,
            "summary": item.summary,
            "risks": ",".join(item.risk_flags),
            "code_url": p.code_url,
            "read_status": "new",
            "why_selected": item.why_selected,
        }

    def _write_csv(self, rows: list[dict[str, str]]) -> None:
        path = Path(self.csv_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

    def _write_xlsx(self, rows: list[dict[str, str]]) -> None:
        path = Path(self.xlsx_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        wb = Workbook()
        ws = wb.active
        ws.title = "papers"
        ws.append(self.COLUMNS)
        for row in rows:
            ws.append([row[c] for c in self.COLUMNS])
        wb.save(path)
