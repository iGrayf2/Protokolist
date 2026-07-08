#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Installing system packages..."
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg git python3-tk

if [ ! -d .venv ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

echo "Upgrading pip..."
.venv/bin/python -m pip install --upgrade pip

echo "Installing Python dependencies..."
.venv/bin/python -m pip install -r requirements.txt

echo
echo "Install complete."
echo "Run GUI: ./scripts/run_gui_ubuntu.sh"
echo "Run CLI: ./scripts/transcribe_file_ubuntu.sh /path/to/audio.mp3"
