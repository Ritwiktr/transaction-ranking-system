#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

if [ ! -d .venv ]; then
  python3.13 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt -q

export DATABASE_URL="${DATABASE_URL:-sqlite:///./local.db}"
export CORS_ORIGINS="${CORS_ORIGINS:-*}"

echo "Starting API + frontend at http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
