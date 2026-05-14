#!/usr/bin/env bash
# Claude チームエージェント起動スクリプト
# どのフォルダからでも動作する

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ANTHROPIC_API_KEY が設定されていません。"
    echo "以下を実行してから再試行してください:"
    echo "  export ANTHROPIC_API_KEY=sk-ant-..."
    exit 1
fi

PRESET="${1:-default}"
echo "Claude チームエージェント起動: $PRESET プリセット"
echo "Ctrl+Q で終了"
echo ""

python "$SCRIPT_DIR/multi_agent_ui.py" --preset "$PRESET"
