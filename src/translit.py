# -*- coding: utf-8 -*-
"""Pinyin -> кириллица «как слышится» (приблизительно, без тонов)."""
import re, unicodedata

SYLLABLES_BY_INITIAL = {
    "": "a ai an ang ao e ei en eng er o ou yi ya yao ye you yan yin yang ying yong yu yue yuan yun wu wa wo wai wei wan wen wang weng",
    "b": "ba bai ban bang bao bei ben beng bi bian biao bie bin bing bo bu",
    "p": "pa pai pan pang pao pei pen peng pi pian piao pie pin ping po pou pu",
    "m": "ma mai man mang mao me mei men meng mi mian miao mie min ming miu mo mou mu",
    "f": "fa fan fang fei fen feng fo fou fu",
    "d": "da dai dan dang dao de dei deng di dian diao die ding diu dong dou du duan dui dun duo",
    "t": "ta tai tan tang tao te teng ti tian tiao tie ting tong tou tu tuan tui tun tuo",
    "n": "na nai nan nang nao ne nei nen neng ni nian niang niao nie nin ning niu nong nou nu nuan nuo nü nüe",
    "l": "la lai lan lang lao le lei leng li lia lian liang liao lie lin ling liu long lou lu luan lun luo lü lüe",
    "g": "ga gai gan gang gao ge gei gen geng gong gou gu gua guai guan guang gui gun guo",
    "k": "ka kai kan kang kao ke kei ken keng kong kou ku kua kuai kuan kuang kui kun kuo",
    "h": "ha hai han hang hao he hei hen heng hong hou hu hua huai huan huang hui hun huo",
    "j": "ji jia jian jiang jiao jie jin jing jiong jiu ju juan jue jun",
    "q": "qi qia qian qiang qiao qie qin qing qiong qiu qu quan que qun",
    "x": "xi xia xian xiang xiao xie xin xing xiong xiu xu xuan xue xun",
    "zh": "zha zhai zhan zhang zhao zhe zhei zhen zheng zhi zhong zhou zhu zhua zhuai zhuan zhuang zhui zhun zhuo",
    "ch": "cha chai chan chang chao che chen cheng chi chong chou chu chua chuai chuan chuang chui chun chuo",
    "sh": "sha shai shan shang shao she shei shen sheng shi shou shu shua shuai shuan shuang shui shun shuo",
    "r": "ran rang rao re ren reng ri rong rou ru rua ruan rui run ruo",
    "z": "za zai zan zang zao ze zei zen zeng zi zong zou zu zuan zui zun zuo",
    "c": "ca cai can cang cao ce cen ceng ci cong cou cu cuan cui cun cuo",
    "s": "sa sai san sang sao se sen seng si song sou su suan sui sun suo",
}
SYLLABLES = [s for v in SYLLABLES_BY_INITIAL.values() for s in v.split()]
SYLSET = set(SYLLABLES)

INIT = {"b": "б", "p": "п", "m": "м", "f": "ф", "d": "д", "t": "т", "n": "н", "l": "л",
        "g": "г", "k": "к", "h": "х", "j": "дз", "q": "ч", "x": "с",
        "zh": "дж", "ch": "ч", "sh": "ш", "r": "ж", "z": "дз", "c": "ц", "s": "с"}

FINAL = {"a": "а", "ai": "ай", "an": "ан", "ang": "анг", "ao": "ао", "e": "э", "ei": "эй",
         "en": "эн", "eng": "энг", "er": "эр", "o": "о", "ou": "оу", "ong": "онг",
         "i": "и", "ia": "я", "ian": "ьен", "iang": "янг", "iao": "яо", "ie": "ье", "in": "ин",
         "ing": "инг", "iong": "ёнг", "iu": "ёу",
         "u": "у", "ua": "уа", "uai": "уай", "uan": "уан", "uang": "уанг", "ui": "уэй", "un": "ун", "uo": "уо",
         "ü": "юй", "üe": "юэ"}
# после j q x: u = ü
PALATAL_U = {"u": "юй", "ue": "юэ", "uan": "юэн", "un": "юн"}
ZERO = {"yi": "и", "ya": "я", "yao": "яо", "ye": "е", "you": "ёу", "yan": "йен", "yin": "ин",
        "yang": "янг", "ying": "инг", "yong": "ёнг", "yu": "юй", "yue": "юэ", "yuan": "юэн", "yun": "юн",
        "wu": "у", "wa": "ва", "wo": "во", "wai": "вай", "wei": "вэй", "wan": "ван", "wen": "вэн",
        "wang": "ванг", "weng": "вэнг"}
BUZZ = {"zhi": "джы", "chi": "чы", "shi": "шы", "ri": "жы", "zi": "дзы", "ci": "цы", "si": "сы"}


def syl_cyr(s):
    if s in BUZZ: return BUZZ[s]
    if s in ZERO: return ZERO[s]
    for ini in ("zh", "ch", "sh"):
        if s.startswith(ini):
            return INIT[ini] + FINAL[s[2:]]
    if s[0] in INIT:
        ini, fin = s[0], s[1:]
        if ini in "jqx" and fin in PALATAL_U:
            return INIT[ini] + PALATAL_U[fin]
        return INIT[ini] + FINAL[fin]
    return FINAL[s]


TONE = str.maketrans("āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙ",
                     "aaaaeeeeiiiioooouuuuüüüüAAAAEEEEIIIIOOOOUUUU")


def strip_tones(t):
    return t.translate(TONE)


def segment(word):
    """DP: минимальное число слогов. word без тонов, lower."""
    n = len(word)
    best = [None] * (n + 1)
    best[0] = []
    for i in range(n):
        if best[i] is None: continue
        for L in range(1, min(7, n - i + 1)):
            p = word[i:i + L]
            if p in SYLSET and (best[i + L] is None or len(best[i]) + 1 < len(best[i + L])):
                best[i + L] = best[i] + [p]
    return best[n]


def word_cyr(w):
    base = strip_tones(w).lower()
    parts = []
    for chunk in base.split("'"):
        seg = segment(chunk)
        er = ""
        if seg is None and chunk.endswith("r"):
            seg = segment(chunk[:-1]); er = "р"
        if seg is None:
            return None
        cy = [syl_cyr(x) for x in seg]
        cy[-1] += er
        parts += cy
    return "-".join(parts)


def to_cyr(text):
    """Транслитерирует pinyin-текст, сохраняя пунктуацию; не-pinyin слова оставляет как есть."""
    def rep(m):
        w = m.group(0)
        c = word_cyr(w)
        return c if c is not None else w
    return re.sub(r"[A-Za-zÀ-ɏüÜ']+", rep, text)


if __name__ == "__main__":
    print(len(SYLLABLES), "syllables")
    for t in ["Nǐ hǎo", "xièxie", "Shīfu, qǐng dài wǒmen qù zhège jiǔdiàn", "xǐshǒujiān zài nǎr?",
              "zài zhèr tíng", "shí'èr hào", "Zhīfùbǎo", "WiFi mìmǎ shì duōshao?", "nǚ", "qù", "xuéxí",
              "Éluósī rén", "èrshíwǔ", "liǎng ge rén", "jǐ wèi?"]:
        print(t, "→", to_cyr(t))
