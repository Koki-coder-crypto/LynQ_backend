# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Releases are automated via [python-semantic-release](https://python-semantic-release.readthedocs.io/)
based on [Conventional Commits](https://www.conventionalcommits.org/).

<!-- next-version-marker -->

## [0.1.0] — 2026-05-14

### Added
- Multi-agent split-screen TUI (`multi_agent_ui.py`) with Pro-plan optimization
- Director-led team agent with parallel worker dispatch (`token_optimizer/team.py`)
- Smart model routing (Haiku / Sonnet / Opus auto-selection)
- Prompt caching with TTL management
- Client-side context compression
- Batch API processor (50% cost reduction)
- Pre-flight token counting and cost estimation
- GitHub Actions: CI, automated release, weekly AI growth report
- AI Issue triage via Claude Haiku
