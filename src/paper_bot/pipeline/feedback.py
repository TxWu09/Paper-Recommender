"""Feedback loop that adjusts scoring weights."""

from __future__ import annotations


def derive_weight_adjustments(feedback_stats: dict[str, float]) -> dict[str, float]:
    """
    Convert average feedback into tiny weight deltas.
    Positive feedback nudges score dimensions up; negative feedback nudges down.
    """
    adjustments: dict[str, float] = {}
    mapping = {
        "topic_like": "topic_fit",
        "venue_like": "venue_signal",
        "author_org_like": "author_org_signal",
        "impact_like": "impact_signal",
        "novelty_like": "method_novelty",
        "evidence_like": "evidence_strength",
    }
    for signal, dim in mapping.items():
        avg = feedback_stats.get(signal)
        if avg is None:
            continue
        # Expect values around {-1, 0, 1}; keep adjustment small and stable.
        adjustments[dim] = 0.02 * max(min(avg, 1.0), -1.0)
    return adjustments
