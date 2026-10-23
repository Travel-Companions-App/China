# -*- coding: utf-8 -*-
"""Проверки после сборки: транскрипция, данные, синтаксис JS."""
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
items = [p for v in PHRASES.values() for _, p, _ in v] + [p for _, p, _, _ in SIGNS] \
        + [p for _, p, _ in BEIJING_STATIONS] + [c["py"] for c in SHOW_CARDS] \
        + [v[1] for v in PLACE_CARD.values() if isinstance(v, tuple)]
from lessons import LESSONS
from guide import GUIDE
struct = []
for l in LESSONS:
    items += [b["py"] for b in l["theory"] if b["k"] == "e"]
    for x in l["ex"]:
        if "py" in x: items.append(x["py"])
        items += [o[1] for o in x.get("opts", []) if isinstance(o, tuple)] + [t[1] for t in x.get("tiles", [])]
        if x["t"] in ("choice", "listen") and not 0 <= x["ok"] < len(x["opts"]): struct.append(f"урок {l['n']}: неверный ok")
        if x["t"] == "order" and len(x["tiles"]) < 2: struct.append(f"урок {l['n']}: мало блоков")
for g in GUIDE:
    items += [p for _, p, _ in g["phrases"]]
    if not g["sources"]: struct.append(f"справка «{g['title']}»: нет источника")
print("уроков:", len(LESSONS), "| статей:", len(GUIDE), "| ошибки структуры:", struct or "нет"); ok &= not struct
# латиница без тонов из заглавных (B口, WiFi) — не pinyin
bad = {w for p in items for w in re.findall(r"[A-Za-zÀ-ɏüÜ']+", p) if word_cyr(w) is None and not re.fullmatch(r"[A-Z]+|WiFi", w)}
print("pinyin без разбора на слоги:", bad or "нет"); ok &= not bad
from words import WORDS
from glossary import check as gloss_check
gerr = gloss_check(WORDS)
print("пословный словарь:", len(WORDS), "слов | ошибки:", gerr[:5] or "нет"); ok &= not gerr
import json
for f in ["index.html", "diag.html"]:
    page = open(os.path.join(OUT, f), encoding="utf-8").read()
    for i, js in enumerate(re.findall(r"<script>(.*?)</script>", page, re.S)):
        tmp = os.path.join(SRC, "_check.js"); open(tmp, "w").write(js)
        r = subprocess.run(["node", "--check", tmp], capture_output=True); os.remove(tmp)
        print(f, f"JS #{i + 1}:", "OK" if r.returncode == 0 else r.stderr.decode()[:200]); ok &= r.returncode == 0
    for js in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
        try: json.loads(js); print(f, "JSON-LD: OK")
        except ValueError as e: print(f, "JSON-LD:", e); ok = False
    left = re.findall(r"__[A-Z]+__", page)
    if left: print(f, "незаменённые метки:", set(left)); ok = False
r = subprocess.run(["node", "--check", os.path.join(OUT, "sw.js")], capture_output=True)
print("sw.js JS:", "OK" if r.returncode == 0 else "ОШИБКА"); ok &= r.returncode == 0
print("ИТОГ:", "OK" if ok else "ЕСТЬ ОШИБКИ"); sys.exit(0 if ok else 1)
