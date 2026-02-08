#!/bin/bash
# format-and-type-check.sh - Pythonファイル編集後に自動でruff formatとty checkを実行

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# ファイルが空または存在しない場合はスキップ
if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

# Pythonファイルのみを処理
if [[ "$FILE_PATH" != *.py ]]; then
  exit 0
fi

# プロジェクトディレクトリに移動
cd "$CLAUDE_PROJECT_DIR" || exit 0

# ruff format実行
uv tool run ruff format "$FILE_PATH" 2>/dev/null

# ty check実行
uv run ty check 2>/dev/null

exit 0
