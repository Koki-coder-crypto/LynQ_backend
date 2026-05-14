"""
OptimizedClient — a drop-in wrapper around the Anthropic SDK that
applies all token-reduction techniques automatically.

Techniques applied per request:
  1. Smart model routing     (cheapest adequate model)
  2. Prompt caching          (stable system/context cached)
  3. Effort control          (low/medium/high thinking depth)
  4. Token counting guard    (abort if over budget)
  5. Cost tracking           (per-request and cumulative)
"""

from __future__ import annotations

from typing import Any

import anthropic

from .caching import CacheManager, CacheTTL
from .routing import ModelRouter, TaskComplexity
from .utils import CostEstimator, TokenCounter


class OptimizedClient:
    """
    Wraps the Anthropic SDK with automatic token-reduction.

    Example:
        client = OptimizedClient(api_key="sk-ant-...")
        reply = client.chat(
            "Summarize this article in one paragraph.",
            system="You are a concise summarizer.",
        )
    """

    def __init__(
        self,
        api_key: str | None = None,
        stable_system: str = "",
        cache_ttl: CacheTTL = "5m",
        max_input_tokens: int | None = None,   # abort if over this limit
        default_max_tokens: int = 4096,
        auto_route: bool = True,               # enable smart model routing
        default_model: str = "claude-sonnet-4-6",
    ) -> None:
        self._sdk = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self._stable_system = stable_system
        self._cache_ttl = cache_ttl
        self._max_input_tokens = max_input_tokens
        self._default_max_tokens = default_max_tokens
        self._auto_route = auto_route
        self._default_model = default_model

        self._cache = CacheManager()
        self._router = ModelRouter()
        self._cost = CostEstimator(default_model)
        self._counter = TokenCounter(self._sdk, default_model)

    # ------------------------------------------------------------------ #
    # Simple single-turn call                                              #
    # ------------------------------------------------------------------ #

    def chat(
        self,
        user_message: str,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        effort: str = "medium",              # low | medium | high | max
        force_complexity: TaskComplexity | None = None,
        extra_params: dict[str, Any] | None = None,
    ) -> str:
        """
        Send a single-turn message with automatic optimizations.
        Returns the assistant's text reply.
        """
        stable = system or self._stable_system
        messages = [{"role": "user", "content": user_message}]

        # 1. Build cached system blocks
        system_blocks = self._cache.cached_system(stable, ttl=self._cache_ttl) if stable else None

        # 2. Smart model routing
        chosen_model = model or self._route_model(messages, stable, force_complexity)

        # 3. Token guard
        if self._max_input_tokens:
            over, count = self._counter.should_abort(messages, self._max_input_tokens, system_blocks)
            if over:
                raise ValueError(
                    f"Request aborted: {count:,} input tokens exceeds limit of "
                    f"{self._max_input_tokens:,}"
                )

        # 4. Build request kwargs
        kwargs: dict[str, Any] = {
            "model": chosen_model,
            "max_tokens": max_tokens or self._default_max_tokens,
            "messages": messages,
        }
        if system_blocks:
            kwargs["system"] = system_blocks
        if chosen_model in ("claude-opus-4-7", "claude-opus-4-6", "claude-sonnet-4-6"):
            kwargs["output_config"] = {"effort": effort}
        if extra_params:
            kwargs.update(extra_params)

        # 5. Call the API
        response = self._sdk.messages.create(**kwargs)

        # 6. Track usage
        self._cache.record_usage(response.usage)
        cost = self._cost.record(response.usage)
        self._cost._model = chosen_model  # update for accurate pricing

        text = next((b.text for b in response.content if b.type == "text"), "")
        return text

    # ------------------------------------------------------------------ #
    # Multi-message call (pass full message array)                        #
    # ------------------------------------------------------------------ #

    def complete(
        self,
        messages: list[dict],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        cache_last_turn: bool = True,
        effort: str = "medium",
        force_complexity: TaskComplexity | None = None,
    ) -> anthropic.types.Message:
        """
        Full messages array call with caching on the last assistant turn.
        Returns the raw Message object.
        """
        stable = system or self._stable_system
        system_blocks = self._cache.cached_system(stable, ttl=self._cache_ttl) if stable else None

        # Cache the last turn of the conversation history if requested
        if cache_last_turn and len(messages) >= 2:
            messages = self._mark_last_turn(messages)

        chosen_model = model or self._route_model(messages, stable, force_complexity)

        kwargs: dict[str, Any] = {
            "model": chosen_model,
            "max_tokens": max_tokens or self._default_max_tokens,
            "messages": messages,
        }
        if system_blocks:
            kwargs["system"] = system_blocks
        if chosen_model in ("claude-opus-4-7", "claude-opus-4-6", "claude-sonnet-4-6"):
            kwargs["output_config"] = {"effort": effort}

        response = self._sdk.messages.create(**kwargs)
        self._cache.record_usage(response.usage)
        self._cost.record(response.usage)
        return response

    # ------------------------------------------------------------------ #
    # Accessors                                                            #
    # ------------------------------------------------------------------ #

    @property
    def sdk(self) -> anthropic.Anthropic:
        """Access the underlying SDK for advanced usage."""
        return self._sdk

    @property
    def cache_stats(self) -> str:
        return self._cache.stats.savings_summary

    @property
    def cost_summary(self) -> str:
        return self._cost.summary

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    def _route_model(
        self,
        messages: list[dict],
        system: str,
        force: TaskComplexity | None,
    ) -> str:
        if not self._auto_route:
            return self._default_model
        decision = self._router.route(messages, system=system, force=force)
        return decision.model

    @staticmethod
    def _mark_last_turn(messages: list[dict]) -> list[dict]:
        """Add cache_control to the last block of the second-to-last turn."""
        msgs = list(messages)
        if len(msgs) < 2:
            return msgs
        last_full = msgs[-2]
        content = last_full.get("content")
        if isinstance(content, str) and content:
            msgs[-2] = dict(last_full, content=[
                {"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}
            ])
        elif isinstance(content, list) and content:
            new_content = list(content)
            new_content[-1] = dict(content[-1], cache_control={"type": "ephemeral"})
            msgs[-2] = dict(last_full, content=new_content)
        return msgs
