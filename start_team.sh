#!/usr/bin/env bash
# Lynq Team Agent launcher
# Works from any directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ANTHROPIC_API_KEY is not set."
    echo "Run the following and try again:"
    echo "  export ANTHROPIC_API_KEY=sk-ant-..."
    exit 1
fi

PRESET="${1:-default}"
echo "Launching Lynq Team Agent: $PRESET preset"
echo "Press Ctrl+Q to quit"
echo ""

python "$SCRIPT_DIR/multi_agent_ui.py" --preset "$PRESET"
