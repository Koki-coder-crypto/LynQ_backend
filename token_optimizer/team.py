#!/usr/bin/env python3
"""
team.py — Director主導チームエージェント並列処理UI

仕組み:
  1. ユーザーが入力 → Director(sonnet)に送信
  2. Directorがタスクを分析し <<<DISPATCH>>> 形式でチームに指示
  3. アプリがDispatchを検出 → Coder・Research を asyncio.gather で並列実行
  4. 結果をDirectorに返す → Directorが統合して最終回答

起動:
    export ANTHROPIC_API_KEY=sk-ant-...
    claude-team                  # 本番モード
    claude-team --demo           # デモ（API不要）
    claude-team --preset dev     # 開発チーム
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

from anthropic import AsyncAnthropic
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Label, ProgressBar, RichLog, Static
from textual import work

# ── 定数 ─────────────────────────────────────────────────────────────────── #

CONTEXT_WINDOWS = {
    "claude-haiku-4-5":    200_000,
    "claude-sonnet-4-6":  1_000_000,
    "claude-opus-4-7":    1_000_000,
}
PRICING = {
    "claude-haiku-4-5":   {"input": 1.00,  "output": 5.00},
    "claude-sonnet-4-6":  {"input": 3.00,  "output": 15.00},
    "claude-opus-4-7":    {"input": 5.00,  "output": 25.00},
}

# Directorのシステムプロンプト
DIRECTOR_SYSTEM = """\
あなたはAIチームの司令官（Director）です。
ユーザーのリクエストを受け取り、チームを指揮します。

チームメンバー:
- CODER  : Python実装・コード生成・技術的な実装
- RESEARCH: 情報調査・ベストプラクティス・分析・比較

【ルール】
1. 複数エージェントで並列処理できるタスクは以下の形式で指示してください:
   <<<DISPATCH>>>
   CODER: [Coderへの具体的な指示 - 1〜2文]
   RESEARCH: [Researchへの具体的な指示 - 1〜2文]
   <<<END_DISPATCH>>>

2. DISPATCHブロックの後に、あなたの計画や概要を簡単に説明してください。

3. チームの結果を受け取ったら、それを統合して最終的な回答をまとめてください。

4. 単純な質問には自分で直接答えてください（DISPATCHは不要）。

必ず日本語で回答してください。
"""


# ── データクラス ──────────────────────────────────────────────────────────── #

@dataclass
class WorkerConfig:
    name:       str
    model:      str
    system:     str
    color:      str = "green"
    max_tokens: int = 1024


@dataclass
class WorkerState:
    config:       WorkerConfig
    input_tokens:  int = 0
    output_tokens: int = 0

    @property
    def context_pct(self) -> float:
        window = CONTEXT_WINDOWS.get(self.config.model, 200_000)
        return min(1.0, self.input_tokens / window)

    @property
    def cost_usd(self) -> float:
        p = PRICING.get(self.config.model, PRICING["claude-haiku-4-5"])
        return (self.input_tokens * p["input"] + self.output_tokens * p["output"]) / 1_000_000


# ── プリセット ────────────────────────────────────────────────────────────── #

WORKER_PRESETS: dict[str, list[WorkerConfig]] = {
    "default": [
        WorkerConfig("Coder",    "claude-haiku-4-5", color="green",
                     system="あなたはPythonエキスパートです。型ヒント付きで簡潔なコードを書いてください。説明は最小限に。"),
        WorkerConfig("Research", "claude-haiku-4-5", color="yellow",
                     system="あなたは調査の専門家です。事実と要点を箇条書きで簡潔にまとめてください。"),
    ],
    "dev": [
        WorkerConfig("Coder",    "claude-haiku-4-5", color="green",
                     system="あなたはシニアPythonエンジニアです。本番品質のコードを書いてください。"),
        WorkerConfig("Reviewer", "claude-haiku-4-5", color="magenta",
                     system="あなたはコードレビュアーです。問題点と改善案を箇条書きで指摘してください。"),
    ],
    "research": [
        WorkerConfig("Finder",   "claude-haiku-4-5", color="yellow",
                     system="あなたは情報収集の専門家です。関連する事実と数字を列挙してください。"),
        WorkerConfig("Analyst",  "claude-haiku-4-5", color="cyan",
                     system="あなたはアナリストです。データを分析してパターンと洞察を導いてください。"),
    ],
    "minimal": [
        WorkerConfig("Worker",   "claude-haiku-4-5", color="green",
                     system="あなたは汎用アシスタントです。簡潔に回答してください。"),
    ],
}


# ── ユーティリティ ────────────────────────────────────────────────────────── #

def parse_dispatch(text: str) -> dict[str, str]:
    """<<<DISPATCH>>>ブロックからエージェント指示を抽出する"""
    m = re.search(r'<<<DISPATCH>>>(.*?)<<<END_DISPATCH>>>', text, re.DOTALL)
    if not m:
        return {}
    tasks: dict[str, str] = {}
    for line in m.group(1).strip().splitlines():
        line = line.strip()
        if ':' in line:
            agent, task = line.split(':', 1)
            tasks[agent.strip().upper()] = task.strip()
    return tasks


# ── ウィジェット ──────────────────────────────────────────────────────────── #

class StreamBuf(Static):
    """ストリーミングテキストバッファ"""
    def __init__(self, **kw):
        super().__init__("", **kw)
        self._buf = ""

    def append(self, text: str) -> None:
        self._buf += text
        self.update(self._buf)

    def reset(self, initial: str = "") -> None:
        self._buf = initial
        self.update(self._buf)

    @property
    def text(self) -> str:
        return self._buf


class DirectorPanel(Vertical):
    """左ペイン: Director との会話"""
    DEFAULT_CSS = """
    DirectorPanel {
        width: 45%;
        border: double $success;
        padding: 0 1;
    }
    DirectorPanel #d-title { height: 1; text-style: bold; background: $success-darken-2; padding: 0 1; }
    DirectorPanel #d-log   { height: 1fr; background: $surface; }
    DirectorPanel #d-stream{ height: auto; min-height: 1; max-height: 8; background: $surface; color: $text-muted; padding: 0 1; }
    DirectorPanel #d-ctx-bar{ height: 1; }
    DirectorPanel #d-stat  { height: 1; padding: 0 1; }
    """

    def __init__(self, model: str = "claude-sonnet-4-6", **kw):
        super().__init__(**kw)
        self.model = model
        self.input_tokens = 0
        self.output_tokens = 0

    def compose(self) -> ComposeResult:
        m = self.model.replace("claude-", "")
        yield Label(f"[bold green]■ Director[/]  [dim]{m}[/]  [dim]←ここに入力[/]", id="d-title")
        yield RichLog(id="d-log", highlight=True, markup=True, wrap=True)
        yield StreamBuf(id="d-stream")
        yield ProgressBar(total=100, show_eta=False, id="d-ctx-bar")
        yield Label("[dim]待機中[/]", id="d-stat", markup=True)

    def add_user(self, text: str) -> None:
        self.query_one("#d-log", RichLog).write(f"[bold cyan]You:[/] {text}")

    def start_reply(self, prefix: str = "[bold green]Director:[/] ") -> None:
        self.query_one("#d-stream", StreamBuf).reset(prefix)

    def stream(self, chunk: str) -> None:
        self.query_one("#d-stream", StreamBuf).append(chunk)

    def finish_reply(self) -> None:
        buf = self.query_one("#d-stream", StreamBuf)
        self.query_one("#d-log", RichLog).write(buf.text)
        buf.reset()

    def set_status(self, msg: str) -> None:
        self.query_one("#d-stream", StreamBuf).reset(msg)

    def update_stats(self) -> None:
        window = CONTEXT_WINDOWS.get(self.model, 1_000_000)
        pct = min(1.0, self.input_tokens / window) * 100
        p = PRICING.get(self.model, PRICING["claude-sonnet-4-6"])
        cost = (self.input_tokens * p["input"] + self.output_tokens * p["output"]) / 1_000_000
        self.query_one("#d-ctx-bar", ProgressBar).progress = pct
        col = "green" if pct < 50 else ("yellow" if pct < 80 else "red")
        self.query_one("#d-stat", Label).update(
            f"[{col}]ctx {pct:.1f}%[/]  {self.input_tokens/1000:.1f}K tokens  [dim]${cost:.4f}[/]"
        )


class WorkerPanel(Vertical):
    """右ペイン内: ワーカーエージェント"""
    DEFAULT_CSS = """
    WorkerPanel {
        width: 1fr;
        border: solid $panel-lighten-2;
        padding: 0 1;
    }
    WorkerPanel #w-title  { height: 1; text-style: bold; background: $panel-lighten-1; padding: 0 1; }
    WorkerPanel #w-log    { height: 1fr; background: $surface; }
    WorkerPanel #w-stream { height: auto; min-height: 1; max-height: 5; background: $surface; color: $text-muted; padding: 0 1; }
    WorkerPanel #w-bar    { height: 1; }
    WorkerPanel #w-stat   { height: 1; padding: 0 1; }
    """

    def __init__(self, state: WorkerState, **kw):
        super().__init__(**kw)
        self.state = state

    def compose(self) -> ComposeResult:
        cfg = self.state.config
        m = cfg.model.replace("claude-", "")
        yield Label(f"[bold {cfg.color}]■ {cfg.name}[/]  [dim]{m}[/]", id="w-title")
        yield RichLog(id="w-log", highlight=True, markup=True, wrap=True)
        yield StreamBuf(id="w-stream")
        yield ProgressBar(total=100, show_eta=False, id="w-bar")
        yield Label("[dim]待機中[/]", id="w-stat", markup=True)

    def start_task(self, task: str) -> None:
        self.query_one("#w-log", RichLog).write(f"[dim]← {task[:60]}{'…' if len(task)>60 else ''}[/]")
        self.query_one("#w-stream", StreamBuf).reset(f"[bold {self.state.config.color}]{self.state.config.name}:[/] ")

    def stream(self, chunk: str) -> None:
        self.query_one("#w-stream", StreamBuf).append(chunk)

    def finish(self) -> None:
        buf = self.query_one("#w-stream", StreamBuf)
        self.query_one("#w-log", RichLog).write(buf.text)
        buf.reset()

    def set_status(self, msg: str) -> None:
        self.query_one("#w-stream", StreamBuf).reset(msg)

    def update_stats(self) -> None:
        s = self.state
        pct = s.context_pct * 100
        col = "green" if pct < 50 else ("yellow" if pct < 80 else "red")
        self.query_one("#w-bar", ProgressBar).progress = pct
        self.query_one("#w-stat", Label).update(
            f"[{col}]ctx {pct:.1f}%[/]  {s.input_tokens/1000:.1f}K  [dim]${s.cost_usd:.4f}[/]"
        )


class GlobalBar(Static):
    DEFAULT_CSS = """
    GlobalBar {
        height: 1; background: $primary-darken-2; color: $text;
        text-align: center; padding: 0 1;
    }
    """

    def update_stats(self, dir_panel: DirectorPanel, workers: list[WorkerState], start: float) -> None:
        elapsed = time.time() - start
        mins, secs = divmod(int(elapsed), 60)
        all_inp  = dir_panel.input_tokens  + sum(w.input_tokens  for w in workers)
        all_out  = dir_panel.output_tokens + sum(w.output_tokens for w in workers)
        all_cost = (
            (dir_panel.input_tokens  * PRICING["claude-sonnet-4-6"]["input"]
             + dir_panel.output_tokens * PRICING["claude-sonnet-4-6"]["output"]) / 1_000_000
            + sum(w.cost_usd for w in workers)
        )
        self.update(
            f"合計: [bold]{all_inp+all_out:,}[/] tokens  |  "
            f"コスト: [bold]${all_cost:.4f}[/]  |  "
            f"経過: {mins}m {secs:02d}s  |  "
            f"[green]Director→Worker で自動並列処理[/]"
        )


# ── メインアプリ ──────────────────────────────────────────────────────────── #

class DirectorTeamApp(App[None]):
    """Director主導チームエージェント UI"""

    TITLE     = "Claude Team — Director 自動指揮"
    SUB_TITLE = "入力 → Director へ自動送信 → チームが並列処理  |  Ctrl+Q=終了"

    CSS = """
    Screen { layout: vertical; }
    #main-area { height: 1fr; layout: horizontal; }
    #worker-area { width: 55%; layout: horizontal; }
    #input-row { height: 3; layout: horizontal; padding: 0 1; align: left middle; }
    #user-input { width: 1fr; margin: 0 1 0 0; }
    #send-btn { width: 20; }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "終了"),
        Binding("escape", "quit", "終了", show=False),
    ]

    def __init__(self, workers: list[WorkerConfig], demo: bool = False) -> None:
        super().__init__()
        self._demo          = demo
        self._worker_states = [WorkerState(config=w) for w in workers]
        self._director      = DirectorPanel()
        self._worker_panels: list[WorkerPanel] = []
        self._director_history: list[dict] = []
        self._start         = time.time()
        self._client        = None if demo else AsyncAnthropic()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-area"):
            yield self._director
            with Horizontal(id="worker-area"):
                for state in self._worker_states:
                    p = WorkerPanel(state)
                    self._worker_panels.append(p)
                    yield p
        with Horizontal(id="input-row"):
            yield Input(
                placeholder="Directorに指示を入力… Director が自動でチームに振り分けます",
                id="user-input",
            )
            yield Button("→ Director へ送信", id="send-btn", variant="primary")
        yield GlobalBar("起動中…", id="global-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(3, self._tick)
        self.query_one("#user-input", Input).focus()
        mode = "[yellow]デモモード[/]" if self._demo else "[green]本番モード[/]"
        self._director.set_status(f"[dim]{mode} — 準備完了。指示をどうぞ。[/]")
        for p in self._worker_panels:
            p.set_status("[dim]Director からの指示を待機中…[/]")

    def _tick(self) -> None:
        self.query_one("#global-bar", GlobalBar).update_stats(
            self._director, self._worker_states, self._start
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        msg = event.value.strip()
        if not msg:
            return
        event.input.value = ""
        self._orchestrate(msg)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-btn":
            inp = self.query_one("#user-input", Input)
            msg = inp.value.strip()
            if msg:
                inp.value = ""
                self._orchestrate(msg)

    def _orchestrate(self, message: str) -> None:
        self._run_orchestration(message)

    # ── 並列オーケストレーション ─────────────────────────────────────────── #

    @work(exclusive=False)
    async def _run_orchestration(self, message: str) -> None:
        """
        Director → parse dispatch → workers parallel → Director synthesize
        """
        dir_panel = self._director

        # ① Director へ送信
        dir_panel.add_user(message)
        self._director_history.append({"role": "user", "content": message})
        dir_panel.start_reply()

        director_response = await self._call_director()

        dir_panel.finish_reply()

        # ② Dispatch ブロックを検出
        tasks = parse_dispatch(director_response)

        if not tasks:
            # Dispatch なし → Director が直接回答
            return

        # ③ ワーカーを並列実行
        dir_panel.set_status("[yellow]⚡ チームに配信中… 並列処理を開始します[/]")
        for p in self._worker_panels:
            p.set_status("[yellow]⟳ 処理中…[/]")

        worker_results = await self._run_workers_parallel(tasks)

        # ④ 結果を Director に返す
        results_text = "\n\n".join(
            f"【{name}の結果】\n{result}"
            for name, result in worker_results.items()
        )
        feedback = f"チームの作業が完了しました。以下が各エージェントの結果です：\n\n{results_text}\n\nこれらを統合して最終回答をまとめてください。"

        self._director_history.append({"role": "assistant", "content": director_response})
        self._director_history.append({"role": "user",      "content": feedback})

        dir_panel.start_reply("[bold green]Director (統合):[/] ")
        await self._call_director()
        dir_panel.finish_reply()
        self._tick()

    async def _call_director(self) -> str:
        """Director に API 呼び出しし、ストリーミング表示する"""
        dir_panel = self._director

        if self._demo:
            return await self._demo_director_response()

        full = ""
        try:
            async with self._client.messages.stream(  # type: ignore
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=DIRECTOR_SYSTEM,
                messages=self._director_history,
            ) as stream:
                async for chunk in stream.text_stream:
                    full += chunk
                    dir_panel.stream(chunk)
                final = await stream.get_final_message()
            dir_panel.input_tokens  += final.usage.input_tokens
            dir_panel.output_tokens += final.usage.output_tokens
            dir_panel.update_stats()
        except Exception as e:
            full = f"[ERROR: {e}]"
            dir_panel.stream(full)
        return full

    async def _run_workers_parallel(self, tasks: dict[str, str]) -> dict[str, str]:
        """指定されたタスクを全ワーカーで並列実行する"""
        # ワーカー名→パネルのマッピング
        panel_map: dict[str, tuple[WorkerPanel, WorkerState]] = {}
        for panel, state in zip(self._worker_panels, self._worker_states):
            panel_map[state.config.name.upper()] = (panel, state)

        async def run_one(agent_name: str, task: str) -> tuple[str, str]:
            key = agent_name.upper()
            if key not in panel_map:
                # 一致するパネルがなければ最初のパネルを使う
                key = next(iter(panel_map))
            panel, state = panel_map[key]
            panel.start_task(task)

            if self._demo:
                result = await self._demo_worker_response(state.config.name, task)
            else:
                result = await self._stream_worker(panel, state, task)
            panel.finish()
            panel.update_stats()
            return agent_name, result

        # 全ワーカーを同時起動
        coros = [run_one(name, task) for name, task in tasks.items()]
        results_list = await asyncio.gather(*coros)
        return dict(results_list)

    async def _stream_worker(self, panel: WorkerPanel, state: WorkerState, task: str) -> str:
        """ワーカーの API 呼び出し"""
        full = ""
        try:
            async with self._client.messages.stream(  # type: ignore
                model=state.config.model,
                max_tokens=state.config.max_tokens,
                system=state.config.system,
                messages=[{"role": "user", "content": task}],
            ) as stream:
                async for chunk in stream.text_stream:
                    full += chunk
                    panel.stream(chunk)
                final = await stream.get_final_message()
            state.input_tokens  += final.usage.input_tokens
            state.output_tokens += final.usage.output_tokens
        except Exception as e:
            full = f"[ERROR: {e}]"
            panel.stream(full)
        return full

    # ── デモモード ──────────────────────────────────────────────────────────── #

    _demo_turn = 0
    _DEMO_DIRECTOR = [
        (
            "了解しました！Coderにコード実装を、Researchに調査を依頼します。\n\n"
            "<<<DISPATCH>>>\n"
            "CODER: asyncio.gather を使った並列処理のPythonサンプルコードを実装してください\n"
            "RESEARCH: Pythonの並列処理手法（asyncio・threading・multiprocessing）の比較をまとめてください\n"
            "<<<END_DISPATCH>>>\n\n"
            "チームが並列で作業します。結果が揃い次第まとめます。"
        ),
        (
            "承知しました。最適化を実施します。\n\n"
            "<<<DISPATCH>>>\n"
            "CODER: 前のコードにキャッシュ機能とエラーハンドリングを追加してください\n"
            "RESEARCH: Proプランでのトークン節約ベストプラクティスを3つ挙げてください\n"
            "<<<END_DISPATCH>>>\n\n"
            "両方同時に処理します。"
        ),
    ]
    _DEMO_CODER = [
        "```python\nimport asyncio\n\nasync def worker(name: str, delay: float) -> str:\n    await asyncio.sleep(delay)\n    return f'{name} 完了 ({delay}秒)'\n\nasync def main() -> None:\n    # 並列実行\n    results = await asyncio.gather(\n        worker('Coder',    0.5),\n        worker('Research', 0.8),\n        worker('Analyst',  0.6),\n    )\n    for r in results: print(r)\n\nasyncio.run(main())\n```\n実装完了。3タスクを並列実行し、最長0.8秒で完了します。",
        "```python\nfrom functools import lru_cache\nimport asyncio\n\n@lru_cache(maxsize=128)\ndef expensive_compute(n: int) -> int:\n    return sum(range(n))\n\nasync def safe_worker(name: str) -> str:\n    try:\n        result = expensive_compute(10000)\n        return f'{name}: {result}'\n    except Exception as e:\n        return f'{name}: エラー - {e}'\n```\nキャッシュとエラーハンドリングを追加しました。",
    ]
    _DEMO_RESEARCH = [
        "Python並列処理比較:\n• asyncio: I/O待機に最適。軽量。同一スレッド。\n• threading: GILあり。CPU処理には不向き。I/Oには有効。\n• multiprocessing: CPU処理に最適。メモリ使用量大。\n→ API呼び出し等のI/O処理には asyncio が最適。",
        "Proプラントークン節約ベストプラクティス:\n1. cache_control で固定プロンプトをキャッシュ（最大90%削減）\n2. Haiku を Worker に使用（Sonnet比 1/3 のコスト）\n3. autoCompactEnabled でコンテキスト自動圧縮（最大80%削減）",
    ]

    async def _demo_director_response(self) -> str:
        responses = self._DEMO_DIRECTOR
        resp = responses[self._demo_turn % len(responses)]
        for char in resp:
            self._director.stream(char)
            await asyncio.sleep(0.01)
        return resp

    async def _demo_worker_response(self, name: str, task: str) -> str:
        if "CODER" in name.upper() or name.upper() == "WORKER":
            responses = self._DEMO_CODER
        else:
            responses = self._DEMO_RESEARCH
        resp = responses[self._demo_turn % len(responses)]
        panel = next(
            (p for p in self._worker_panels
             if p.state.config.name.upper() == name.upper()),
            self._worker_panels[0] if self._worker_panels else None
        )
        if panel:
            for char in resp:
                panel.stream(char)
                await asyncio.sleep(0.008)
            # フェイクトークン更新
            state = panel.state
            state.input_tokens  += len(task.split()) * 4 + 300
            state.output_tokens += len(resp.split()) * 4
        self._demo_turn += 1
        return resp


# ── make_presets (後方互換) ─────────────────────────────────────────────── #

def make_presets() -> dict[str, list]:
    """後方互換: 以前のプリセット形式を返す"""
    return {k: v for k, v in WORKER_PRESETS.items()}


# ── エントリポイント ──────────────────────────────────────────────────────── #

def main() -> None:
    ap = argparse.ArgumentParser(description="Claude チームエージェント — Director自動指揮")
    ap.add_argument("--preset", default="default",
                    choices=list(WORKER_PRESETS.keys()),
                    help="ワーカープリセット")
    ap.add_argument("--demo",   action="store_true",
                    help="デモモード（API キー不要）")
    args = ap.parse_args()

    if not args.demo and not os.environ.get("ANTHROPIC_API_KEY"):
        print()
        print("=" * 55)
        print("  ANTHROPIC_API_KEY が設定されていません。")
        print()
        print("  デモモード（今すぐ画面確認）:")
        print("    claude-team --demo")
        print()
        print("  本番モード:")
        print("    export ANTHROPIC_API_KEY=sk-ant-...")
        print("    claude-team")
        print("=" * 55)
        sys.exit(1)

    workers = WORKER_PRESETS[args.preset]
    mode    = "デモ" if args.demo else "本番"
    print(f"\n{mode}モード / {args.preset} プリセット")
    print(f"  Director: claude-sonnet-4-6")
    for w in workers:
        p = PRICING[w.model]
        print(f"  {w.name:12s}: {w.model.replace('claude-','')}  ${p['input']:.2f}/1M入力")
    print()
    print("  ※ 入力は常に Director へ → 自動でワーカーに並列配信")
    print()

    DirectorTeamApp(workers, demo=args.demo).run()


if __name__ == "__main__":
    main()
