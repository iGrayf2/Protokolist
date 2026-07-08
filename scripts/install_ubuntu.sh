#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Installing system packages..."
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg git python3-tk

echo "Creating local working folders..."
mkdir -p input output logs models cache

if [ ! -d .venv ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

echo "Upgrading pip..."
.venv/bin/python -m pip install --upgrade pip

echo "Installing Python dependencies..."
.venv/bin/python -m pip install -r requirements.txt

echo "Making scripts executable..."
chmod +x scripts/*.sh

echo
echo "Install complete."
echo
echo "Recommended project location: ~/Protokolist"
echo "Put audio files into:        ./input"
echo "Results will be saved into: ./output"
echo
echo "Run GUI: ./scripts/run_gui_ubuntu.sh"
echo "Run CLI: ./scripts/transcribe_file_ubuntu.sh input/meeting.mp3"
