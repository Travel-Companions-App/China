#!/bin/sh
# Пересборка PDF и тренажёра + проверки. Нужны: python3, wkhtmltopdf, шрифт Noto Sans CJK SC, node.
set -e
cd "$(dirname "$0")"
python3 build_pdf.py
python3 build_pwa.py
python3 check.py
