"""End-to-end pipeline orchestrator."""

from __future__ import annotations

from dataclasses import dataclass

from paper_bot.connectors.registry import fetch_all_sources
from paper_bot.exporters.notion_exporter import NotionExporter
from paper_bot.exporters.sheet_exporter import SheetExporter
from paper_bot.pipeline.feedback import derive_weight_adjustments
from paper_bot.pipeline.ingest import deduplicate_papers, filter_by_selected_topics, tag_topics
from paper_bot.pipeline.push import PushDispatcher
from paper_bot.pipeline.quality import QualityEngine
from paper_bot.pipeline.summary import SummaryEngine
from paper_bot.storage.sqlite_store import SQLiteStore
from paper_bot.topic_taxonomy import TopicTaxonomy


@dataclass
class RunResult:
    total_fetched: int
    total_unique: int
    total_recommended: int


class PaperBot:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        db_path = cfg.get("storage", {}).get("sqlite_path", "data/papers.db")
        self.store = SQLiteStore(db_path)
        self.taxonomy = TopicTaxonomy.from_config(cfg.get("topics", {}))
        self.summary_engine = SummaryEngine(cfg)
        self.sheet_exporter = SheetExporter(cfg)
        self.notion_exporter = NotionExporter(cfg)
        self.push_dispatcher = PushDispatcher(cfg)

    def run_once(self, selected_topics: list[str] | None = None) -> RunResult:
        fetched = fetch_all_sources(self.cfg)
        unique = deduplicate_papers(fetched)
        tagged = tag_topics(unique, self.taxonomy)
        if selected_topics is None:
            selected_topics = self.cfg.get("app", {}).get("selected_topics", [])
        tagged = filter_by_selected_topics(tagged, selected_topics)

        feedback_stats = self.store.feedback_stats()
        adjustments = derive_weight_adjustments(feedback_stats)
        quality_engine = QualityEngine(self.cfg, feedback_adjustments=adjustments)
        scored = quality_engine.score_many(tagged)
        scored = self.summary_engine.summarize_many(scored)

        self.store.upsert_scored_papers(scored)
        top_n = int(self.cfg.get("app", {}).get("daily_top_n", 5))
        top_rows = self.store.top_unpushed(limit=top_n)
        id_to_scored = {x.paper.paper_id: x for x in scored}
        selected = [id_to_scored[r["paper_id"]] for r in top_rows if r["paper_id"] in id_to_scored]
        self.sheet_exporter.export(selected)
        self.notion_exporter.export(selected)
        self.push_dispatcher.write_markdown_digest(selected)
        self.store.mark_pushed([x.paper.paper_id for x in selected])
        return RunResult(
            total_fetched=len(fetched),
            total_unique=len(unique),
            total_recommended=len(selected),
        )
