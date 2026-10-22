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
# в тренажёре вокзалы — часть раздела «Поезд» (в PDF — отдельная страница)
ph["Поезд"] = ph["Поезд"] + st
show = [dict(c, cy=to_cyr(c["py"])) for c in SHOW_CARDS]
groups = [("Без согласного (a, e, o, y-, w-)", [""]), ("b p m f", list("bpmf")), ("d t n l", list("dtnl")),
          ("g k h", list("gkh")), ("j q x", list("jqx")), ("zh ch sh r", ["zh", "ch", "sh", "r"]), ("z c s", list("zcs"))]
syl = [[t, [[x, syl_cyr(x)] for i in ini for x in SYLLABLES_BY_INITIAL[i].split()]] for t, ini in groups]
from lessons import LESSONS
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

guide = [dict(g, phrases=[[z, p, to_cyr(p), r] for z, p, r in g["phrases"]]) for g in GUIDE]
SITE = "https://aleksandrkaiser.github.io/cn-trainer/"
place = {k: [v[0], v[1], to_cyr(v[1])] if isinstance(v, tuple) else v for k, v in PLACE_CARD.items()}
data = {"phrases": ph, "signs": signs, "numbers": nums, "stations": st, "show": show, "tips": TIPS, "syllables": syl,
        "lessons": [lesson_json(l) for l in LESSONS],
        "guide": guide, "checked": CHECKED, "place": place}
tpl = open(os.path.join(SRC, "pwa_template.html"), encoding="utf-8").read()
# версия = хеш шаблона и данных; дата сборки — дата последнего изменения контента (стабильна при пересборке без правок)
body = json.dumps(data, ensure_ascii=False, sort_keys=True)
data["ver"] = hashlib.sha1((tpl + body).encode()).hexdigest()[:8]
stamp_file = os.path.join(SRC, ".build_stamp")
prev = open(stamp_file).read().split() if os.path.exists(stamp_file) else ["", ""]
if prev[0] == data["ver"]:
    data["built"] = prev[1]
else:
    import datetime
    data["built"] = datetime.date.today().isoformat()
    open(stamp_file, "w").write(data["ver"] + " " + data["built"] + "\n")
n_phr = sum(len(v) for v in PHRASES.values())
jsonld = {"@context": "https://schema.org", "@type": "WebApplication", "name": "Китайский для туриста",
          "url": SITE, "inLanguage": "ru", "applicationCategory": "EducationalApplication", "operatingSystem": "iOS, Android, любой браузер",
          "isAccessibleForFree": True, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "RUB"},
          "description": f"Офлайн-разговорник китайского для туристов: {n_phr} фраз, {len(SIGNS)} вывесок, {len(LESSONS)} уроков, справочник о жизни в Китае. Pinyin и произношение кириллицей.",
          "codeRepository": "https://github.com/aleksandrkaiser/cn-trainer", "license": "https://opensource.org/licenses/MIT"}
html = (tpl.replace("__DATA__", json.dumps(data, ensure_ascii=False))
           .replace("__JSONLD__", json.dumps(jsonld, ensure_ascii=False))
           .replace("__SITE__", SITE))
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(html)

manifest = {"id": "./", "name": "Китайский: разговорник", "short_name": "Китайский", "start_url": "./", "scope": "./",
            "description": "Офлайн-разговорник и тренажёр китайского для туриста",
            "display": "standalone", "background_color": "#faf8f5", "theme_color": "#b3261e", "lang": "ru",
            "categories": ["education", "travel"],
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
# robots.txt здесь бесполезен: краулеры читают его только из корня домена (aleksandrkaiser.github.io/robots.txt).
# sitemap.xml подаётся вручную в Google Search Console / Яндекс.Вебмастер.
open(os.path.join(OUT, "sitemap.xml"), "w").write(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    f'  <url><loc>{SITE}</loc><lastmod>{data["built"]}</lastmod></url>\n'
    f'  <url><loc>{SITE}China_razgovornik.pdf</loc><lastmod>{data["built"]}</lastmod></url>\n</urlset>\n')
print("built", ver, len(html), "bytes")
