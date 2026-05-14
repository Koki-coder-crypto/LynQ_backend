"""
Batch processing — 50% cost reduction for non-latency-sensitive workloads.

Limits: up to 100,000 requests or 256 MB per batch.
Most batches complete within 1 hour; max 24 hours.
Results available for 29 days.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import anthropic


@dataclass
class BatchResult:
    custom_id: str
    text: str | None
    error: str | None
    tokens_used: int


class BatchProcessor:
    """
    Submit many independent requests at 50% of standard API cost.
    Use for classification, summarization, extraction pipelines.

    Example:
        bp = BatchProcessor(client, model="claude-haiku-4-5")
        results = bp.run([
            {"id": "1", "prompt": "Classify: The product is great!"},
            {"id": "2", "prompt": "Classify: Terrible experience."},
        ])
    """

    def __init__(
        self,
        client: anthropic.Anthropic,
        model: str = "claude-haiku-4-5",
        max_tokens: int = 256,
        system: str = "",
        poll_interval: int = 30,
    ) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens
        self._system = system
        self._poll_interval = poll_interval

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def run(
        self,
        items: list[dict[str, Any]],
        shared_system: str | None = None,
    ) -> list[BatchResult]:
        """
        Submit a batch and block until results are available.

        items: list of {"id": str, "prompt": str} dicts.
        shared_system: overrides self._system for this batch.
        Returns list of BatchResult, preserving input order.
        """
        system = shared_system if shared_system is not None else self._system
        requests = self._build_requests(items, system)

        batch = self._client.messages.batches.create(requests=requests)
        batch_id = batch.id
        print(f"[Batch] Submitted {len(requests)} requests → {batch_id}")

        # Poll until complete
        while True:
            batch = self._client.messages.batches.retrieve(batch_id)
            counts = batch.request_counts
            if batch.processing_status == "ended":
                break
            print(
                f"[Batch] {batch_id} — processing: {counts.processing} / "
                f"succeeded: {counts.succeeded} / errored: {counts.errored}"
            )
            time.sleep(self._poll_interval)

        print(
            f"[Batch] Complete — "
            f"succeeded: {batch.request_counts.succeeded}, "
            f"errored: {batch.request_counts.errored}"
        )
        return self._collect_results(batch_id)

    def submit_async(
        self,
        items: list[dict[str, Any]],
        shared_system: str | None = None,
    ) -> str:
        """
        Submit a batch without waiting. Returns batch_id.
        Call collect(batch_id) later to retrieve results.
        """
        system = shared_system if shared_system is not None else self._system
        requests = self._build_requests(items, system)
        batch = self._client.messages.batches.create(requests=requests)
        return batch.id

    def collect(self, batch_id: str) -> list[BatchResult] | None:
        """
        Check status and return results if ready, else None.
        """
        batch = self._client.messages.batches.retrieve(batch_id)
        if batch.processing_status != "ended":
            return None
        return self._collect_results(batch_id)

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    def _build_requests(
        self,
        items: list[dict[str, Any]],
        system: str,
    ) -> list[dict]:
        requests = []
        for item in items:
            params: dict[str, Any] = {
                "model": self._model,
                "max_tokens": self._max_tokens,
                "messages": [{"role": "user", "content": item["prompt"]}],
            }
            if system:
                params["system"] = system
            requests.append(
                {
                    "custom_id": item["id"],
                    "params": params,
                }
            )
        return requests

    def _collect_results(self, batch_id: str) -> list[BatchResult]:
        results: dict[str, BatchResult] = {}
        for result in self._client.messages.batches.results(batch_id):
            custom_id = result.custom_id
            if result.result.type == "succeeded":
                msg = result.result.message
                text = next((b.text for b in msg.content if b.type == "text"), "")
                tokens = (getattr(msg.usage, "input_tokens", 0) or 0) + (
                    getattr(msg.usage, "output_tokens", 0) or 0
                )
                results[custom_id] = BatchResult(custom_id, text, None, tokens)
            elif result.result.type == "errored":
                err = getattr(result.result, "error", None)
                msg = getattr(err, "message", str(err)) if err else "unknown error"
                results[custom_id] = BatchResult(custom_id, None, msg, 0)
            else:
                results[custom_id] = BatchResult(
                    custom_id, None, f"status: {result.result.type}", 0
                )
        return list(results.values())
