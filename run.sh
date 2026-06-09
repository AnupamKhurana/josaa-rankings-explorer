#!/bin/bash
# Script to run the JoSAA & JAC Delhi Rankings Explorer App

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

echo "Starting JoSAA & JAC Delhi Rankings Explorer server..."
if [ -d "venv" ]; then
    echo "Using virtual environment (venv)..."
    ./venv/bin/python main.py
elif command -v python3 &>/dev/null; then
    python3 main.py
elif command -v python &>/dev/null; then
    python main.py
else
    echo "Error: Python is not installed or not in PATH." >&2
    exit 1
fi
