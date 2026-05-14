"""
Context compression — two strategies for keeping conversations affordable:

1. Server-side compaction (beta: compact-2026-01-12)
   The API automatically summarizes earlier turns when context grows large.
   Works on Opus 4.7, Opus 4.6, Sonnet 4.6.
   Critical: append response.content (not just text) so compaction blocks survive.

2. Client-side summarization
   When conversation exceeds a token threshold, ask Claude to summarize
   the history, then restart with just the summary. Useful for older models
   or when you want deterministic control over what's preserved.
"""

from __future__ import annotations

import anthropic


class ContextCompressor:
    """
    Manages long conversations with automatic compression.

    Usage (server-side compaction):
        cc = ContextCompressor(client, strategy="server")
        reply = cc.chat("Tell me about Python")
        reply = cc.chat("Now explain decorators")  # compaction happens automatically

    Usage (client-side summarization):
        cc = ContextCompressor(client, strategy="client", max_tokens_before_compress=8000)
        reply = cc.chat("...")
    """

    def __init__(
        self,
        client: anthropic.Anthropic,
        model: str = "claude-opus-4-7",
        strategy: str = "server",           # "server" | "client"
        max_tokens_before_compress: int = 10_000,
        system: str = "You are a helpful assistant.",
    ) -> None:
        self._client = client
        self._model = model
        self._strategy = strategy
        self._max_tokens = max_tokens_before_compress
        self._system = system
        self._history: list = []             # beta message params for server / dicts for client
        self._total_tokens_used = 0
        self._compressions_done = 0

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def chat(self, user_message: str) -> str:
        if self._strategy == "server":
            return self._chat_server_compaction(user_message)
        return self._chat_client_summarization(user_message)

    @property
    def stats(self) -> dict:
        return {
            "turns": len(self._history) // 2,
            "total_tokens_used": self._total_tokens_used,
            "compressions": self._compressions_done,
        }

    def reset(self) -> None:
        self._history = []
        self._total_tokens_used = 0
        self._compressions_done = 0

    # ------------------------------------------------------------------ #
    # Strategy 1: server-side compaction                                  #
    # ------------------------------------------------------------------ #

    def _chat_server_compaction(self, user_message: str) -> str:
        """
        Uses the beta compaction API. The server automatically summarizes
        earlier context when it approaches the trigger threshold.

        CRITICAL: append response.content (the full list, not just text)
        so compaction blocks survive in the history.
        """
        self._history.append({"role": "user", "content": user_message})

        response = self._client.beta.messages.create(
            betas=["compact-2026-01-12"],
            model=self._model,
            max_tokens=4096,
            system=self._system,
            messages=self._history,
            context_management={
                "edits": [{"type": "compact_20260112"}]
            },
        )

        # Must append full content list — not just the text string
        self._history.append({"role": "assistant", "content": response.content})
        self._total_tokens_used += (
            (getattr(response.usage, "input_tokens", 0) or 0)
            + (getattr(response.usage, "output_tokens", 0) or 0)
        )

        # Check if compaction occurred this turn
        for block in response.content:
            if getattr(block, "type", None) == "compaction":
                self._compressions_done += 1
                break

        return next(
            (b.text for b in response.content if getattr(b, "type", None) == "text"),
            "",
        )

    # ------------------------------------------------------------------ #
    # Strategy 2: client-side summarization                               #
    # ------------------------------------------------------------------ #

    def _chat_client_summarization(self, user_message: str) -> str:
        """
        Estimates token usage. When the history grows beyond the threshold,
        summarizes it with a separate Claude call, then continues with the summary.
        """
        self._history.append({"role": "user", "content": user_message})

        # Estimate whether compression is needed
        if self._estimate_tokens() > self._max_tokens and len(self._history) > 4:
            self._compress_client_side()

        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=self._system,
            messages=self._history,
        )

        reply_text = next(
            (b.text for b in response.content if b.type == "text"), ""
        )
        self._history.append({"role": "assistant", "content": reply_text})
        self._total_tokens_used += (
            (getattr(response.usage, "input_tokens", 0) or 0)
            + (getattr(response.usage, "output_tokens", 0) or 0)
        )
        return reply_text

    def _compress_client_side(self) -> None:
        """Summarize the current history into a compact system note."""
        # Build a transcript for summarization (exclude the new user message)
        history_to_summarize = self._history[:-1]
        transcript = "\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in history_to_summarize
            if isinstance(m.get("content"), str)
        )

        summary_response = self._client.messages.create(
            model="claude-haiku-4-5",  # use cheapest model to summarize
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Summarize the following conversation history concisely. "
                        "Preserve key facts, decisions, and context the assistant will need.\n\n"
                        f"{transcript}"
                    ),
                }
            ],
        )
        summary = next(
            (b.text for b in summary_response.content if b.type == "text"), ""
        )

        # Replace history with the summary + most-recent user message
        new_user_msg = self._history[-1]
        self._history = [
            {
                "role": "user",
                "content": f"[Conversation summary]\n{summary}",
            },
            {
                "role": "assistant",
                "content": "Understood. I'll continue based on our conversation so far.",
            },
            new_user_msg,
        ]
        self._compressions_done += 1

    def _estimate_tokens(self) -> int:
        """Rough word-count estimate (actual tokenization varies by model)."""
        total = 0
        for m in self._history:
            content = m.get("content", "")
            if isinstance(content, str):
                total += len(content.split())
            elif isinstance(content, list):
                for block in content:
                    total += len(block.get("text", "").split())
        return total
