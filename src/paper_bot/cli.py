"""CLI entrypoint."""

from __future__ import annotations

import argparse

from paper_bot.pipeline.bot import PaperBot
from paper_bot.storage.sqlite_store import SQLiteStore
from paper_bot.utils.config import load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Paper Reading Assistant bot")
    parser.add_argument("--config", default="config/bot_config.yaml", help="Path to YAML config")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("run", help="Run one ingest-score-export cycle")

    fb = sub.add_parser("feedback", help="Submit feedback signal for a paper")
    fb.add_argument("--paper-id", required=True)
    fb.add_argument("--signal", required=True, help="e.g., topic_like, venue_like")
    fb.add_argument("--value", type=int, choices=[-1, 0, 1], required=True)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    cfg = load_config(args.config)
    if args.command in (None, "run"):
        bot = PaperBot(cfg)
        result = bot.run_once()
        print(
            f"Run complete: fetched={result.total_fetched}, "
            f"unique={result.total_unique}, recommended={result.total_recommended}"
        )
        return
    if args.command == "feedback":
        db_path = cfg.get("storage", {}).get("sqlite_path", "data/papers.db")
        store = SQLiteStore(db_path)
        store.add_feedback(args.paper_id, args.signal, args.value)
        print("Feedback stored.")
        return
    parser.print_help()


if __name__ == "__main__":
    main()
