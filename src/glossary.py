# -*- coding: utf-8 -*-
"""Пословный перевод: разбиение китайского текста на слова словаря (words.py) и сверка с pinyin контента.

Разбиение — жадное по самому длинному слову словаря слева направо; тот же алгоритм в pwa_template.html (segWords).
"""
import re, sys, os
SRC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SRC)
from translit import SYLSET, strip_tones

HAN = re.compile(r"[㐀-鿿]")
TONED = re.compile(r"[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]")


def seg(text, words, maxlen):
    """[(кусок, есть_в_словаре)]; китайские символы вне словаря — по одному, со значением False."""
    out, i, n = [], 0, len(text)
    while i < n:
        if HAN.match(text[i]):
            for L in range(min(maxlen, n - i), 0, -1):
                if text[i:i + L] in words:
                    out.append((text[i:i + L], True)); i += L; break
            else:
                out.append((text[i], False)); i += 1
        else:
            j = i
            while j < n and not HAN.match(text[j]): j += 1
            out.append((text[i:j], None)); i = j
    return out


def _split_word(w):
    """Слово pinyin с тонами → слоги с тонами (по таблице слогов; не более одного тона на слог)."""
    low = w.lower()
    bare = strip_tones(low)
    n = len(bare)
    best = [None] * (n + 1); best[0] = []
    for i in range(n):
        if best[i] is None: continue
        for L in range(1, min(7, n - i + 1)):
            p = bare[i:i + L]
            if p in SYLSET and len(TONED.findall(low[i:i + L])) <= 1:
                if best[i + L] is None or len(best[i]) + 1 < len(best[i + L]):
                    best[i + L] = best[i] + [(i, i + L)]
    if best[n] is None and bare.endswith("r"):
        s = _split_word(w[:-1])
        return None if s is None else s + ["r"]
    return None if best[n] is None else [low[a:b] for a, b in best[n]]


def syllables(py, zh=""):
    out = []
    for w in re.findall(r"[A-Za-zÀ-ɏüÜ]+", py):
        if w in zh: continue  # латиница из самой надписи (WiFi, B口)
        for part in w.split("'"):
            s = _split_word(part)
            if s is None: return None
            out += s
    return out


def align(zh, py):
    """[(иероглиф, слог)] или None, если число слогов не сходится."""
    chars = HAN.findall(zh)
    s = syllables(py, zh)
    if s is None or len(s) != len(chars): return None
    return list(zip(chars, s))


def pairs():
    """Все пары (汉字, pinyin, источник) из контента приложения."""
    import data, guide, lessons
    out = []
    def add(z, p, src):
        zs, ps = z.split(" / "), p.split(" / ")
        if len(zs) == len(ps) > 1:
            for a, b in zip(zs, ps): out.append((a, b, src))
        else: out.append((z, p, src))
    for sec, v in data.PHRASES.items():
        for z, p, r in v: add(z, p, sec)
    for z, p, r, g in data.SIGNS: add(z, p, "Вывески")
    for z, p, r in data.BEIJING_STATIONS: add(z, p, "Вокзалы")
    for c in data.SHOW_CARDS: add("".join(c["zh"]), c["py"], "Карточки")
    for v in data.PLACE_CARD.values():
        if isinstance(v, tuple): add(v[0], v[1], "Места")
    for g in guide.GUIDE:
        for z, p, r in g["phrases"]: add(z, p, "Справка")
    for i, l in enumerate(lessons.LESSONS):
        src = "Урок %d" % (i + 1)
        for b in l["theory"]:
            if b["k"] == "e": add(b["zh"], b["py"], src)
        for x in l["ex"]:
            if x.get("zh") and x.get("py"): add(x["zh"], x["py"], src)
            for o in x.get("opts", []) + x.get("tiles", []):
                if isinstance(o, (tuple, list)): add(o[0], o[1], src)
    return out


def all_han_text():
    """Все строки контента, где есть иероглифы (для проверки покрытия)."""
    import data, guide, lessons
    found = []
    def walk(o):
        if isinstance(o, str):
            if HAN.search(o): found.append(o)
        elif isinstance(o, dict):
            for v in o.values(): walk(v)
        elif isinstance(o, (list, tuple)):
            for v in o: walk(v)
    for n in dir(data):
        if n.isupper(): walk(getattr(data, n))
    walk(guide.GUIDE); walk(lessons.LESSONS)
    return found


def check(words):
    """Ошибки: иероглифы вне словаря; pinyin слова словаря не совпадает с pinyin контента (без учёта тонов)."""
    maxlen = max(map(len, words))
    errs = []
    for t in all_han_text():
        miss = [p for p, ok in seg(t, words, maxlen) if ok is False]
        if miss: errs.append("нет в словаре: %s ← %s" % ("".join(miss), t[:40]))
    for z, p, src in pairs():
        al = align(z, p)
        if not al: continue
        k = 0
        for piece, ok in seg(z, words, maxlen):
            if ok is None: continue
            n = len(piece); got = [s for _, s in al[k:k + n]]; k += n
            if ok:
                want = syllables(words[piece][0], piece)
                if want is None or [strip_tones(x) for x in want] != [strip_tones(x) for x in got]:
                    errs.append("pinyin %s: словарь «%s», в «%s» — «%s»" % (piece, words[piece][0], z, " ".join(got)))
    return errs
