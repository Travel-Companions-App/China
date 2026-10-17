# -*- coding: utf-8 -*-
"""Сквозной тест тренажёра в headless Chromium (Playwright).

Проходит главную, поиск, показ крупно, все уроки и диалоги, справку, карточки, тест,
поездку, настройки; затем проверяет офлайн-перезагрузку и баннер обновления.

    python3 src/e2e.py            # тест
    python3 src/e2e.py --shots    # + скриншоты для README в docs/screenshots/
Нужно: pip install playwright && python3 -m playwright install chromium
"""
import os, sys, shutil, tempfile, threading, functools, http.server, socketserver
from playwright.sync_api import sync_playwright

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = "--shots" in sys.argv
FILES = ["index.html", "sw.js", "manifest.webmanifest", "icon-180.png", "icon-192.png", "icon-512.png"]

tmp = tempfile.mkdtemp()
for f in FILES: shutil.copy(os.path.join(OUT, f), tmp)
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
Handler = functools.partial(Quiet, directory=tmp)
srv = socketserver.TCPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/"

errors, fails = [], []
def check(cond, msg):
    print(("  ok  " if cond else "  FAIL ") + msg)
    if not cond: fails.append(msg)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2 if SHOTS else 1,
                        is_mobile=True, has_touch=True, locale="ru-RU", color_scheme="light")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
    shot = lambda name: SHOTS and pg.screenshot(path=os.path.join(OUT, "docs", "screenshots", name + ".png"))
    if SHOTS: os.makedirs(os.path.join(OUT, "docs", "screenshots"), exist_ok=True)
    ev = pg.evaluate

    pg.goto(URL); pg.wait_for_function("typeof render === 'function' && document.querySelector('#hq') !== null", timeout=15000)
    check(not errors, "страница загрузилась без ошибок JS" + ("" if not errors else ": " + errors[0]))
    if errors: sys.exit(1)
    ev("navigator.serviceWorker.ready.then(() => true)")
    pg.reload(); pg.wait_for_selector("#hq"); check(ev("!!navigator.serviceWorker.controller"), "service worker управляет страницей")
    print("Главная")
    check(pg.locator(".hero h1").inner_text().startswith("你好"), "заголовок")
    check(pg.locator(".qk").count() == 3, "три быстрые кнопки")
    check("поездки" in pg.locator("#hsub").inner_text() or "Пекин" in pg.locator("#hsub").inner_text(), "строка поездки: " + pg.locator("#hsub").inner_text())
    shot("1-home")

    print("Поиск")
    for q, min_n in [("вода", 3), ("shui", 3), ("水", 3), ("туалет", 2), ("дзи-чанг", 1), ("Alipay", 2)]:
        pg.fill("#hq", q); n = pg.locator("#hres .ritem").count()
        check(n >= min_n, f"«{q}» → {n} фраз")
    pg.fill("#hq", "такси"); check(pg.locator("#hres .rlink").count() >= 1, "«такси» находит статью/диалог")
    pg.fill("#hq", "вода"); shot("2-search")
    pg.locator("#hres [data-fv]").first.click(); check(ev("Object.keys(favs).length") == 1, "звёздочка добавила в избранное")
    pg.locator("#hres .ritem").first.click(); check(pg.is_visible("#full"), "результат открывается крупно")
    pg.click("[data-f=close]"); pg.fill("#hq", ""); pg.dispatch_event("#hq", "input")

    print("Показ крупно")
    pg.click("[data-sh=taxi]"); check("酒店" in pg.locator("#full .zh").inner_text(), "такси → карточка отеля")
    fz = ev("fullS.fz"); pg.click("[data-f=plus]"); check(ev("fullS.fz") > fz, "A+ увеличивает шрифт")
    pg.click("[data-f=rot]"); check("rot" in pg.get_attribute("#full", "class"), "поворот")
    pg.click("[data-f=rot]"); pg.click("[data-f=minus]")
    i0 = ev("fullS.i"); pg.keyboard.press("ArrowRight"); check(ev("fullS.i") == i0 + 1, "листание к следующей карточке")
    shot("3-show-full")
    pg.click("[data-f=close]"); check(not pg.is_visible("#full"), "закрытие")
    pg.click("#tabs [data-v=show]"); n = pg.locator("#shows .sc").count(); check(n >= 8, f"вкладка «Показать»: {n} карточек (7 + избранное)")

    print("Уроки")
    pg.click("#tabs [data-v=les]")
    for n in range(1, ev("DATA.lessons.length") + 1):
        pg.click(f"[data-l='{n}']"); pg.click("[data-a=start]"); steps = 0
        while ev("lesState.mode") == "ex" and steps < 200:
            e = ev("lesState.list[lesState.i]")
            if e["t"] == "order":
                ev("lesState.picked = lesState.list[lesState.i].tiles.map((t,i)=>i); drawTiles()"); pg.click("[data-a=check]")
            else:
                pg.click(f"#opts [data-o='{e['ok']}']")
            pg.click("[data-a=next]"); steps += 1
        check(ev("lesState.mode") == "done" and ev("lesState.score") == ev("lesState.list.length"), f"урок {n}: {ev('lesState.score')}/{ev('lesState.list.length')}")
        if n == 2: shot("4-lesson-done")
        pg.click("[data-a=list]")

    print("Диалоги")
    pg.click("#tabs [data-v=dlg]")
    for i in range(ev("DATA.dialogs.length")):
        pg.click(f"[data-d='{i}']"); steps = 0
        while ev("dlg.step < dlg.d.steps.length") and steps < 60:
            k = ev("dlg.d.steps[dlg.step].opts.findIndex(o => o.ok)"); pg.click(f"#turn [data-i='{k}']"); steps += 1
        check(ev("dlg.errors") == 0 and pg.locator("#turn").inner_text().startswith("Сценарий пройден"), "диалог: " + ev("dlg.d.title"))
        if i == 3: pg.evaluate("window.scrollTo(0, 0)"); shot("5-dialog")
        pg.click("#turn [data-a=list]")

    print("Справка")
    pg.click("#tabs [data-v=gd]")
    for i in range(ev("DATA.guide.length")):
        pg.click(f"[data-g='{i}']"); check(pg.locator(".pts li").count() > 0 and pg.locator(".src a").count() > 0, "статья: " + ev(f"DATA.guide[{i}].title"))
        pg.click("[data-a=list]")

    print("Ещё")
    pg.click("#tabs [data-v=more]"); pg.click("[data-go=learn]")
    check(ev("cur !== null"), "карточка показана")
    for ok in [True, True, False, True]:
        pg.click("#fc"); pg.click("#bYes" if ok else "#bNo")
    check(ev("Object.keys(srs).length") >= 3, f"интервальное повторение записано: {ev('Object.keys(srs).length')}")
    pg.click("#tabs [data-v=more]"); pg.click("[data-go=quiz]"); pg.locator("#qopts .opt").first.click(); check(ev("score.n") == 1, "тест отвечает")
    pg.click("#tabs [data-v=more]"); pg.click("[data-go=list]"); pg.fill("#q", "метро"); check(pg.locator("#list .item").count() >= 2, "список фраз с поиском")
    pg.locator("#list .item").first.click(); check(pg.is_visible("#full"), "фраза из списка открывается крупно"); pg.click("[data-f=close]")
    pg.click("#tabs [data-v=more]"); pg.click("[data-go=syl]"); check(pg.locator(".syl").count() == 406, "406 слогов")

    print("Мои фразы")
    diff = ev("ALL.filter(c => c.deck !== MY && toCyr(c.py) !== c.cy).map(c => c.py + ' → ' + toCyr(c.py) + ' ≠ ' + c.cy)")
    check(not diff, "кириллица в JS совпадает с Python для всех фраз" + ("" if not diff else ": " + "; ".join(diff[:3])))
    pg.click("#tabs [data-v=more]"); pg.click("[data-go=my]")
    ev("window.__opened = []; window.open = function (u) { window.__opened.push(u); return null; }; 0")
    pg.fill("#my-ask", "у меня аллергия на арахис"); pg.click("[data-m=ask]")
    url = ev("window.__opened[0] || ''")
    check(url.startswith("https://claude.ai/new?q=") and "%E6%B1%89%E5%AD%97" in url, "«Спросить Claude» открывает claude.ai с запросом")
    sample = "Вот варианты:\n- 我对花生过敏 | wǒ duì huāshēng guòmǐn | у меня аллергия на арахис\n2. 里面有花生吗？ | lǐmiàn yǒu huāshēng ma? | внутри есть арахис?\n没有 | méiyǒu | нет (слышите)\nqqqq | xx | не строка"
    pg.fill("#my-paste", sample); pg.click("[data-m=parse]")
    check(pg.locator("#v-my .item").count() == 3, "разобрано 3 строки из ответа")
    check("во дуэй хуа-шэнг гуо-мин" in pg.locator("#v-my").inner_text(), "кириллица построена: " + ev("toCyr('wǒ duì huāshēng guòmǐn')"))
    pg.click("[data-m=save]"); check(ev("ALL.filter(c => c.deck === MY).length") == 3, "сохранено в «Мои фразы»")
    pg.click("#tabs [data-v=home]"); pg.fill("#hq", "арахис"); check(pg.locator("#hres .ritem").count() >= 2, "свои фразы находятся поиском")
    pg.click("#hres [data-ask]"); check(ev("view") == "my" and pg.input_value("#my-ask") == "арахис", "из поиска — в «Спросить Claude» с запросом")
    shot("8-my-phrases")
    pg.click("#tabs [data-v=home]"); pg.fill("#hq", ""); pg.dispatch_event("#hq", "input")

    print("Поездка")
    pg.click("#tabs [data-v=more]"); pg.click("[data-go=trips]")
    check(pg.locator("[data-t]").count() == 1, "пример города есть")
    shot("6-trips")
    pg.click("[data-a=add]")
    pg.fill("#tf-city", "Тестоград"); pg.fill("#tf-from", ev("isoDay(today())")); pg.fill("#tf-hotel", "测试酒店"); pg.fill("#tf-addr", "测试路1号"); pg.fill("#tf-station", "上海虹桥站")
    pg.click("[data-a=save]"); check(pg.locator("[data-t]").count() == 2, "город добавлен")
    pg.click("#tabs [data-v=show]")
    t = pg.locator("#shows").inner_text()
    check("Тестоград" in t and "测试酒店" in t and "上海虹桥站" in t, "карточки такси → отель и вокзал из поездки")
    ev("store.set('trips', trips().filter(s => s.city !== 'Тестоград'))")

    print("Настройки")
    pg.click("#tabs [data-v=more]"); pg.click("[data-go=set]")
    pg.click("[data-th=dark]"); check(ev("document.documentElement.dataset.theme") == "dark", "тёмная тема")
    pg.reload(); pg.wait_for_selector("#hq"); check(ev("document.documentElement.dataset.theme") == "dark", "тема сохраняется после перезапуска")
    if SHOTS: shot("7-home-dark")
    ev("setTheme('auto')")
    check(ev("Object.keys(favs).length") == 1 and ev("Object.keys(srs).length") >= 3, "прогресс сохранился после перезапуска")

    print("Офлайн")
    ctx.set_offline(True); pg.reload(); pg.wait_for_selector("#hq")
    check("офлайн" in pg.locator("#net").inner_text(), "индикатор «офлайн»")
    pg.click("#tabs [data-v=les]"); check(pg.locator("[data-l]").count() == 8, "уроки офлайн")
    pg.click("#tabs [data-v=show]"); pg.locator("#shows .sc").first.click(); check(pg.is_visible("#full"), "показ офлайн")
    pg.click("[data-f=close]"); ctx.set_offline(False)

    print("Обновление")
    sw = open(os.path.join(tmp, "sw.js")).read().replace('const CACHE = "cn-', 'const CACHE = "cn-test-')
    open(os.path.join(tmp, "sw.js"), "w").write(sw)
    ev("swReg.update()")
    try: pg.wait_for_selector("#upd:not(.hide)", timeout=10000); check(True, "баннер «Доступна новая версия»")
    except Exception: check(False, "баннер «Доступна новая версия»")

    check(not errors, "ошибок JS нет" + ("" if not errors else ": " + "; ".join(errors[:5])))
    b.close()
srv.shutdown(); shutil.rmtree(tmp)
print("E2E:", "OK" if not fails else f"ОШИБКИ ({len(fails)})"); sys.exit(1 if fails else 0)
