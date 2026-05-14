"""
Smart model routing — directs requests to the cheapest model that can handle the task.

Pricing per 1M tokens (input / output):
  haiku-4-5:   $1.00 / $5.00   ← simple classification, short Q&A
  sonnet-4-6:  $3.00 / $15.00  ← standard generation, summarization
  opus-4-7:    $5.00 / $25.00  ← complex reasoning, long-horizon agentic
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class TaskComplexity(Enum):
    SIMPLE = "simple"  # → haiku-4-5
    STANDARD = "standard"  # → sonnet-4-6
    COMPLEX = "complex"  # → opus-4-7


# Model IDs used by the router
MODEL_MAP = {
    TaskComplexity.SIMPLE: "claude-haiku-4-5",
    TaskComplexity.STANDARD: "claude-sonnet-4-6",
    TaskComplexity.COMPLEX: "claude-opus-4-7",
}

# $/1M tokens for cost logging
PRICING = {
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-7": {"input": 5.00, "output": 25.00},
}

_COMPLEX_KEYWORDS = re.compile(
    r"\b(reason|analyze|compare|evaluate|debate|multi.?step|agent|plan|"
    r"architecture|design|refactor|implement|algorithm)\b",
    re.I,
)
_SIMPLE_KEYWORDS = re.compile(
    r"\b(classify|label|yes.?or.?no|true.?or.?false|summarize|translate|"
    r"extract|format|convert|list|what is|define)\b",
    re.I,
)


@dataclass
class RoutingDecision:
    model: str
    complexity: TaskComplexity
    reason: str


class ModelRouter:
    """
    Classifies a request and returns the cheapest adequate model.

    Usage:
        router = ModelRouter()
        decision = router.route(messages, system="...", expected_output_tokens=500)
        client.messages.create(model=decision.model, ...)
    """

    def __init__(
        self,
        simple_token_threshold: int = 500,
        complex_token_threshold: int = 3000,
    ):
        self._simple_thresh = simple_token_threshold
        self._complex_thresh = complex_token_threshold

    def route(
        self,
        messages: list[dict],
        system: str = "",
        expected_output_tokens: int = 1000,
        force: TaskComplexity | None = None,
    ) -> RoutingDecision:
        if force is not None:
            model = MODEL_MAP[force]
            return RoutingDecision(model, force, "forced by caller")

        complexity, reason = self._classify(messages, system, expected_output_tokens)
        return RoutingDecision(MODEL_MAP[complexity], complexity, reason)

    def _classify(
        self,
        messages: list[dict],
        system: str,
        expected_output_tokens: int,
    ) -> tuple[TaskComplexity, str]:
        # Combine all text for analysis
        text = " ".join(
            (m.get("content") or "")
            if isinstance(m.get("content"), str)
            else " ".join(b.get("text", "") for b in m.get("content", []) if isinstance(b, dict))
            for m in messages
        )
        combined = (system + " " + text).strip()
        approx_tokens = len(combined.split())

        if approx_tokens > self._complex_thresh or expected_output_tokens > 4000:
            return TaskComplexity.COMPLEX, f"large context ({approx_tokens} words)"

        if _COMPLEX_KEYWORDS.search(combined):
            return TaskComplexity.COMPLEX, "complex task keywords detected"

        if approx_tokens < self._simple_thresh and _SIMPLE_KEYWORDS.search(combined):
            return TaskComplexity.SIMPLE, "simple task with few tokens"

        if approx_tokens < self._simple_thresh and expected_output_tokens < 300:
            return TaskComplexity.SIMPLE, f"small request ({approx_tokens} words, short output)"

        return TaskComplexity.STANDARD, "default standard task"

    @staticmethod
    def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        """Returns estimated cost in USD."""
        p = PRICING.get(model, PRICING["claude-sonnet-4-6"])
        return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000
