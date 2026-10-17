# -*- coding: utf-8 -*-
"""Картинка для превью ссылки (Open Graph, 1200×630): python3 src/og.py → og.png"""
import os
from playwright.sync_api import sync_playwright
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = """<html><body style="margin:0;width:1200px;height:630px;background:#faf8f5;font-family:'Noto Sans CJK SC',sans-serif;display:flex">
<div style="flex:1;padding:70px 80px;display:flex;flex-direction:column;justify-content:center">
<div style="font-size:150px;font-weight:700;color:#b3261e;line-height:1">你好</div>
<div style="font-size:64px;font-weight:700;color:#1c1b1a;margin-top:28px">Китайский для туриста</div>
<div style="font-size:34px;color:#6b6660;margin-top:18px">Офлайн-разговорник и тренажёр · pinyin и кириллица «как слышится»</div>
<div style="font-size:30px;margin-top:30px"><span style="color:#b3261e">nǐ hǎo</span> · <span style="color:#1f5f8b">ни хао</span> · здравствуйте</div>
</div><div style="width:24px;background:#b3261e"></div></body></html>"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 630})
    pg.set_content(HTML); pg.screenshot(path=os.path.join(OUT, "og.png")); b.close()
print("og.png")
