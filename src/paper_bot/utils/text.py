"""Text and similarity helpers."""

from __future__ import annotations

import re
from difflib import SequenceMatcher


def normalize_title(title: str) -> str:
    text = (title or "").strip().lower()
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()
