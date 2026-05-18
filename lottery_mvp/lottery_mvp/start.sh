#!/usr/bin/env sh
set -eu

python updater.py --seed-demo >/dev/null 2>&1 || true
exec streamlit run app.py --server.port="${PORT:-8501}" --server.address="0.0.0.0"
