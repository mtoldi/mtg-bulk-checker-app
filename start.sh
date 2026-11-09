#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    echo "First run: setting things up, this takes a minute or two..."
    if ! command -v python3 >/dev/null 2>&1; then
        echo "Python was not found. Install it from https://www.python.org/downloads/"
        exit 1
    fi
    python3 -m venv .venv
fi

# Dependencies are only installed when requirements.txt changes.
if ! cmp -s requirements.txt .venv/installed-requirements.txt; then
    echo "Installing dependencies..."
    .venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt
    cp requirements.txt .venv/installed-requirements.txt
fi

echo "Bulk Checker is opening in your browser. Press Ctrl+C to stop it."
exec .venv/bin/python -m streamlit run app.py
