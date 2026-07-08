#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ $# -lt 1 ]; then
  echo "Usage: ./scripts/transcribe_file_ubuntu.sh input/meeting.mp3 [options]"
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  echo "Virtual environment not found. Run ./scripts/install_ubuntu.sh first."
  exit 1
fi

# Рабочий режим по умолчанию: medium на CPU.
# Для ускорения можно явно передать: --model small
# Для максимального качества можно явно передать: --model large-v3
has_model=0
for arg in "$@"; do
  if [ "$arg" = "--model" ] || [[ "$arg" == --model=* ]]; then
    has_model=1
    break
  fi
done

if [ "$has_model" -eq 1 ]; then
  PYTHONPATH=src .venv/bin/python -m protokolist.cli "$@"
else
  PYTHONPATH=src .venv/bin/python -m protokolist.cli "$@" --model medium
fi
