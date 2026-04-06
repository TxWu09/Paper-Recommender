"""Domain keyword recommendation helpers."""

from __future__ import annotations


def suggest_keywords_for_domain(cfg: dict, domain: str, limit: int = 20) -> list[str]:
    catalogs = cfg.get("domain_keyword_catalog", {}) or {}
    if not isinstance(catalogs, dict):
        return []
    domain_key = (domain or "").strip().lower()
    exact = _as_keyword_list(catalogs.get(domain_key))
    if exact:
        return exact[:limit]

    # Fuzzy fallback: return merged keywords for partial matching domains.
    merged: list[str] = []
    for key, value in catalogs.items():
        if domain_key in str(key).lower() or str(key).lower() in domain_key:
            merged.extend(_as_keyword_list(value))
    return _dedup(merged)[:limit]


def topics_from_selected_keywords(cfg: dict, selected_keywords: list[str]) -> list[str]:
    selected = {x.strip().lower() for x in selected_keywords if x.strip()}
    topics_cfg = cfg.get("topics", {}) or {}
    matched_topics: list[str] = []
    for topic, payload in topics_cfg.items():
        aliases = []
        if isinstance(payload, dict):
            aliases = payload.get("aliases", [])
        elif isinstance(payload, list):
            aliases = payload
        alias_set = {str(a).strip().lower() for a in aliases}
        if selected.intersection(alias_set):
            matched_topics.append(str(topic))
    return _dedup(matched_topics)


def _as_keyword_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip().lower() for x in value if str(x).strip()]
    return []


def _dedup(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def domain_catalog_keys(cfg: dict) -> list[str]:
    catalogs = cfg.get("domain_keyword_catalog", {}) or {}
    if not isinstance(catalogs, dict):
        return []
    return list(catalogs.keys())


def keywords_for_catalog_key(cfg: dict, key: str) -> list[str]:
    catalogs = cfg.get("domain_keyword_catalog", {}) or {}
    if not isinstance(catalogs, dict):
        return []
    raw = catalogs.get(key)
    return _dedup(_as_keyword_list(raw))
