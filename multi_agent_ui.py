#!/usr/bin/env python3
"""
multi_agent_ui.py — Pro-plan Multi-Agent Split-Screen UI

  ┌─────────────────────────┬──────────────────────────┬──────────────────────────┐
  │ ■ Director [sonnet]     │ ■ Coder [haiku]           │ ■ Research [haiku]        │
  │  You: Plan this         │  Claude: Code done        │  Claude: Research…        │
  │  Claude: Directing each  │                           │                           │
  │  agent…                  │  ─────────────────────   │  ─────────────────────   │
  │  ─────────────────────  │  ctx ████████░░░░ 65%     │  ctx ████░░░░░░░░ 33%     │
  │  ctx ████████░░░░ 78%   │  budget ██░░░░░░░░░░  8K  │  budget █░░░░░░░░░░  5K   │
  │  $0.0041                │  $0.0002                  │  $0.0001                  │
  ├─────────────────────────┴──────────────────────────┴──────────────────────────┤
  │ [Enter message]  [→ Director] [→ Coder] [→ Research] [→ All]                  │
  │ Total: 156K tokens | $0.0044 | Elapsed: 4m 12s | Saved: -68% vs Opus          │
  └────────────────────────────────────────────────────────────────────────────────┘

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python multi_agent_ui.py              # default 3 agents (Pro-optimized)
    python multi_agent_ui.py --preset dev # dev team
    python multi_agent_ui.py --preset research  # research team
    python multi_agent_ui.py --preset minimal   # 2 agents (ultra-save)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass, field

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

# Recommended token budget per agent on Pro plan
PRO_BUDGET_PER_AGENT = 25_000   # trigger auto-compress when exceeded
AUTO_COMPRESS_AT     = 0.80     # auto-compress fires at 80% of budget


# ── Data classes ──────────────────────────────────────────────────────────── #

@dataclass
class AgentConfig:
    name:   str
    model:  str
    system: str
    color:  str  = "cyan"
    budget: int  = PRO_BUDGET_PER_AGENT   # token budget for this agent
    max_tokens: int = 1024                 # max tokens per response


@dataclass
class AgentState:
    config: AgentConfig
    history:        list[dict] = field(default_factory=list)
    input_tokens:   int = 0
    output_tokens:  int = 0
    session_tokens: int = 0   # budget counter (reset on compress)
    is_busy:        bool = False
    compressions:   int  = 0

    @property
    def context_pct(self) -> float:
        window = CONTEXT_WINDOWS.get(self.config.model, 200_000)
        return min(1.0, self.input_tokens / window)

    @property
    def budget_pct(self) -> float:
        return min(1.0, self.session_tokens / self.config.budget)

    @property
    def cost_usd(self) -> float:
        p = PRICING.get(self.config.model, PRICING["claude-sonnet-4-6"])
        return (self.input_tokens * p["input"] + self.output_tokens * p["output"]) / 1_000_000

    @property
    def needs_compress(self) -> bool:
        return self.budget_pct >= AUTO_COMPRESS_AT

    @property
    def bar_color_ctx(self) -> str:
        pct = self.context_pct * 100
        return "green" if pct < 50 else ("yellow" if pct < 80 else "red")

    @property
    def bar_color_budget(self) -> str:
        pct = self.budget_pct * 100
        return "green" if pct < 60 else ("yellow" if pct < 80 else "red")

    @property
    def context_bar_label(self) -> str:
        window = CONTEXT_WINDOWS.get(self.config.model, 200_000)
        pct = self.context_pct * 100
        return (
            f"[{self.bar_color_ctx}]ctx {pct:5.1f}%[/]  "
            f"{self.input_tokens/1000:.1f}K/{window//1000}K  "
            f"[dim]${self.cost_usd:.4f}[/]"
        )

    @property
    def budget_bar_label(self) -> str:
        used = self.session_tokens
        bgt  = self.config.budget
        pct  = self.budget_pct * 100
        compress_note = f" [dim](×{self.compressions} compressed)[/]" if self.compressions else ""
        return (
            f"[{self.bar_color_budget}]budget {pct:5.1f}%[/]  "
            f"{used/1000:.1f}K/{bgt//1000}K{compress_note}"
        )


# ── Presets ────────────────────────────────────────────────────────────────── #

def make_presets() -> dict[str, list[AgentConfig]]:
    return {
        # Pro plan recommended: 1 director (sonnet) + 2 workers (haiku)
        "default": [
            AgentConfig(
                name="Director", model="claude-sonnet-4-6", color="cyan",
                budget=30_000, max_tokens=2048,
                system=(
                    "You are the team leader. Analyze the user's instructions and give "
                    "specific directions to Coder and Research. Also provide your own response. Be concise."
                ),
            ),
            AgentConfig(
                name="Coder", model="claude-haiku-4-5", color="green",
                budget=20_000, max_tokens=1024,
                system=(
                    "You are a Python expert. "
                    "Write code concisely with type hints. Keep explanations minimal."
                ),
            ),
            AgentConfig(
                name="Research", model="claude-haiku-4-5", color="yellow",
                budget=20_000, max_tokens=1024,
                system=(
                    "You are a research and summarization specialist. "
                    "Present facts in bullet points concisely. Avoid verbose explanations."
                ),
            ),
        ],
        # Dev team: 3 agents for design, implementation, and review
        "dev": [
            AgentConfig(
                name="Architect", model="claude-sonnet-4-6", color="cyan",
                budget=35_000, max_tokens=2048,
                system="You are a system design specialist. Present design principles and architecture concisely.",
            ),
            AgentConfig(
                name="Coder", model="claude-haiku-4-5", color="green",
                budget=20_000, max_tokens=1024,
                system="You are a Python expert. Write code only.",
            ),
            AgentConfig(
                name="Reviewer", model="claude-haiku-4-5", color="magenta",
                budget=15_000, max_tokens=512,
                system="You are a code reviewer. Point out only issues in bullet points.",
            ),
        ],
        # Research team: 3 agents for finding, analysis, and writing
        "research": [
            AgentConfig(
                name="Finder", model="claude-haiku-4-5", color="yellow",
                budget=20_000, max_tokens=1024,
                system="You are an information gathering specialist. Present facts and evidence in bullet points.",
            ),
            AgentConfig(
                name="Analyst", model="claude-sonnet-4-6", color="cyan",
                budget=30_000, max_tokens=2048,
                system="You are a data analyst. Analyze patterns and insights.",
            ),
            AgentConfig(
                name="Writer", model="claude-haiku-4-5", color="green",
                budget=15_000, max_tokens=1024,
                system="You are a writer. Summarize conclusions in concise prose.",
            ),
        ],
        # Ultra-save: 2 agents (for long sessions on Pro plan)
        "minimal": [
            AgentConfig(
                name="Assistant", model="claude-haiku-4-5", color="cyan",
                budget=30_000, max_tokens=1024,
                system="You are a general-purpose assistant. Answer concisely.",
            ),
            AgentConfig(
                name="Expert", model="claude-sonnet-4-6", color="green",
                budget=25_000, max_tokens=2048,
                system="You are an expert assistant. Answer detailed questions.",
            ),
        ],
    }


# ── Widgets ──────────────────────────────────────────────────────────────── #

class StreamingBuffer(Static):
    def __init__(self, **kw) -> None:
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


class AgentPanel(Vertical):
    DEFAULT_CSS = """
    AgentPanel {
        border: solid $panel-lighten-2;
        width: 1fr;
        height: 1fr;
        padding: 0 1;
    }
    AgentPanel.active { border: double $success; }
    AgentPanel #title { height: 1; text-style: bold; background: $panel-lighten-1; padding: 0 1; }
    AgentPanel #log { height: 1fr; background: $surface; }
    AgentPanel #stream { height: auto; min-height: 1; max-height: 6; background: $surface; color: $text-muted; padding: 0 1; }
    AgentPanel #ctx-bar { height: 1; margin: 0; }
    AgentPanel #ctx-label { height: 1; padding: 0 1; }
    AgentPanel #bgt-bar { height: 1; margin: 0; }
    AgentPanel #bgt-label { height: 1; padding: 0 1; }
    """

    def __init__(self, state: AgentState, idx: int, **kw) -> None:
        super().__init__(**kw)
        self.state = state
        self.idx   = idx
        self.id    = f"panel-{idx}"

    def compose(self) -> ComposeResult:
        cfg = self.state.config
        model_short = cfg.model.replace("claude-", "")
        yield Label(
            f"[bold {cfg.color}]■ {cfg.name}[/]  [dim]{model_short}  budget {cfg.budget//1000}K[/]",
            id="title",
        )
        yield RichLog(id="log", highlight=True, markup=True, wrap=True)
        yield StreamingBuffer(id="stream")
        yield ProgressBar(total=100, show_eta=False, id="ctx-bar")
        yield Label("", id="ctx-label",  markup=True)
        yield ProgressBar(total=100, show_eta=False, id="bgt-bar")
        yield Label("", id="bgt-label", markup=True)

    # ── Message operations ──────────────────────────────────────────── #

    def add_user(self, text: str) -> None:
        self.query_one("#log", RichLog).write(f"[bold cyan]You:[/] {text}")

    def start_reply(self) -> None:
        self.query_one("#stream", StreamingBuffer).reset("[bold green]Claude:[/] ")

    def stream_chunk(self, chunk: str) -> None:
        self.query_one("#stream", StreamingBuffer).append(chunk)

    def finish_reply(self) -> None:
        buf = self.query_one("#stream", StreamingBuffer)
        self.query_one("#log",    RichLog).write(buf.text)
        buf.reset()

    def set_status(self, msg: str) -> None:
        self.query_one("#stream", StreamingBuffer).reset(msg)

    def refresh_stats(self) -> None:
        s = self.state
        ctx_bar = self.query_one("#ctx-bar", ProgressBar)
        bgt_bar = self.query_one("#bgt-bar", ProgressBar)
        ctx_bar.progress = s.context_pct * 100
        bgt_bar.progress = s.budget_pct * 100
        self.query_one("#ctx-label",  Label).update(s.context_bar_label)
        self.query_one("#bgt-label", Label).update(s.budget_bar_label)

    def mark_active(self, active: bool) -> None:
        if active:
            self.add_class("active")
        else:
            self.remove_class("active")


class GlobalStatsBar(Static):
    DEFAULT_CSS = """
    GlobalStatsBar {
        height: 1;
        background: $primary-darken-2;
        color: $text;
        text-align: center;
        padding: 0 1;
    }
    """

    def refresh_stats(self, states: list[AgentState], start: float) -> None:
        elapsed = time.time() - start
        mins, secs = divmod(int(elapsed), 60)

        total_cost   = sum(s.cost_usd for s in states)
        total_tokens = sum(s.input_tokens + s.output_tokens for s in states)

        # Estimate savings based on haiku usage (baseline: all sonnet)
        sonnet_cost = sum(
            (s.input_tokens * 3.0 + s.output_tokens * 15.0) / 1_000_000
            for s in states
        )
        saving_pct = max(0, (1 - total_cost / sonnet_cost) * 100) if sonnet_cost > 1e-9 else 0

        parts = [
            f"Total: [bold]{total_tokens:,}[/] tokens",
            f"Cost: [bold]${total_cost:.4f}[/]",
            f"Elapsed: {mins}m {secs:02d}s",
        ]
        if saving_pct > 1:
            parts.append(f"[green]↓{saving_pct:.0f}% saved[/] (model optimization)")

        self.update("  |  ".join(parts))


# ── Main app ──────────────────────────────────────────────────────────────── #

class TeamAgentApp(App[None]):
    """Pro-plan multi-agent split-screen UI"""

    TITLE     = "Claude Team Agents"
    SUB_TITLE = "Tab=Next Agent  F1-F4=Select  Ctrl+A=Send to All  Ctrl+Q=Quit"

    CSS = """
    Screen { layout: vertical; }
    #panels { height: 1fr; layout: horizontal; }
    #input-row { height: 3; layout: horizontal; padding: 0 1; align: left middle; }
    #user-input { width: 1fr; margin: 0 1 0 0; }
    .send-btn { width: auto; margin: 0 1 0 0; min-width: 10; }
    #btn-all { variant: warning; }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit",          "Quit"),
        Binding("tab",    "cycle_agent",   "Next",  show=False),
        Binding("ctrl+a", "send_all",      "All"),
        Binding("f1",     "select_0",      "Agent1"),
        Binding("f2",     "select_1",      "Agent2"),
        Binding("f3",     "select_2",      "Agent3"),
        Binding("f4",     "select_3",      "Agent4"),
    ]

    def __init__(self, agents: list[AgentConfig]) -> None:
        super().__init__()
        self._states  = [AgentState(config=c) for c in agents]
        self._panels: list[AgentPanel] = []
        self._active  = 0
        self._start   = time.time()
        self._client  = AsyncAnthropic()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="panels"):
            for i, state in enumerate(self._states):
                p = AgentPanel(state, i)
                self._panels.append(p)
                yield p
        with Horizontal(id="input-row"):
            yield Input(
                placeholder="Type a message… (Tab/F1-F4 to select agent, Ctrl+A to send to all)",
                id="user-input",
            )
            for i, s in enumerate(self._states):
                yield Button(f"→{s.config.name}", id=f"btn-{i}", classes="send-btn",
                             variant="primary" if i == 0 else "default")
            yield Button("→All", id="btn-all", classes="send-btn")
        yield GlobalStatsBar("Starting…", id="global-stats")
        yield Footer()

    def on_mount(self) -> None:
        self._sync_active()
        self.set_interval(3, self._tick)
        self.query_one("#user-input", Input).focus()
        for p in self._panels:
            p.set_status(
                f"[dim]Ready. Budget: {p.state.config.budget//1000}K tokens. "
                f"Auto-compress at 80%.[/]"
            )

    # ── Events ────────────────────────────────────────────────── #

    def on_input_submitted(self, event: Input.Submitted) -> None:
        msg = event.value.strip()
        if not msg:
            return
        event.input.value = ""
        self._dispatch(self._active, msg)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        inp = self.query_one("#user-input", Input)
        msg = inp.value.strip()

        if bid == "btn-all":
            if msg:
                inp.value = ""
                for i in range(len(self._states)):
                    self._dispatch(i, msg)
            return

        if bid.startswith("btn-"):
            idx = int(bid.split("-")[1])
            if msg:
                inp.value = ""
                self._active = idx
                self._sync_active()
                self._dispatch(idx, msg)
            else:
                self._active = idx
                self._sync_active()

    # ── Actions ──────────────────────────────────────────────── #

    def action_cycle_agent(self) -> None:
        self._active = (self._active + 1) % len(self._states)
        self._sync_active()

    def action_send_all(self) -> None:
        inp = self.query_one("#user-input", Input)
        msg = inp.value.strip()
        if msg:
            inp.value = ""
            for i in range(len(self._states)):
                self._dispatch(i, msg)

    def action_select_0(self) -> None: self._select(0)
    def action_select_1(self) -> None: self._select(1)
    def action_select_2(self) -> None: self._select(2)
    def action_select_3(self) -> None: self._select(3)

    def _select(self, idx: int) -> None:
        if 0 <= idx < len(self._states):
            self._active = idx
            self._sync_active()

    # ── Internal helpers ─────────────────────────────────────────── #

    def _sync_active(self) -> None:
        for i, panel in enumerate(self._panels):
            panel.mark_active(i == self._active)
        for i in range(len(self._states)):
            try:
                btn = self.query_one(f"#btn-{i}", Button)
                btn.variant = "primary" if i == self._active else "default"
            except Exception:
                pass

    def _dispatch(self, idx: int, msg: str) -> None:
        if self._states[idx].is_busy:
            self._panels[idx].set_status("[yellow]⏳ Processing… please wait[/]")
            return
        self._send(idx, msg)

    def _tick(self) -> None:
        self.query_one("#global-stats", GlobalStatsBar).refresh_stats(
            self._states, self._start
        )

    # ── Async workers ────────────────────────────────────────────── #

    @work(exclusive=False)
    async def _send(self, idx: int, message: str) -> None:
        state  = self._states[idx]
        panel  = self._panels[idx]

        # Budget check → auto-compress if needed
        if state.needs_compress:
            await self._auto_compress(idx)

        state.is_busy = True
        state.history.append({"role": "user", "content": message})
        panel.add_user(message)
        panel.start_reply()

        full_text = ""
        try:
            async with self._client.messages.stream(
                model=state.config.model,
                max_tokens=state.config.max_tokens,
                system=state.config.system,
                messages=state.history,
            ) as stream:
                async for chunk in stream.text_stream:
                    full_text += chunk
                    panel.stream_chunk(chunk)
                final = await stream.get_final_message()

            state.history.append({"role": "assistant", "content": full_text})
            inp = final.usage.input_tokens
            out = final.usage.output_tokens
            state.input_tokens   += inp
            state.output_tokens  += out
            state.session_tokens += inp + out

        except Exception as exc:
            panel.stream_chunk(f"\n[bold red][ERROR: {exc}][/]")

        panel.finish_reply()
        panel.refresh_stats()
        state.is_busy = False
        self._tick()

    async def _auto_compress(self, idx: int) -> None:
        """Summarize conversation history with Haiku and reset (budget saving)"""
        state = self._states[idx]
        panel = self._panels[idx]
        panel.set_status("[yellow]⚡ Auto-compressing… (saving budget)[/]")

        transcript = "\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in state.history
            if isinstance(m.get("content"), str)
        )
        try:
            resp = await self._client.messages.create(
                model="claude-haiku-4-5",   # always use cheapest model for compression
                max_tokens=512,
                messages=[{
                    "role": "user",
                    "content": (
                        "Please summarize the following conversation in 100 words or less. "
                        "Retain only important decisions, facts, and code.\n\n" + transcript
                    ),
                }],
            )
            summary = next(
                (b.text for b in resp.content if b.type == "text"), "(no summary)"
            )
        except Exception:
            summary = "(compression error)"

        # Replace history with summary
        state.history = [
            {"role": "user",      "content": f"[Conversation Summary]\n{summary}"},
            {"role": "assistant", "content": "Understood. Let's continue."},
        ]
        state.session_tokens = 0
        state.compressions  += 1
        panel.query_one("#log", RichLog).write(
            f"[dim]⚡ Auto-compress complete (×{state.compressions}) — budget reset[/]"
        )


# ── Entry point ──────────────────────────────────────────────────────────── #

def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY is not set.")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    ap = argparse.ArgumentParser(description="Claude multi-agent split-screen UI")
    ap.add_argument(
        "--preset", default="default",
        choices=["default", "dev", "research", "minimal"],
        help="Team preset (default=Pro-optimized, dev=development, research=research, minimal=ultra-save)",
    )
    args = ap.parse_args()

    presets = make_presets()
    agents  = presets[args.preset]

    print(f"\nPreset: {args.preset}")
    for a in agents:
        model_short = a.model.replace("claude-", "")
        p = PRICING[a.model]
        print(f"  {a.name:12s} {model_short:20s}  budget {a.budget//1000}K  ${p['input']:.2f}/M input")
    print()

    TeamAgentApp(agents).run()


if __name__ == "__main__":
    main()
