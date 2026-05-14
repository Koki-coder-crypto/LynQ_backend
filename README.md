# Lynq Backend

Claude API token optimization toolkit and multi-agent UI — powering the [Lynq](https://github.com/Koki-coder-crypto/LynQ_iOS) QR code app.

## Features

| Module | What it does | Savings |
|---|---|---|
| **Smart Routing** | Auto-selects Haiku / Sonnet / Opus based on task complexity | Up to 67% cost reduction |
| **Prompt Caching** | Caches stable system prompts with TTL | Up to 90% on repeated calls |
| **Context Compression** | Summarizes long histories via Haiku | Prevents context overflow |
| **Batch API** | Groups non-urgent calls | 50% flat discount |
| **Multi-Agent UI** | Split-screen TUI with Director + Workers | Pro-plan optimized |

## Quick start

```bash
pip install lynq-backend
export ANTHROPIC_API_KEY=sk-ant-...

# Multi-agent split-screen UI
claude-team

# Demo (no API key needed)
claude-team --demo

# Dev team preset
claude-team --preset dev
```

## Presets

| Preset | Agents | Use case |
|---|---|---|
| `default` | Director (Sonnet) + Coder + Research (Haiku) | General — Pro-plan optimized |
| `dev` | Architect + Coder + Reviewer | Software development |
| `research` | Finder + Analyst + Writer | Research and analysis |
| `minimal` | 2 agents | Long sessions, ultra-save |

## Release

Releases are fully automated via [python-semantic-release](https://python-semantic-release.readthedocs.io/).
Use [Conventional Commits](https://www.conventionalcommits.org/) and merging to `master` triggers an automatic version bump, changelog update, PyPI publish, and GitHub Release.

| Commit prefix | Version bump |
|---|---|
| `feat:` | Minor (0.x.0) |
| `fix:` / `perf:` | Patch (0.0.x) |
| `BREAKING CHANGE` | Major (x.0.0) |

## License

MIT
