# -*- coding: utf-8 -*-
"""Проверки после сборки: транскрипция, PDF без переполнений, синтаксис JS."""
import os, re, sys, subprocess
SRC = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.dirname(SRC)
sys.path.insert(0, SRC)
from translit import SYLLABLES, syl_cyr, word_cyr
from data import *
ok = True
dup = {}
for s in SYLLABLES: dup.setdefault(syl_cyr(s), []).append(s)
coll = {k: v for k, v in dup.items() if len(v) > 1}
print("слогов:", len(SYLLABLES), "| совпадений кириллицы:", coll or "нет"); ok &= not coll
items = [p for v in PHRASES.values() for _, p, _ in v] + [p for _, p, _, _ in SIGNS] + [p for _, p, _ in NUMBERS] \
        + [p for _, p, _ in BEIJING_STATIONS] + [c["py"] for c in SHOW_CARDS] + [HOTEL["addr_py"]]
bad = {w for p in items for w in re.findall(r"[A-Za-zÀ-ɏüÜ']+", p) if word_cyr(w) is None} - {"WiFi"}
print("pinyin без разбора на слоги:", bad or "нет"); ok &= not bad
pdf = os.path.join(OUT, "China_razgovornik.pdf")
n = int(re.search(r"Pages:\s+(\d+)", subprocess.check_output(["pdfinfo", pdf]).decode()).group(1))
divs = open(os.path.join(SRC, "_print.html"), encoding="utf-8").read().count('class="page"')
print(f"PDF: страниц {n}, блоков {divs}", "OK" if n == divs else "ПЕРЕПОЛНЕНИЕ"); ok &= n == divs
for f in ["index.html", "diag.html"]:
    js = re.search(r"<script>(.*)</script>", open(os.path.join(OUT, f), encoding="utf-8").read(), re.S).group(1)
    tmp = os.path.join(SRC, "_check.js"); open(tmp, "w").write(js)
    r = subprocess.run(["node", "--check", tmp], capture_output=True); os.remove(tmp)
    print(f, "JS:", "OK" if r.returncode == 0 else r.stderr.decode()[:200]); ok &= r.returncode == 0
r = subprocess.run(["node", "--check", os.path.join(OUT, "sw.js")], capture_output=True)
print("sw.js JS:", "OK" if r.returncode == 0 else "ОШИБКА"); ok &= r.returncode == 0
print("ИТОГ:", "OK" if ok else "ЕСТЬ ОШИБКИ"); sys.exit(0 if ok else 1)
