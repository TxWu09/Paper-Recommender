"""Topic taxonomy and matching helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TopicTaxonomy:
    topic_aliases: dict[str, list[str]]

    @classmethod
    def default(cls) -> "TopicTaxonomy":
        return cls(
            topic_aliases={
                "reasoning": [
                    "reasoning",
                    "chain-of-thought",
                    "inference-time compute",
                    "tree search",
                    "self-consistency",
                ],
                "agent": [
                    "agent",
                    "tool use",
                    "function calling",
                    "multi-agent",
                    "planning and acting",
                ],
                "post_training": [
                    "post-training",
                    "alignment",
                    "instruction tuning",
                    "preference optimization",
                    "dpo",
                    "ppo",
                    "rlhf",
                ],
                "rl": [
                    "reinforcement learning",
                    "policy optimization",
                    "reward model",
                    "actor critic",
                    "offline rl",
                ],
            }
        )

    @classmethod
    def from_config(cls, topics_cfg: dict) -> "TopicTaxonomy":
        alias_map: dict[str, list[str]] = {}
        for topic, payload in (topics_cfg or {}).items():
            if isinstance(payload, dict):
                aliases = payload.get("aliases", [])
                if isinstance(aliases, list):
                    alias_map[topic] = [str(a).lower() for a in aliases]
            elif isinstance(payload, list):
                alias_map[topic] = [str(a).lower() for a in payload]
        if not alias_map:
            return cls.default()
        return cls(topic_aliases=alias_map)

    def match_topics(self, text: str) -> list[str]:
        text_l = (text or "").lower()
        matched: list[str] = []
        for topic, aliases in self.topic_aliases.items():
            if any(alias in text_l for alias in aliases):
                matched.append(topic)
        return matched
