#!/usr/bin/env bash

set -e

cd "$(dirname "$0")"

echo "Installing pipenv..."
python3 -m pip install --user pipenv

export PATH="$HOME/.local/bin:$PATH"

echo "Installing project dependencies..."
pipenv install

echo "Installation completed."