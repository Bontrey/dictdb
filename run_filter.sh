#!/bin/bash
# Script to run filter_jsonl.py inside the virtual environment
# Usage: ./run_filter.sh [all filter_jsonl.py arguments]
#
# This script automatically sets up the virtual environment if it doesn't exist.

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/venv"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found. Creating it..." >&2
    python3 -m venv "$VENV_DIR"

    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment" >&2
        exit 1
    fi

    echo "Installing dependencies..." >&2
    source "$VENV_DIR/bin/activate"

    if [ -f "$REQUIREMENTS_FILE" ]; then
        pip install -r "$REQUIREMENTS_FILE"
        if [ $? -ne 0 ]; then
            echo "Error: Failed to install dependencies" >&2
            exit 1
        fi
    else
        # Fallback if requirements.txt doesn't exist
        pip install pyliblzfse
        if [ $? -ne 0 ]; then
            echo "Error: Failed to install pyliblzfse" >&2
            exit 1
        fi
    fi

    echo "Virtual environment setup complete." >&2
else
    # Activate existing virtual environment
    source "$VENV_DIR/bin/activate"
fi

# Run filter_jsonl.py with all provided arguments
python3 "$SCRIPT_DIR/filter_jsonl.py" "$@"
