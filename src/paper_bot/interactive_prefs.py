"""Interactive prompt for domain + keyword preferences (domain_keyword_catalog)."""

from __future__ import annotations

from paper_bot.domain_keywords import (
    domain_catalog_keys,
    keywords_for_catalog_key,
    topics_from_selected_keywords,
)


def prompt_preferences(cfg: dict) -> tuple[list[str], list[str]]:
    """
    Ask user to pick a broad domain and multi-select keywords from config.

    Returns:
        (selected_topics, keyword_fallback)
        - If topic aliases match, use selected_topics for filtering.
        - If selected_topics is empty but keyword_fallback is non-empty, the pipeline
          filters by title/abstract substring (see filter_by_keyword_substrings).
    """
    keys = domain_catalog_keys(cfg)
    if not keys:
        print(
            "[INFO] No domain_keyword_catalog in config. "
            "Add domains under domain_keyword_catalog in bot_config.yaml, or use --selected-keywords."
        )
        return [], []

    print("\n--- Your preferences (from bot_config.yaml) ---\n")
    print("Broad domains:")
    for i, k in enumerate(keys, start=1):
        print(f"  {i}. {k}")

    raw = input("\nPick domain: number or name (Enter = 1, 0 = skip / no keyword filter): ").strip()
    if raw == "0":
        print("No keyword filter — will use all matched topics.\n")
        return [], []

    domain_key = _resolve_domain_key(keys, raw)

    keywords = keywords_for_catalog_key(cfg, domain_key)
    if not keywords:
        print(f"No keywords for domain '{domain_key}'.")
        return [], []

    print(f"\nKeywords for [{domain_key}] (multi-select):")
    for i, kw in enumerate(keywords, start=1):
        print(f"  {i:02d}. {kw}")

    sel = input(
        "\nEnter numbers separated by comma/space (e.g. 1,3,5), "
        "'all' for all, or Enter = all: "
    ).strip().lower()

    if not sel or sel == "all":
        chosen = list(keywords)
    else:
        chosen = []
        for part in sel.replace(",", " ").split():
            part = part.strip()
            if not part:
                continue
            if part.isdigit():
                idx = int(part)
                if 1 <= idx <= len(keywords):
                    kw = keywords[idx - 1]
                    if kw not in chosen:
                        chosen.append(kw)
            else:
                for kw in keywords:
                    if part in kw or kw.startswith(part):
                        if kw not in chosen:
                            chosen.append(kw)
        if not chosen:
            print("No valid selection; using all keywords in this domain.")
            chosen = list(keywords)

    topics = topics_from_selected_keywords(cfg, chosen)
    print(f"\nSelected keywords: {', '.join(chosen)}")
    if topics:
        print(f"Mapped to topic filters: {', '.join(topics)}")
    else:
        print(
            "[INFO] No topic alias overlap — will filter papers by keyword text in title/abstract."
        )
    print()
    return topics, chosen


def _resolve_domain_key(keys: list[str], raw: str) -> str:
    if not raw:
        return keys[0]
    if raw.isdigit():
        idx = int(raw)
        if 1 <= idx <= len(keys):
            return keys[idx - 1]
        print("Invalid number; using first domain.")
        return keys[0]
    lowered = raw.lower().strip()
    for k in keys:
        if k.lower() == lowered:
            return k
    for k in keys:
        if lowered in k.lower() or k.lower() in lowered:
            return k
    print(f"Unknown domain '{raw}'. Using first: {keys[0]}")
    return keys[0]
