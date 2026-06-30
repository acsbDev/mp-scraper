#!/usr/bin/env bash

set -e

cd "$(dirname "$0")"

echo "Running MercadoPublico scraper..."
pipenv run python main.py

echo "Scraper finished."