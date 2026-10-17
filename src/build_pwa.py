# -*- coding: utf-8 -*-
import json, sys, shutil, hashlib
import os
SRC = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(SRC)
sys.path.insert(0, SRC)
from data import *
from translit import to_cyr, SYLLABLES_BY_INITIAL, syl_cyr

ph = {k: [[z, p, to_cyr(p), r] for z, p, r in v] for k, v in PHRASES.items()}
signs = [[z, p, to_cyr(p), r, g] for z, p, r, g in SIGNS]
nums = [[z, p, to_cyr(p), r] for z, p, r in NUMBERS]
st = [[z, p, to_cyr(p), r] for z, p, r in BEIJING_STATIONS]
show = [dict(c, cy=to_cyr(c["py"])) for c in SHOW_CARDS]
groups = [("Без согласного (a, e, o, y-, w-)", [""]), ("b p m f", list("bpmf")), ("d t n l", list("dtnl")),
          ("g k h", list("gkh")), ("j q x", list("jqx")), ("zh ch sh r", ["zh", "ch", "sh", "r"]), ("z c s", list("zcs"))]
syl = [[t, [[x, syl_cyr(x)] for i in ini for x in SYLLABLES_BY_INITIAL[i].split()]] for t, ini in groups]
from lessons import LESSONS
from dialogs import DIALOGS
from guide import GUIDE, CHECKED

TONEMARK = {"a": "āáǎà", "e": "ēéěè", "i": "īíǐì", "o": "ōóǒò", "u": "ūúǔù", "ü": "ǖǘǚǜ"}
def tone_variants(py):
    """mǎi -> [māi, mái, mǎi, mài]; верный — исходный."""
    from translit import strip_tones
    bare = strip_tones(py).lower()
    if "a" in bare or "e" in bare: v = "a" if "a" in bare else "e"; pos = bare.index(v)
    elif "ou" in bare: v = "o"; pos = bare.index("o")
    else: pos = max(i for i, ch in enumerate(bare) if ch in "iouü"); v = bare[pos]
    return [bare[:pos] + TONEMARK[v][t] + bare[pos + 1:] for t in range(4)]

def opt(o):
    return [o[0], o[1], to_cyr(o[1])] if isinstance(o, (tuple, list)) else o

def lesson_json(l):
    th = [dict(b, cy=to_cyr(b["py"])) if b["k"] == "e" else b for b in l["theory"]]
    ex = []
    for e in l["ex"]:
        e = dict(e)
        if "py" in e: e["cy"] = to_cyr(e["py"])
        if "opts" in e: e["opts"] = [opt(o) for o in e["opts"]]
        if "tiles" in e: e["tiles"] = [opt(t) for t in e["tiles"]]
        if e["t"] == "tone":
            e["opts"] = tone_variants(e["py"]); e["ok"] = e["opts"].index(e["py"])
        ex.append(e)
    return dict(l, theory=th, ex=ex)

def line(s):
    return dict(s, cy=to_cyr(s["py"])) if s else None

def dialog_json(d):
    steps = []
    for s in d["steps"]:
        if s["who"] == "them": steps.append(line(s))
        else: steps.append(dict(s, opts=[dict(a, cy=to_cyr(a["py"]), reply=line(a["reply"])) for a in s["opts"]]))
    return dict(d, steps=steps)

guide = [dict(g, phrases=[[z, p, to_cyr(p), r] for z, p, r in g["phrases"]]) for g in GUIDE]
data = {"phrases": ph, "signs": signs, "numbers": nums, "stations": st, "show": show, "tips": TIPS, "syllables": syl,
        "lessons": [lesson_json(l) for l in LESSONS], "dialogs": [dialog_json(d) for d in DIALOGS],
        "guide": guide, "checked": CHECKED}
html = open(os.path.join(SRC, "pwa_template.html"), encoding="utf-8").read().replace("__DATA__", json.dumps(data, ensure_ascii=False))
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(html)

manifest = {"name": "Китайский: разговорник", "short_name": "Китайский", "start_url": "./", "scope": "./",
            "display": "standalone", "background_color": "#faf8f5", "theme_color": "#b3261e", "lang": "ru",
            "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                      {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"}]}
open(os.path.join(OUT, "manifest.webmanifest"), "w", encoding="utf-8").write(json.dumps(manifest, ensure_ascii=False, indent=1))

ver = hashlib.sha1(html.encode()).hexdigest()[:8]
sw = f"""const CACHE = "cn-{ver}";
const FILES = ["./", "index.html", "manifest.webmanifest", "icon-180.png", "icon-192.png", "icon-512.png"];
self.addEventListener("install", e => {{ e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting())); }});
self.addEventListener("activate", e => {{ e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); }});
self.addEventListener("fetch", e => {{
  if (e.request.method !== "GET") return;
  e.respondWith(caches.match(e.request, {{ignoreSearch: true}}).then(r => r || fetch(e.request).catch(() => caches.match("index.html"))));
}});
"""
open(os.path.join(OUT, "sw.js"), "w").write(sw)
print("built", ver, len(html), "bytes")
