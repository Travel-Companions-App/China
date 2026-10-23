#!/bin/sh
# Пересборка тренажёра + проверки. Нужны: python3, node.
set -e
cd "$(dirname "$0")"
python3 build_pwa.py
python3 check.py
