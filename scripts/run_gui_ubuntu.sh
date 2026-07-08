#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -x .venv/bin/python ]; then
  echo "Virtual environment not found. Run ./scripts/install_ubuntu.sh first."
  exit 1
fi

PYTHONPATH=src .venv/bin/python run.py
