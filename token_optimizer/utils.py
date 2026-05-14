"""
Token counting and cost estimation utilities.
"""

from __future__ import annotations

import anthropic

PRICING = {
    "claude-haiku-4-5":   {"input": 1.00,  "output": 5.00,  "cache_write": 1.25,  "cache_read": 0.10},
    "claude-sonnet-4-6":  {"input": 3.00,  "output": 15.00, "cache_write": 3.75,  "cache_read": 0.30},
    "claude-opus-4-7":    {"input": 5.00,  "output": 25.00, "cache_write": 6.25,  "cache_read": 0.50},
}


class TokenCounter:
    """Pre-request token counting to estimate cost before committing to a call."""

    def __init__(self, client: anthropic.Anthropic, model: str = "claude-sonnet-4-6") -> None:
        self._client = client
        self._model = model

    def count(
        self,
        messages: list[dict],
        system: str | list[dict] | None = None,
        tools: list | None = None,
    ) -> int:
        """Returns the exact input token count for the given request."""
        params: dict = {"model": self._model, "messages": messages}
        if system is not None:
            params["system"] = system
        if tools:
            params["tools"] = tools
        result = self._client.messages.count_tokens(**params)
        return result.input_tokens

    def should_abort(
        self,
        messages: list[dict],
        max_input_tokens: int,
        system: str | list[dict] | None = None,
    ) -> tuple[bool, int]:
        """
        Returns (should_abort, token_count).
        Use to gate expensive requests before sending.
        """
        count = self.count(messages, system)
        return count > max_input_tokens, count


class CostEstimator:
    """Estimate and track API spend."""

    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        self._model = model
        self._total_usd = 0.0
        self._total_input = 0
        self._total_output = 0

    def estimate(
        self,
        input_tokens: int,
        output_tokens: int,
        cache_write_tokens: int = 0,
        cache_read_tokens: int = 0,
    ) -> float:
        """Returns estimated cost in USD."""
        p = PRICING.get(self._model, PRICING["claude-sonnet-4-6"])
        cost = (
            input_tokens * p["input"]
            + output_tokens * p["output"]
            + cache_write_tokens * p["cache_write"]
            + cache_read_tokens * p["cache_read"]
        ) / 1_000_000
        return cost

    def record(self, usage: object) -> float:
        """Record usage from a response and return this request's cost."""
        inp = getattr(usage, "input_tokens", 0) or 0
        out = getattr(usage, "output_tokens", 0) or 0
        cw  = getattr(usage, "cache_creation_input_tokens", 0) or 0
        cr  = getattr(usage, "cache_read_input_tokens", 0) or 0
        cost = self.estimate(inp, out, cw, cr)
        self._total_usd += cost
        self._total_input += inp
        self._total_output += out
        return cost

    @property
    def total_usd(self) -> float:
        return self._total_usd

    @property
    def summary(self) -> str:
        return (
            f"Total: ${self._total_usd:.6f} USD | "
            f"Input: {self._total_input:,} tokens | "
            f"Output: {self._total_output:,} tokens"
        )
