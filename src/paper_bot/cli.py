"""CLI entrypoint."""

from __future__ import annotations

import argparse

from paper_bot.domain_keywords import topics_from_selected_keywords
from paper_bot.interactive_prefs import prompt_preferences
from paper_bot.pipeline.bot import PaperBot
from paper_bot.storage.sqlite_store import SQLiteStore
from paper_bot.utils.config import load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Paper Reading Assistant bot")
    parser.add_argument("--config", default="config/bot_config.yaml", help="Path to YAML config")
    sub = parser.add_subparsers(dest="command")

    run = sub.add_parser("run", help="Run one ingest-score-export cycle")
    run.add_argument(
        "--selected-topics",
        default="",
        help="Comma-separated topics to keep (e.g., reasoning,post_training).",
    )
    run.add_argument(
        "--selected-keywords",
        default="",
        help="Comma-separated keywords; will be mapped to topics via topic aliases.",
    )
    run.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Prompt for domain + keywords from domain_keyword_catalog in config.",
    )

    fb = sub.add_parser("feedback", help="Submit feedback signal for a paper")
    fb.add_argument("--paper-id", required=True)
    fb.add_argument("--signal", required=True, help="e.g., topic_like, venue_like")
    fb.add_argument("--value", type=int, choices=[-1, 0, 1], required=True)

    suggest = sub.add_parser("suggest-keywords", help="Suggest selectable keywords from a broad domain")
    suggest.add_argument("--domain", required=True, help="Broad domain, e.g. LLM, CV, Robotics")
    suggest.add_argument("--limit", type=int, default=20, help="Max number of suggested keywords")
    return parser


def _parse_csv(value: str) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def _dedupe_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    cfg = load_config(args.config)
    if args.command in (None, "run"):
        bot = PaperBot(cfg)

        cli_topics = _parse_csv(getattr(args, "selected_topics", ""))
        cli_keywords = _parse_csv(getattr(args, "selected_keywords", ""))
        interactive = bool(getattr(args, "interactive", False)) or bool(
            cfg.get("app", {}).get("interactive_on_run", False)
        )

        # Non-interactive: if user passed CLI flags, do not open prompt
        if cli_topics or cli_keywords:
            interactive = False

        selected_topics: list[str] | None = None
        keyword_substrings: list[str] | None = None

        if interactive:
            topics, kw = prompt_preferences(cfg)
            if topics:
                selected_topics = topics
            elif kw:
                selected_topics = []
                keyword_substrings = kw
            else:
                # Skip (0) or empty catalog: no extra filter
                selected_topics = []
        else:
            selected_topics = list(cli_topics)
            keyword_substrings = None
            if cli_keywords:
                mapped = topics_from_selected_keywords(cfg, cli_keywords)
                if mapped:
                    selected_topics = _dedupe_preserve(selected_topics + mapped)
                else:
                    keyword_substrings = cli_keywords
            if selected_topics is not None and not selected_topics and not keyword_substrings:
                # No CLI filter: use yaml app.selected_topics
                selected_topics = None

        result = bot.run_once(
            selected_topics=selected_topics,
            keyword_substrings=keyword_substrings,
        )
        st = selected_topics if selected_topics is not None else cfg.get("app", {}).get("selected_topics", [])
        print(
            f"Run complete: fetched={result.total_fetched}, "
            f"unique={result.total_unique}, recommended={result.total_recommended}, "
            f"selected_topics={st or 'ALL'}, keyword_substrings={keyword_substrings or 'NONE'}"
        )
        return
    if args.command == "suggest-keywords":
        from paper_bot.domain_keywords import suggest_keywords_for_domain

        suggestions = suggest_keywords_for_domain(cfg, args.domain, limit=args.limit)
        if not suggestions:
            print(
                "No keyword suggestions found for this domain. "
                "Please add entries under domain_keyword_catalog in config."
            )
            return
        print(f"Domain: {args.domain}")
        print("Suggested keywords (multi-select):")
        for idx, keyword in enumerate(suggestions, start=1):
            print(f"{idx:02d}. {keyword}")
        mapped_topics = topics_from_selected_keywords(cfg, suggestions)
        if mapped_topics:
            print(f"\nMapped topics from these keywords: {', '.join(mapped_topics)}")
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
