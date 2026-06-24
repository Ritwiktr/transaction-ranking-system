#!/usr/bin/env bash
# Push to GitHub and deploy via Render Blueprint.
# Prerequisites: GitHub repo created, Render billing active, gh or git remote configured.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -d .git ]; then
  echo "Initialize git in this folder first:"
  echo "  cd $ROOT && git init && git add -A && git commit -m 'Initial commit'"
  exit 1
fi

echo "1. Push to GitHub (create repo at https://github.com/new first):"
echo "   git remote add origin https://github.com/YOUR_USER/transaction-ranking-system.git"
echo "   git branch -M main && git push -u origin main"
echo ""
echo "2. Deploy on Render:"
echo "   - Open https://dashboard.render.com/blueprints"
echo "   - New Blueprint Instance -> connect repo -> select render.yaml"
echo "   - Set CORS_ORIGINS to your static site URL"
echo "   - Set API_BASE_URL on the static site to your API URL"
echo ""
echo "Single-service option: deploy only txn-ranking-api; it serves the frontend at /"
