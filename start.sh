#!/usr/bin/env bash

echo "=== Installing Playwright browsers ==="
python -m playwright install chromium 2>&1
python -m playwright install chromium-headless-shell 2>&1 || echo "(chromium-headless-shell target not available — trying full install)"
python -m playwright install 2>&1 || true

echo "=== Verifying installation ==="
ls -la /opt/render/.cache/ms-playwright/ 2>&1 || echo "No playwright cache at /opt/render/.cache"
ls -la ~/.cache/ms-playwright/ 2>&1 || echo "No playwright cache at ~/.cache"

echo "=== Starting app ==="
python main.py
