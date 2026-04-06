"""Optional Notion sync exporter."""

from __future__ import annotations

import os

import requests

from paper_bot.models.paper import ScoredPaper


class NotionExporter:
    def __init__(self, cfg: dict) -> None:
        notion_cfg = cfg.get("export", {}).get("notion", {})
        self.enabled = bool(notion_cfg.get("enabled", False))
        self.database_id = notion_cfg.get("database_id", "")
        token_env = notion_cfg.get("token_env", "NOTION_API_KEY")
        self.token = os.getenv(token_env, "")

    def export(self, scored: list[ScoredPaper]) -> None:
        if not self.enabled:
            return
        if not self.database_id or not self.token:
            print("[WARN] Notion enabled but database_id/token missing, skipping.")
            return
        for item in scored:
            self._create_page(item)

    def _create_page(self, item: ScoredPaper) -> None:
        p = item.paper
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        payload = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Name": {"title": [{"text": {"content": p.title[:2000]}}]},
                "URL": {"url": p.url or None},
                "Topics": {"multi_select": [{"name": t} for t in p.topics[:10]]},
                "Score": {"number": round(item.final_score, 3)},
                "Confidence": {"select": {"name": item.confidence}},
            },
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": item.summary[:2000]}}]},
                }
            ],
        }
        resp = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload, timeout=30)
        if resp.status_code >= 300:
            print(f"[WARN] Notion upsert failed for {p.paper_id}: {resp.text[:300]}")
