"""
demo.py — Habitly token optimizer デモ

実行方法:
    export ANTHROPIC_API_KEY=sk-ant-...
    python demo.py
"""

from __future__ import annotations

import os
import time
import anthropic

from token_optimizer import (
    OptimizedClient,
    CacheManager,
    ModelRouter,
    TaskComplexity,
    ContextCompressor,
    BatchProcessor,
    TokenCounter,
    CostEstimator,
)

SEPARATOR = "=" * 60


def demo_routing() -> None:
    print(f"\n{SEPARATOR}")
    print("1. スマートモデルルーティング")
    print(SEPARATOR)

    router = ModelRouter()
    cases = [
        (
            [{"role": "user", "content": "ポジティブ / ネガティブで分類して: 最高でした！"}],
            "",
            100,
        ),
        (
            [{"role": "user", "content": "この記事を要約してください。"}],
            "あなたはライターです。",
            500,
        ),
        (
            [{"role": "user", "content": "Pythonのデコレータパターンを設計・実装してください。"}],
            "あなたはシニアエンジニアです。",
            2000,
        ),
    ]
    for messages, system, out_tokens in cases:
        decision = router.route(messages, system=system, expected_output_tokens=out_tokens)
        prompt = messages[0]["content"][:40]
        print(f"  [{decision.complexity.value:8s}] {decision.model:25s} ← {prompt}…")
        print(f"             理由: {decision.reason}")


def demo_caching(client: anthropic.Anthropic) -> None:
    print(f"\n{SEPARATOR}")
    print("2. プロンプトキャッシング")
    print(SEPARATOR)

    cm = CacheManager()
    cost = CostEstimator("claude-haiku-4-5")

    STABLE_SYSTEM = (
        "あなたは日本語で回答する丁寧なアシスタントです。" * 60  # ~1000トークン相当の安定コンテンツ
    )

    questions = [
        "こんにちは！",
        "今日の天気は？",
        "おすすめの本は？",
    ]

    print(f"  安定システムプロンプト: {len(STABLE_SYSTEM)} 文字")
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
            f"  リクエスト {i}: "
            f"入力={getattr(u,'input_tokens',0):4d} "
            f"書込={getattr(u,'cache_creation_input_tokens',0):4d} "
            f"読込={getattr(u,'cache_read_input_tokens',0):4d} "
            f"コスト=${this_cost:.6f}"
        )

    print(f"\n  キャッシュ統計: {cm.stats.savings_summary}")


def demo_compression(client: anthropic.Anthropic) -> None:
    print(f"\n{SEPARATOR}")
    print("3. コンテキスト圧縮（クライアントサイド要約）")
    print(SEPARATOR)

    cc = ContextCompressor(
        client,
        model="claude-haiku-4-5",
        strategy="client",
        max_tokens_before_compress=300,   # デモ用に低い閾値
        system="あなたは物知りなアシスタントです。",
    )

    turns = [
        "Pythonとは何ですか？",
        "リスト内包表記の使い方を教えてください。",
        "デコレータについて説明してください。",
        "非同期処理はどう書きますか？",
        "型ヒントの書き方は？",
    ]

    for turn in turns:
        reply = cc.chat(turn)
        print(f"  Q: {turn}")
        print(f"  A: {reply[:80]}…" if len(reply) > 80 else f"  A: {reply}")
        print(f"     [圧縮回数: {cc.stats['compressions']}]")
        print()


def demo_batch(client: anthropic.Anthropic) -> None:
    print(f"\n{SEPARATOR}")
    print("4. バッチAPI（50%コスト削減）")
    print(SEPARATOR)

    bp = BatchProcessor(
        client,
        model="claude-haiku-4-5",
        max_tokens=64,
        system="感情分析してください。'ポジティブ'または'ネガティブ'の1単語で答えてください。",
        poll_interval=5,
    )

    items = [
        {"id": "r1", "prompt": "この商品は最高でした！"},
        {"id": "r2", "prompt": "全くひどいサービスで二度と使いません。"},
        {"id": "r3", "prompt": "普通ですが特に感動はありません。"},
        {"id": "r4", "prompt": "価格に見合った品質で満足しています！"},
        {"id": "r5", "prompt": "配送が遅すぎて最悪でした。"},
    ]

    print(f"  {len(items)} 件を一括送信中…")
    results = bp.run(items)

    total_tokens = sum(r.tokens_used for r in results)
    print()
    for r in results:
        status = r.text or f"ERROR: {r.error}"
        print(f"  [{r.custom_id}] {status}")
    print(f"\n  合計トークン: {total_tokens:,} (通常の50%のコスト)")


def demo_token_counting(client: anthropic.Anthropic) -> None:
    print(f"\n{SEPARATOR}")
    print("5. 事前トークンカウント（コスト予測）")
    print(SEPARATOR)

    counter = TokenCounter(client, model="claude-sonnet-4-6")
    estimator = CostEstimator("claude-sonnet-4-6")

    scenarios = [
        {
            "name": "短い質問",
            "messages": [{"role": "user", "content": "こんにちは！"}],
            "expected_output": 50,
        },
        {
            "name": "長文要約依頼",
            "messages": [
                {
                    "role": "user",
                    "content": "以下の文章を要約してください：\n" + "Pythonは汎用プログラミング言語です。" * 50,
                }
            ],
            "expected_output": 200,
        },
    ]

    for s in scenarios:
        input_tokens = counter.count(s["messages"])
        est_cost = estimator.estimate(input_tokens, s["expected_output"])
        print(f"  [{s['name']}]")
        print(f"    入力トークン: {input_tokens:,}")
        print(f"    推定コスト:   ${est_cost:.6f} USD")
        print()


def demo_optimized_client() -> None:
    print(f"\n{SEPARATOR}")
    print("6. OptimizedClient（全手法の統合）")
    print(SEPARATOR)

    oc = OptimizedClient(
        stable_system="あなたは丁寧な日本語アシスタントです。",
        cache_ttl="5m",
        auto_route=True,
        default_max_tokens=256,
    )

    queries = [
        ("分類して: 映画が面白かった", TaskComplexity.SIMPLE),
        ("Pythonのジェネレータを説明してください", None),
    ]

    for q, force in queries:
        reply = oc.chat(q, effort="low", force_complexity=force)
        print(f"  Q: {q}")
        print(f"  A: {reply[:100]}…" if len(reply) > 100 else f"  A: {reply}")
        print()

    print(f"  キャッシュ: {oc.cache_stats}")
    print(f"  コスト:     {oc.cost_summary}")


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY 環境変数が設定されていません")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        return

    client = anthropic.Anthropic(api_key=api_key)

    print("\n🚀 Habitly — Claude トークン最適化デモ")
    print("=" * 60)

    demo_routing()
    demo_caching(client)
    demo_token_counting(client)
    demo_compression(client)
    demo_optimized_client()

    # バッチはAPIコールが多いため最後（コメントアウトで任意実行）
    # demo_batch(client)

    print(f"\n{SEPARATOR}")
    print("完了！")


if __name__ == "__main__":
    main()
