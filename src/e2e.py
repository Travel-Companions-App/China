# -*- coding: utf-8 -*-
"""Сквозной тест тренажёра в headless Chromium (Playwright).

Проходит главную (поиск, недавние, избранное, разделы), показ крупно, «Мои места» → такси,
все уроки, справку, карточки, тест, настройки; затем проверяет офлайн-перезагрузку и баннер обновления.

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
    n = pg.locator("#hbody .sec").count(); check(n >= 15, f"разделы на главной: {n}")
    check(pg.locator("#tabs button").count() == 3, "вкладки: Главная / Показать / Ещё")
    check("Фраза дня" not in pg.locator("#hbody").inner_text() and "Урок" not in pg.locator("#hbody").inner_text(), "на главной нет фразы дня и уроков")

    print("Поиск")
    for q, min_n in [("вода", 3), ("shui", 3), ("水", 3), ("туалет", 2), ("дзи-чанг", 1), ("Alipay", 2)]:
        pg.fill("#hq", q); n = pg.locator("#hres .ritem").count()
        check(n >= min_n, f"«{q}» → {n} фраз")
    pg.fill("#hq", "такси"); check(pg.locator("#hres .rlink").count() >= 1, "«такси» находит статью справки")
    pg.fill("#hq", "вода"); shot("2-search")
    pg.locator("#hres [data-fv]").first.click(); check(ev("Object.keys(favs).length") == 1, "звёздочка добавила в избранное")
    pg.locator("#hres .ritem").first.click(); check(pg.is_visible("#full"), "результат открывается крупно")
    i0 = ev("fullS.i"); pg.keyboard.press("ArrowRight"); check(ev("fullS.i") == i0 + 1, "листание к следующему результату")
    pg.click("[data-f=close]"); pg.fill("#hq", ""); pg.dispatch_event("#hq", "input")

    print("Главная: недавние, избранное, разделы")
    check(pg.locator("#hbody h2", has_text="Недавние").count() == 1 and pg.locator("#hbody .hrow").count() >= 2, "недавние и избранное на главной")
    pg.locator("#hbody .hrow").first.click(); check(pg.is_visible("#full"), "недавняя фраза открывается крупно"); pg.click("[data-f=close]")
    pg.click("#hbody [data-sec='Фразы: Такси']")
    check(ev("view") == "list" and pg.locator("#list .item").count() == ev("DATA.phrases['Такси'].length"), "раздел «Такси» открывается списком")
    pg.click("#tabs [data-v=home]")

    print("Показ крупно")
    pg.click("[data-sh=nochinese]"); check("中文" in pg.locator("#full .zh").inner_text(), "«Не говорю» → карточка")
    fz = ev("fullS.fz"); pg.click("[data-f=plus]"); check(ev("fullS.fz") > fz, "A+ увеличивает шрифт")
    pg.click("[data-f=rot]"); check("rot" in pg.get_attribute("#full", "class"), "поворот")
    pg.click("[data-f=rot]"); pg.click("[data-f=minus]")
    pg.click("[data-f=close]"); check(not pg.is_visible("#full"), "закрытие")
    pg.click("#tabs [data-v=show]"); n = pg.locator("#shows .sc").count(); check(n >= 8, f"вкладка «Показать»: {n} карточек (7 + избранное)")
    check("酒店" not in pg.locator("#shows").inner_text(), "в карточках нет конкретного отеля")

    print("Мои места")
    ev("store.set('trips', [{city: 'Тестоград', hotel: '测试酒店', addr: '测试路1号', phone: '+86 1', station: '上海虹桥站'}]); localStorage.removeItem('cn:places'); 0")
    pg.click("#tabs [data-v=home]"); pg.click("[data-h=taxi]")
    check(ev("view") == "places" and pg.locator("#v-places [data-p]").count() == 2, "«Такси» → «Мои места»; перенос из старой поездки: отель + вокзал")
    pg.click("[data-a=add]"); pg.fill("#pf-name", "Ресторан"); pg.fill("#pf-zh", "好吃饭店"); pg.fill("#pf-addr", "人民路8号"); pg.click("[data-a=save]")
    check(pg.locator("#v-places [data-p]").count() == 3 and "好吃饭店" in pg.locator("#v-places [data-p='0']").inner_text(), "место добавлено, новое — сверху")
    shot("5-places")
    pg.click("#v-places [data-p='0']"); t = pg.locator("#full .zh").inner_text()
    check("请带我们去这里" in t and "好吃饭店" in t and "人民路8号" in t, "карточка для водителя: название и адрес")
    shot("3-show-full")
    pg.keyboard.press("ArrowRight"); check(ev("fullS.list.length") == 3 and ev("fullS.i") == 1, "листание между местами")
    pg.click("[data-f=close]")
    pg.click("#v-places [data-e='0']"); pg.fill("#pf-name", "Ресторан у дома"); pg.click("[data-a=save]")
    check("Ресторан у дома" in pg.locator("#v-places").inner_text(), "место изменено")
    ev("window.confirm = () => true; 0"); pg.click("#v-places [data-e='0']"); pg.click("[data-a=del]")
    check(pg.locator("#v-places [data-p]").count() == 2, "место удалено")
    pg.click("#tabs [data-v=show]"); t = pg.locator("#shows").inner_text()
    check("测试酒店" in t and "上海虹桥站" in t, "места попадают в «Показать»")
    pg.click("#tabs [data-v=home]"); pg.fill("#hq", "Тестоград"); check(pg.locator("#hres .ritem").count() >= 1, "места находятся поиском")
    pg.fill("#hq", ""); pg.dispatch_event("#hq", "input")
    pg.reload(); pg.wait_for_selector("#hq"); check(ev("places().length") == 2, "места сохраняются после перезапуска")

    print("Уроки")
    pg.click("#tabs [data-v=more]"); pg.click("[data-go=les]")
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

    print("Справка")
    pg.click("#tabs [data-v=more]"); pg.click("[data-go=gd]")
    for i in range(ev("DATA.guide.length")):
        pg.click(f"[data-g='{i}']"); check(pg.locator(".pts li").count() > 0 and pg.locator(".src a").count() > 0, "статья: " + ev(f"DATA.guide[{i}].title"))
        pg.click("[data-a=list]")

    print("Ещё")
    pg.click("#tabs [data-v=more]"); pg.click("[data-go=learn]")
    ev("$('deck').value = 'Фразы: Такси'; $('deck').onchange(); 0")
    check(ev("cur !== null"), "карточка показана")
    check(pg.locator("#fc .zh").count() == 1 and pg.locator("#fc .py").inner_text() == ev("cur.py"), "на лицевой стороне иероглифы и pinyin")
    check(pg.locator("#fc .ru").count() == 0, "перевод скрыт до нажатия")
    pg.click("#fc"); check(pg.locator("#fc .ru").count() == 1 and pg.locator("#fc .cy").count() == 1, "нажатие открывает кириллицу и перевод")
    pg.click("#pyf"); pg.click("#fc"); check(pg.locator("#fc .py").count() == 0, "pinyin можно спрятать до переворота"); pg.click("#pyf")
    n = ev("visibleCards().length"); seen = [ev("cur.id")]
    for _ in range(n - 1): pg.click("#bNext"); seen.append(ev("cur.id"))
    check(len(set(seen)) == n, f"«Дальше» проходит всю колоду без повторов: {len(set(seen))} из {n}")
    pg.click("#bBack"); check(ev("cur.id") == seen[-2], "«Назад» возвращает предыдущую карточку")
    pg.click("#bBack"); pg.click("#bNext"); check(ev("cur.id") == seen[-2], "«Дальше» после «Назад» идёт по истории")
    first = ev("cur.id"); pg.click("#bHide")
    check(ev("Object.keys(hidden).length") == 1 and ev("visibleCards().length") == n - 1 and ev("cur.id") != first, "«Знаю — не показывать» скрывает и листает дальше")
    ids = []
    for _ in range(n + 2): pg.click("#bNext"); ids.append(ev("cur.id"))
    check(first not in ids, f"скрытая карточка не появляется за {len(ids)} шагов")
    pg.click("#bHidden"); check(pg.locator("#lhid [data-uh]").count() == 2, "список скрытых с «Вернуть»")
    pg.locator("#lhid [data-uh]").nth(1).click(); check(ev("Object.keys(hidden).length") == 0 and ev("visibleCards().length") == n, "карточка возвращена")
    pg.click("#bHidden")
    pg.click("#fc"); pg.click("#bHide"); check(ev("Object.keys(hidden).length") == 1, "скрытие для проверки перезапуска")
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
    shot("1-home")


    print("Настройки")
    pg.click("#tabs [data-v=more]"); pg.click("[data-go=set]")
    pg.click("[data-th=dark]"); check(ev("document.documentElement.dataset.theme") == "dark", "тёмная тема")
    pg.reload(); pg.wait_for_selector("#hq"); check(ev("document.documentElement.dataset.theme") == "dark", "тема сохраняется после перезапуска")
    if SHOTS: shot("7-home-dark")
    ev("setTheme('auto')")
    check(ev("Object.keys(favs).length") == 1 and ev("Object.keys(hidden).length") == 1, "избранное и скрытые карточки сохранились после перезапуска")

    print("Офлайн")
    ctx.set_offline(True); pg.reload(); pg.wait_for_selector("#hq")
    check("офлайн" in pg.locator("#net").inner_text(), "индикатор «офлайн»")
    pg.click("#tabs [data-v=more]"); pg.click("[data-go=les]"); check(pg.locator("[data-l]").count() == 8, "уроки офлайн")
    pg.click("#tabs [data-v=home]"); pg.click("[data-h=taxi]"); check(pg.locator("#v-places [data-p]").count() == 2, "мои места офлайн")
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
