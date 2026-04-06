"""SQLite persistence for papers and feedback."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from paper_bot.models.paper import Paper, ScoredPaper


class SQLiteStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS papers (
              paper_id TEXT PRIMARY KEY,
              source TEXT,
              title TEXT,
              abstract TEXT,
              url TEXT,
              published_at TEXT,
              authors_json TEXT,
              orgs_json TEXT,
              venue TEXT,
              topics_json TEXT,
              code_url TEXT,
              citation_count INTEGER,
              social_signal REAL,
              metadata_json TEXT,
              final_score REAL,
              confidence TEXT,
              score_breakdown_json TEXT,
              why_selected TEXT,
              risk_flags_json TEXT,
              summary TEXT,
              pushed INTEGER DEFAULT 0
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              paper_id TEXT,
              signal TEXT,
              value INTEGER,
              created_at TEXT
            )
            """
        )
        self.conn.commit()
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        """Add columns if missing (older DB files)."""
        try:
            self.conn.execute("ALTER TABLE papers ADD COLUMN pushed_at TEXT")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass

    def upsert_scored_papers(self, papers: list[ScoredPaper]) -> None:
        for item in papers:
            p = item.paper
            self.conn.execute(
                """
                INSERT INTO papers (
                    paper_id, source, title, abstract, url, published_at, authors_json, orgs_json,
                    venue, topics_json, code_url, citation_count, social_signal, metadata_json,
                    final_score, confidence, score_breakdown_json, why_selected, risk_flags_json, summary, pushed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(paper_id) DO UPDATE SET
                    source=excluded.source,
                    title=excluded.title,
                    abstract=excluded.abstract,
                    url=excluded.url,
                    published_at=excluded.published_at,
                    authors_json=excluded.authors_json,
                    orgs_json=excluded.orgs_json,
                    venue=excluded.venue,
                    topics_json=excluded.topics_json,
                    code_url=excluded.code_url,
                    citation_count=excluded.citation_count,
                    social_signal=excluded.social_signal,
                    metadata_json=excluded.metadata_json,
                    final_score=excluded.final_score,
                    confidence=excluded.confidence,
                    score_breakdown_json=excluded.score_breakdown_json,
                    why_selected=excluded.why_selected,
                    risk_flags_json=excluded.risk_flags_json,
                    summary=excluded.summary
                """,
                (
                    p.paper_id,
                    p.source,
                    p.title,
                    p.abstract,
                    p.url,
                    p.published_at.isoformat() if p.published_at else "",
                    json.dumps(p.authors, ensure_ascii=False),
                    json.dumps(p.orgs, ensure_ascii=False),
                    p.venue,
                    json.dumps(p.topics, ensure_ascii=False),
                    p.code_url,
                    p.citation_count,
                    p.social_signal,
                    json.dumps(p.metadata, ensure_ascii=False),
                    item.final_score,
                    item.confidence,
                    json.dumps(item.score_breakdown, ensure_ascii=False),
                    item.why_selected,
                    json.dumps(item.risk_flags, ensure_ascii=False),
                    item.summary,
                ),
            )
        self.conn.commit()

    def top_unpushed(self, limit: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM papers WHERE pushed = 0 ORDER BY final_score DESC LIMIT ?", (limit,)
        ).fetchall()

    def get_pushed_flags(self, paper_ids: list[str]) -> dict[str, int]:
        """Return paper_id -> pushed (0 or 1). Omitted ids are treated as unpushed when absent."""
        if not paper_ids:
            return {}
        placeholders = ",".join("?" for _ in paper_ids)
        rows = self.conn.execute(
            f"SELECT paper_id, pushed FROM papers WHERE paper_id IN ({placeholders})",
            paper_ids,
        ).fetchall()
        return {str(r["paper_id"]): int(r["pushed"]) for r in rows}

    def mark_pushed(self, paper_ids: list[str]) -> None:
        if not paper_ids:
            return
        now = datetime.utcnow().isoformat()
        for pid in paper_ids:
            self.conn.execute(
                "UPDATE papers SET pushed = 1, pushed_at = ? WHERE paper_id = ?",
                (now, pid),
            )
        self.conn.commit()

    def add_feedback(self, paper_id: str, signal: str, value: int) -> None:
        self.conn.execute(
            "INSERT INTO feedback (paper_id, signal, value, created_at) VALUES (?, ?, ?, ?)",
            (paper_id, signal, value, datetime.utcnow().isoformat()),
        )
        self.conn.commit()

    def feedback_stats(self) -> dict[str, float]:
        rows = self.conn.execute(
            "SELECT signal, AVG(value) AS avg_value FROM feedback GROUP BY signal"
        ).fetchall()
        return {r["signal"]: float(r["avg_value"]) for r in rows}
