#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
mkdir -p instance
flask --app app init-db

printf '\nIMS server setup complete. Start it with:\n'
printf 'source .venv/bin/activate\n'
printf 'flask --app app run --host 0.0.0.0 --port 5000\n'