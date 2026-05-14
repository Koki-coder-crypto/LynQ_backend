"""
Prompt caching helpers — reduces input token cost by up to 90% for cached prefixes.

Cache writes cost 1.25x base price (5-min TTL) or 2x (1-hour TTL).
Cache reads cost 0.1x base price.
Break-even: 2 requests for 5-min TTL, 3 requests for 1-hour TTL.

The fundamental rule: caching is a PREFIX MATCH.
Any change before the cache_control marker invalidates the cache.
Render order: tools → system → messages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CacheTTL = Literal["5m", "1h"]


@dataclass
class CacheStats:
    requests: int = 0
    cache_writes: int = 0  # tokens written to cache
    cache_reads: int = 0  # tokens read from cache
    uncached_tokens: int = 0  # full-price input tokens

    @property
    def hit_rate(self) -> float:
        total = self.cache_reads + self.cache_writes + self.uncached_tokens
        return self.cache_reads / total if total > 0 else 0.0

    @property
    def savings_summary(self) -> str:
        # Uncached cost: 1.0x per token
        # Cache write:   1.25x per token
        # Cache read:    0.1x per token
        baseline = self.cache_writes + self.cache_reads + self.uncached_tokens
        actual = self.cache_writes * 1.25 + self.cache_reads * 0.1 + self.uncached_tokens * 1.0
        if baseline == 0:
            return "No data yet"
        saved_pct = max(0, (1 - actual / baseline) * 100)
        return (
            f"Hit rate: {self.hit_rate:.1%} | "
            f"Tokens saved ≈ {saved_pct:.1f}% "
            f"({self.cache_reads:,} read from cache, {self.cache_writes:,} written)"
        )


class CacheManager:
    """
    Builds cache-annotated system prompts and messages, and tracks statistics.

    Stable content (never changes) → place BEFORE the cache marker.
    Volatile content (changes per request) → place AFTER the cache marker.

    Example:
        cm = CacheManager()
        system_blocks = cm.cached_system(stable_prompt, ttl="1h")
        messages = cm.cached_conversation(history, new_user_message)
    """

    def __init__(self) -> None:
        self.stats = CacheStats()

    # ------------------------------------------------------------------ #
    # System prompt helpers                                                #
    # ------------------------------------------------------------------ #

    def cached_system(
        self,
        stable_text: str,
        volatile_text: str = "",
        ttl: CacheTTL = "5m",
    ) -> list[dict]:
        """
        Returns a system list with cache_control on the stable block.
        Volatile text (dynamic user context, timestamps) goes in a second block
        WITHOUT a cache marker so it doesn't break the cache.
        """
        blocks: list[dict] = [
            {
                "type": "text",
                "text": stable_text,
                "cache_control": self._cache_control(ttl),
            }
        ]
        if volatile_text:
            blocks.append({"type": "text", "text": volatile_text})
        return blocks

    # ------------------------------------------------------------------ #
    # Message history helpers                                              #
    # ------------------------------------------------------------------ #

    def cached_conversation(
        self,
        history: list[dict],
        new_user_message: str,
        ttl: CacheTTL = "5m",
    ) -> list[dict]:
        """
        Marks the last block of the most-recently-appended turn with cache_control.
        This lets each subsequent request reuse the entire prior conversation prefix.
        """
        messages = list(history)  # shallow copy

        # Cache the last block of the last existing turn (the accumulated history)
        if messages:
            last = messages[-1]
            content = last.get("content")
            if isinstance(content, str):
                messages[-1] = dict(
                    last,
                    content=[
                        {"type": "text", "text": content, "cache_control": self._cache_control(ttl)}
                    ],
                )
            elif isinstance(content, list) and content:
                new_content = list(content)
                new_content[-1] = dict(content[-1], cache_control=self._cache_control(ttl))
                messages[-1] = dict(last, content=new_content)

        # Append the new user turn WITHOUT a cache marker (it changes next turn)
        messages.append({"role": "user", "content": new_user_message})
        return messages

    # ------------------------------------------------------------------ #
    # Document / large-context caching                                    #
    # ------------------------------------------------------------------ #

    def cached_document_message(
        self,
        document_text: str,
        question: str,
        ttl: CacheTTL = "1h",
    ) -> list[dict]:
        """
        Single user message with a large shared document cached separately
        from the varying question. Use 1h TTL when re-querying the same doc
        across many requests.
        """
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": document_text,
                        "cache_control": self._cache_control(ttl),
                    },
                    {
                        "type": "text",
                        "text": question,
                        # No cache_control — this varies per request
                    },
                ],
            }
        ]

    # ------------------------------------------------------------------ #
    # Stats tracking                                                       #
    # ------------------------------------------------------------------ #

    def record_usage(self, usage: object) -> None:
        """Pass the response.usage object to track cache efficiency."""
        self.stats.requests += 1
        self.stats.cache_writes += getattr(usage, "cache_creation_input_tokens", 0) or 0
        self.stats.cache_reads += getattr(usage, "cache_read_input_tokens", 0) or 0
        self.stats.uncached_tokens += getattr(usage, "input_tokens", 0) or 0

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _cache_control(ttl: CacheTTL) -> dict:
        ctrl: dict = {"type": "ephemeral"}
        if ttl == "1h":
            ctrl["ttl"] = "1h"
        return ctrl
