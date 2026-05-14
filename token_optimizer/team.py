#!/usr/bin/env python3
"""
team.py — Director-led team agent with parallel processing UI

How it works:
  1. User input → sent to Director (sonnet)
  2. Director analyzes the task and issues instructions via <<<DISPATCH>>> format
  3. App detects Dispatch → runs Coder & Research in parallel via asyncio.gather
  4. Results returned to Director → Director synthesizes the final answer

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    claude-team                  # production mode
    claude-team --demo           # demo (no API key required)
    claude-team --preset dev     # dev team preset
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

# ── Constants ─────────────────────────────────────────────────────────────── #

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

DIRECTOR_SYSTEM = """\
You are the Director of an AI team.
You receive the user's request and coordinate the team.

Team members:
- CODER   : Python implementation, code generation, technical tasks
- RESEARCH: Information gathering, best practices, analysis, comparison

Rules:
1. For tasks that can be parallelized across agents, use this format:
   <<<DISPATCH>>>
   CODER: [specific instruction for Coder — 1-2 sentences]
   RESEARCH: [specific instruction for Research — 1-2 sentences]
   <<<END_DISPATCH>>>

2. After the DISPATCH block, briefly describe your plan or overview.

3. When you receive the team's results, integrate them into a final answer.

4. For simple questions, answer directly yourself (no DISPATCH needed).

Always respond in English.
"""


# ── Data classes ──────────────────────────────────────────────────────────── #

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


# ── Presets ────────────────────────────────────────────────────────────────── #

WORKER_PRESETS: dict[str, list[WorkerConfig]] = {
    "default": [
        WorkerConfig("Coder",    "claude-haiku-4-5", color="green",
                     system="You are a Python expert. Write concise code with type hints. Keep explanations minimal."),
        WorkerConfig("Research", "claude-haiku-4-5", color="yellow",
                     system="You are a research specialist. Summarize facts and key points in bullet points concisely."),
    ],
    "dev": [
        WorkerConfig("Coder",    "claude-haiku-4-5", color="green",
                     system="You are a senior Python engineer. Write production-quality code."),
        WorkerConfig("Reviewer", "claude-haiku-4-5", color="magenta",
                     system="You are a code reviewer. Point out issues and improvements in bullet points."),
    ],
    "research": [
        WorkerConfig("Finder",   "claude-haiku-4-5", color="yellow",
                     system="You are an information gathering specialist. List relevant facts and figures."),
        WorkerConfig("Analyst",  "claude-haiku-4-5", color="cyan",
                     system="You are an analyst. Analyze data to derive patterns and insights."),
    ],
    "minimal": [
        WorkerConfig("Worker",   "claude-haiku-4-5", color="green",
                     system="You are a general-purpose assistant. Answer concisely."),
    ],
}


# ── Utilities ─────────────────────────────────────────────────────────────── #

def parse_dispatch(text: str) -> dict[str, str]:
    """Extract agent instructions from a <<<DISPATCH>>> block."""
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


# ── Widgets ──────────────────────────────────────────────────────────────── #

class StreamBuf(Static):
    """Streaming text buffer widget."""
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
    """Left pane: conversation with Director."""
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
        yield Label(f"[bold green]■ Director[/]  [dim]{m}[/]  [dim]← type here[/]", id="d-title")
        yield RichLog(id="d-log", highlight=True, markup=True, wrap=True)
        yield StreamBuf(id="d-stream")
        yield ProgressBar(total=100, show_eta=False, id="d-ctx-bar")
        yield Label("[dim]Idle[/]", id="d-stat", markup=True)

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
    """Right pane: worker agent."""
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
        yield Label("[dim]Idle[/]", id="w-stat", markup=True)

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
            f"Total: [bold]{all_inp+all_out:,}[/] tokens  |  "
            f"Cost: [bold]${all_cost:.4f}[/]  |  "
            f"Elapsed: {mins}m {secs:02d}s  |  "
            f"[green]Director → Workers auto-parallel[/]"
        )


# ── Main app ──────────────────────────────────────────────────────────────── #

class DirectorTeamApp(App[None]):
    """Director-led team agent UI."""

    TITLE     = "Lynq Team — Director Auto-Dispatch"
    SUB_TITLE = "Type → sent to Director → team processes in parallel  |  Ctrl+Q=Quit"

    CSS = """
    Screen { layout: vertical; }
    #main-area { height: 1fr; layout: horizontal; }
    #worker-area { width: 55%; layout: horizontal; }
    #input-row { height: 3; layout: horizontal; padding: 0 1; align: left middle; }
    #user-input { width: 1fr; margin: 0 1 0 0; }
    #send-btn { width: 20; }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("escape", "quit", "Quit", show=False),
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
                placeholder="Give Director an instruction… Director will auto-dispatch to the team",
                id="user-input",
            )
            yield Button("→ Send to Director", id="send-btn", variant="primary")
        yield GlobalBar("Starting…", id="global-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(3, self._tick)
        self.query_one("#user-input", Input).focus()
        mode = "[yellow]Demo mode[/]" if self._demo else "[green]Production mode[/]"
        self._director.set_status(f"[dim]{mode} — Ready. Give me an instruction.[/]")
        for p in self._worker_panels:
            p.set_status("[dim]Waiting for Director's dispatch…[/]")

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

    # ── Parallel orchestration ───────────────────────────────────────────── #

    @work(exclusive=False)
    async def _run_orchestration(self, message: str) -> None:
        """Director → parse dispatch → workers parallel → Director synthesize"""
        dir_panel = self._director

        # ① Send to Director
        dir_panel.add_user(message)
        self._director_history.append({"role": "user", "content": message})
        dir_panel.start_reply()

        director_response = await self._call_director()

        dir_panel.finish_reply()

        # ② Detect Dispatch block
        tasks = parse_dispatch(director_response)

        if not tasks:
            # No dispatch → Director answered directly
            return

        # ③ Run workers in parallel
        dir_panel.set_status("[yellow]⚡ Dispatching to team… starting parallel processing[/]")
        for p in self._worker_panels:
            p.set_status("[yellow]⟳ Processing…[/]")

        worker_results = await self._run_workers_parallel(tasks)

        # ④ Return results to Director for synthesis
        results_text = "\n\n".join(
            f"[{name} result]\n{result}"
            for name, result in worker_results.items()
        )
        feedback = (
            f"The team has finished. Here are each agent's results:\n\n{results_text}\n\n"
            "Please integrate these into a final answer."
        )

        self._director_history.append({"role": "assistant", "content": director_response})
        self._director_history.append({"role": "user",      "content": feedback})

        dir_panel.start_reply("[bold green]Director (synthesis):[/] ")
        await self._call_director()
        dir_panel.finish_reply()
        self._tick()

    async def _call_director(self) -> str:
        """Call Director API with streaming display."""
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
        """Run all assigned tasks across workers in parallel."""
        panel_map: dict[str, tuple[WorkerPanel, WorkerState]] = {}
        for panel, state in zip(self._worker_panels, self._worker_states):
            panel_map[state.config.name.upper()] = (panel, state)

        async def run_one(agent_name: str, task: str) -> tuple[str, str]:
            key = agent_name.upper()
            if key not in panel_map:
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

        coros = [run_one(name, task) for name, task in tasks.items()]
        results_list = await asyncio.gather(*coros)
        return dict(results_list)

    async def _stream_worker(self, panel: WorkerPanel, state: WorkerState, task: str) -> str:
        """Worker API call with streaming."""
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

    # ── Demo mode ──────────────────────────────────────────────────────────── #

    _demo_turn = 0
    _DEMO_DIRECTOR = [
        (
            "Got it! I'll ask Coder to implement the code and Research to investigate.\n\n"
            "<<<DISPATCH>>>\n"
            "CODER: Implement a Python sample using asyncio.gather for parallel processing\n"
            "RESEARCH: Summarize a comparison of Python parallelism methods (asyncio, threading, multiprocessing)\n"
            "<<<END_DISPATCH>>>\n\n"
            "The team will work in parallel. I'll synthesize the results once they're ready."
        ),
        (
            "Understood. Let's optimize.\n\n"
            "<<<DISPATCH>>>\n"
            "CODER: Add caching and error handling to the previous code\n"
            "RESEARCH: List 3 token-saving best practices for Pro plan usage\n"
            "<<<END_DISPATCH>>>\n\n"
            "Processing both simultaneously."
        ),
    ]
    _DEMO_CODER = [
        "```python\nimport asyncio\n\nasync def worker(name: str, delay: float) -> str:\n    await asyncio.sleep(delay)\n    return f'{name} done ({delay}s)'\n\nasync def main() -> None:\n    results = await asyncio.gather(\n        worker('Coder',    0.5),\n        worker('Research', 0.8),\n        worker('Analyst',  0.6),\n    )\n    for r in results: print(r)\n\nasyncio.run(main())\n```\nImplemented. 3 tasks run in parallel, completing in 0.8s max.",
        "```python\nfrom functools import lru_cache\nimport asyncio\n\n@lru_cache(maxsize=128)\ndef expensive_compute(n: int) -> int:\n    return sum(range(n))\n\nasync def safe_worker(name: str) -> str:\n    try:\n        result = expensive_compute(10000)\n        return f'{name}: {result}'\n    except Exception as e:\n        return f'{name}: error - {e}'\n```\nAdded caching and error handling.",
    ]
    _DEMO_RESEARCH = [
        "Python parallelism comparison:\n• asyncio: Best for I/O-bound tasks. Lightweight. Single-threaded.\n• threading: Has GIL. Poor for CPU tasks. Good for I/O.\n• multiprocessing: Best for CPU tasks. Higher memory usage.\n→ asyncio is optimal for API calls and other I/O.",
        "Pro plan token-saving best practices:\n1. Use cache_control for stable prompts (up to 90% reduction)\n2. Use Haiku for workers (1/3 cost of Sonnet)\n3. Enable autoCompact for context compression (up to 80% reduction)",
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
            state = panel.state
            state.input_tokens  += len(task.split()) * 4 + 300
            state.output_tokens += len(resp.split()) * 4
        self._demo_turn += 1
        return resp


# ── Backwards compatibility ─────────────────────────────────────────────── #

def make_presets() -> dict[str, list]:
    return {k: v for k, v in WORKER_PRESETS.items()}


# ── Entry point ──────────────────────────────────────────────────────────── #

def main() -> None:
    ap = argparse.ArgumentParser(description="Lynq Team Agent — Director auto-dispatch")
    ap.add_argument("--preset", default="default",
                    choices=list(WORKER_PRESETS.keys()),
                    help="Worker preset")
    ap.add_argument("--demo",   action="store_true",
                    help="Demo mode (no API key required)")
    args = ap.parse_args()

    if not args.demo and not os.environ.get("ANTHROPIC_API_KEY"):
        print()
        print("=" * 55)
        print("  ANTHROPIC_API_KEY is not set.")
        print()
        print("  Demo mode (preview the UI now):")
        print("    claude-team --demo")
        print()
        print("  Production mode:")
        print("    export ANTHROPIC_API_KEY=sk-ant-...")
        print("    claude-team")
        print("=" * 55)
        sys.exit(1)

    workers = WORKER_PRESETS[args.preset]
    mode    = "Demo" if args.demo else "Production"
    print(f"\n{mode} mode / {args.preset} preset")
    print(f"  Director: claude-sonnet-4-6")
    for w in workers:
        p = PRICING[w.model]
        print(f"  {w.name:12s}: {w.model.replace('claude-','')}  ${p['input']:.2f}/1M input")
    print()
    print("  * Input always goes to Director → auto-dispatched to workers in parallel")
    print()

    DirectorTeamApp(workers, demo=args.demo).run()


if __name__ == "__main__":
    main()
