"""
demo.py — Lynq token optimizer demo

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python demo.py
"""

from __future__ import annotations

import os

import anthropic

from token_optimizer import (
    BatchProcessor,
    CacheManager,
    ContextCompressor,
    CostEstimator,
    ModelRouter,
    OptimizedClient,
    TaskComplexity,
    TokenCounter,
)

SEPARATOR = "=" * 60


def demo_routing() -> None:
    print(f"\n{SEPARATOR}")
    print("1. Smart Model Routing")
    print(SEPARATOR)

    router = ModelRouter()
    cases = [
        (
            [{"role": "user", "content": "Classify as positive / negative: This was amazing!"}],
            "",
            100,
        ),
        (
            [{"role": "user", "content": "Please summarize this article."}],
            "You are a writer.",
            500,
        ),
        (
            [{"role": "user", "content": "Design and implement a Python decorator pattern."}],
            "You are a senior engineer.",
            2000,
        ),
    ]
    for messages, system, out_tokens in cases:
        decision = router.route(messages, system=system, expected_output_tokens=out_tokens)
        prompt = messages[0]["content"][:40]
        print(f"  [{decision.complexity.value:8s}] {decision.model:25s} ← {prompt}…")
        print(f"             Reason: {decision.reason}")


def demo_caching(client: anthropic.Anthropic) -> None:
    print(f"\n{SEPARATOR}")
    print("2. Prompt Caching")
    print(SEPARATOR)

    cm = CacheManager()
    cost = CostEstimator("claude-haiku-4-5")

    STABLE_SYSTEM = (
        "You are a polite and helpful assistant. " * 60  # ~1000 tokens of stable content
    )

    questions = [
        "Hello!",
        "What's the weather like today?",
        "Can you recommend a book?",
    ]

    print(f"  Stable system prompt: {len(STABLE_SYSTEM)} chars")
    print()

    for i, q in enumerate(questions, 1):
        system_blocks = cm.cached_system(STABLE_SYSTEM, ttl="5m")
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=128,
            system=system_blocks,
            messages=[{"role": "user", "content": q}],
        )
        cm.record_usage(response.usage)
        this_cost = cost.record(response.usage)
        u = response.usage
        print(
            f"  Request {i}: "
            f"input={getattr(u, 'input_tokens', 0):4d} "
            f"write={getattr(u, 'cache_creation_input_tokens', 0):4d} "
            f"read={getattr(u, 'cache_read_input_tokens', 0):4d} "
            f"cost=${this_cost:.6f}"
        )

    print(f"\n  Cache stats: {cm.stats.savings_summary}")


def demo_compression(client: anthropic.Anthropic) -> None:
    print(f"\n{SEPARATOR}")
    print("3. Context Compression (client-side summarization)")
    print(SEPARATOR)

    cc = ContextCompressor(
        client,
        model="claude-haiku-4-5",
        strategy="client",
        max_tokens_before_compress=300,  # low threshold for demo
        system="You are a knowledgeable assistant.",
    )

    turns = [
        "What is Python?",
        "How do I use list comprehensions?",
        "Can you explain decorators?",
        "How do I write async code?",
        "What is the syntax for type hints?",
    ]

    for turn in turns:
        reply = cc.chat(turn)
        print(f"  Q: {turn}")
        print(f"  A: {reply[:80]}…" if len(reply) > 80 else f"  A: {reply}")
        print(f"     [compressions: {cc.stats['compressions']}]")
        print()


def demo_batch(client: anthropic.Anthropic) -> None:
    print(f"\n{SEPARATOR}")
    print("4. Batch API (50% cost reduction)")
    print(SEPARATOR)

    bp = BatchProcessor(
        client,
        model="claude-haiku-4-5",
        max_tokens=64,
        system="Perform sentiment analysis. Answer with exactly one word: 'positive' or 'negative'.",
        poll_interval=5,
    )

    items = [
        {"id": "r1", "prompt": "This product was absolutely amazing!"},
        {"id": "r2", "prompt": "Terrible service, I will never use this again."},
        {"id": "r3", "prompt": "It was okay, nothing special."},
        {"id": "r4", "prompt": "Great value for the price, very satisfied!"},
        {"id": "r5", "prompt": "Delivery was way too slow, worst experience ever."},
    ]

    print(f"  Submitting {len(items)} items as a batch…")
    results = bp.run(items)

    total_tokens = sum(r.tokens_used for r in results)
    print()
    for r in results:
        status = r.text or f"ERROR: {r.error}"
        print(f"  [{r.custom_id}] {status}")
    print(f"\n  Total tokens: {total_tokens:,} (50% of standard cost)")


def demo_token_counting(client: anthropic.Anthropic) -> None:
    print(f"\n{SEPARATOR}")
    print("5. Pre-flight Token Counting (cost estimation)")
    print(SEPARATOR)

    counter = TokenCounter(client, model="claude-sonnet-4-6")
    estimator = CostEstimator("claude-sonnet-4-6")

    scenarios = [
        {
            "name": "Short question",
            "messages": [{"role": "user", "content": "Hello!"}],
            "expected_output": 50,
        },
        {
            "name": "Long summarization request",
            "messages": [
                {
                    "role": "user",
                    "content": "Please summarize the following:\n"
                    + "Python is a general-purpose programming language. " * 50,
                }
            ],
            "expected_output": 200,
        },
    ]

    for s in scenarios:
        input_tokens = counter.count(s["messages"])
        est_cost = estimator.estimate(input_tokens, s["expected_output"])
        print(f"  [{s['name']}]")
        print(f"    Input tokens:    {input_tokens:,}")
        print(f"    Estimated cost:  ${est_cost:.6f} USD")
        print()


def demo_optimized_client() -> None:
    print(f"\n{SEPARATOR}")
    print("6. OptimizedClient (all techniques combined)")
    print(SEPARATOR)

    oc = OptimizedClient(
        stable_system="You are a polite and helpful assistant.",
        cache_ttl="5m",
        auto_route=True,
        default_max_tokens=256,
    )

    queries = [
        ("Classify: The movie was enjoyable", TaskComplexity.SIMPLE),
        ("Explain Python generators", None),
    ]

    for q, force in queries:
        reply = oc.chat(q, effort="low", force_complexity=force)
        print(f"  Q: {q}")
        print(f"  A: {reply[:100]}…" if len(reply) > 100 else f"  A: {reply}")
        print()

    print(f"  Cache:  {oc.cache_stats}")
    print(f"  Cost:   {oc.cost_summary}")


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        return

    client = anthropic.Anthropic(api_key=api_key)

    print("\n🚀 Lynq — Claude Token Optimization Demo")
    print("=" * 60)

    demo_routing()
    demo_caching(client)
    demo_token_counting(client)
    demo_compression(client)
    demo_optimized_client()

    # Batch demo is last (makes multiple API calls — uncomment to run)
    # demo_batch(client)

    print(f"\n{SEPARATOR}")
    print("Done!")


if __name__ == "__main__":
    main()
