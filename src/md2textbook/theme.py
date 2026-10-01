import re
from functools import lru_cache
from pathlib import Path

import matplotlib
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph

from . import mathkit

PAGE_W, PAGE_H = A4
ML = MR = 62
MT, MB = 74, 70
TEXT_W = PAGE_W - ML - MR

INDIGO = HexColor("#4F46E5")
INDIGO_DARK = HexColor("#312E81")
INDIGO_SOFT = HexColor("#EEF2FF")
PURPLE = HexColor("#6D28D9")
INK = HexColor("#1F2937")
MUTED = HexColor("#6B7280")
RULE = HexColor("#E5E7EB")
ZEBRA = HexColor("#F5F6FB")
LINK = "#4338CA"
INLINE_CODE = "#9D174D"

# kind -> (label, bar colour, tint)
BOXES = {
    "definition": ("DEFINITION", "#2563EB", "#EFF6FF"),
    "example": ("WORKED EXAMPLE", "#16A34A", "#F0FDF4"),
    "insight": ("INSIGHT", "#7C3AED", "#F5F3FF"),
    "warning": ("WARNING", "#DC2626", "#FEF2F2"),
    "recap": ("RECAP", "#6B7280", "#F3F4F6"),
    "objective": ("LEARNING OBJECTIVES", "#0D9488", "#F0FDFA"),
    "code": ("CODE", "#EA580C", "#FFF7ED"),
    "idea": ("RESEARCH IDEA", "#B45309", "#FFF4E0"),
    "review": ("REVIEWER'S VIEW", "#DB2777", "#FDF2F8"),
    "brief": ("QUICK REFERENCE", "#0891B2", "#ECFEFF"),
    "math": ("MATH", "#1E3A8A", "#E8EEFF"),
    "note": ("NOTE", "#0EA5E9", "#F0F9FF"),
    "quote": (None, "#A5B4FC", "#F8F9FF"),
}

# alias -> (box kind, label shown)
ALIASES = {
    "TIP": ("insight", "TIP"),
    "IMPORTANT": ("insight", "IMPORTANT"),
    "CAUTION": ("warning", "CAUTION"),
    "DANGER": ("warning", "DANGER"),
    "SUMMARY": ("recap", "SUMMARY"),
    "TAKEAWAYS": ("recap", "KEY TAKEAWAYS"),
    "KEY TAKEAWAYS": ("recap", "KEY TAKEAWAYS"),
    "OBJECTIVES": ("objective", None),
    "GOAL": ("objective", "GOAL"),
    "GOALS": ("objective", "GOALS"),
    "THEOREM": ("math", "THEOREM"),
    "LEMMA": ("math", "LEMMA"),
    "PROOF": ("math", "PROOF"),
    "DERIVATION": ("math", "DERIVATION"),
    "EXERCISE": ("example", "EXERCISE"),
    "WARN": ("warning", None),
    "REFERENCE": ("brief", None),
    "CHEATSHEET": ("brief", None),
}


def box_spec(name: str) -> tuple[str, str | None] | None:
    key = name.strip().upper()
    if key.lower() in BOXES and key.lower() != "quote":
        return key.lower(), None
    if key in ALIASES:
        kind, label = ALIASES[key]
        return kind, label
    return None


FONT_DIR = Path(__file__).parent / "fonts"
MPL_FONTS = Path(matplotlib.get_data_path()) / "fonts" / "ttf"


def _register(name: str, bundled: str, fallback: str) -> None:
    path = FONT_DIR / bundled
    if not bundled or not path.exists():
        path = MPL_FONTS / fallback
    pdfmetrics.registerFont(TTFont(name, str(path)))


def register_fonts() -> None:
    sans, sans_b = "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"
    serif = {"": "DejaVuSerif.ttf", "-B": "DejaVuSerif-Bold.ttf", "-I": "DejaVuSerif-Italic.ttf",
             "-BI": "DejaVuSerif-BoldItalic.ttf"}
    _register("Head", "Poppins-Regular.ttf", sans)
    _register("HeadL", "Poppins-Light.ttf", sans)
    _register("HeadM", "Poppins-Medium.ttf", sans_b)
    _register("HeadSB", "Poppins-SemiBold.ttf", sans_b)
    _register("HeadB", "Poppins-Bold.ttf", sans_b)
    for suffix, fallback in serif.items():
        style = {"": "Regular", "-B": "Bold", "-I": "Italic", "-BI": "BoldItalic"}[suffix]
        _register(f"Body{suffix}", f"Caladea-{style}.ttf", fallback)
    _register("Sym", "", sans)
    _register("Sym-B", "", sans_b)
    _register("Mono", "", "DejaVuSansMono.ttf")
    _register("Mono-B", "", "DejaVuSansMono-Bold.ttf")
    reg = pdfmetrics.registerFontFamily
    reg("Body", normal="Body", bold="Body-B", italic="Body-I", boldItalic="Body-BI")
    reg("Sym", normal="Sym", bold="Sym-B", italic="Sym", boldItalic="Sym-B")
    reg("Mono", normal="Mono", bold="Mono-B", italic="Mono", boldItalic="Mono-B")
    for head in ("Head", "HeadL", "HeadM", "HeadSB", "HeadB"):
        reg(head, normal=head, bold="HeadB", italic=head, boldItalic="HeadB")


@lru_cache(maxsize=None)
def coverage(font: str) -> frozenset[int]:
    face = getattr(pdfmetrics.getFont(font), "face", None)
    glyphs = getattr(face, "charToGlyph", None)
    return frozenset(glyphs) if glyphs else frozenset(range(32, 127))


PRIVATE = range(0xE000, 0xF900)


def wrap_missing_glyphs(text: str, font: str) -> str:
    have, sym = coverage(font), coverage("Sym")
    out: list[str] = []
    in_sym = False
    for part in re.split(r"(<[^>]*>)", text):
        if part.startswith("<") and part.endswith(">") and len(part) > 1:
            out.append(part)
            continue
        for ch in part:
            code = ord(ch)
            needs_sym = code not in have and code in sym and not ch.isspace() and code not in PRIVATE
            if needs_sym and not in_sym:
                out.append('<font name="Sym">')
            elif not needs_sym and in_sym:
                out.append("</font>")
            in_sym = needs_sym
            out.append(ch)
        if in_sym:
            out.append("</font>")
            in_sym = False
    return "".join(out)


def xml_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_CODE = re.compile(r"(`+)(.+?)\1")
_ESCAPED = re.compile(r"\\([\\`*_{}\[\]()#+\-.!$|~<>])")
_MATH = re.compile(r"(?<![\\$])\$(?!\s)([^$\n]+?)(?<!\s)\$(?![\d$])")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_BOLD_ITALIC = re.compile(r"\*\*\*(.+?)\*\*\*")
_BOLD = re.compile(r"\*\*(.+?)\*\*|(?<!\w)__(.+?)__(?!\w)")
_ITALIC = re.compile(r"(?<![\w*])\*(?![\s*])(.+?)(?<![\s*])\*(?![\w*])|(?<![\w\\])_(?![\s_])(.+?)(?<![\s_])_(?!\w)")
_STRIKE = re.compile(r"~~(.+?)~~")
_LINEBREAK = re.compile(r"<br\s*/?>", re.I)
_PLACEHOLDER = re.compile("\ue000(\\d+)\ue001")


def code_span(code: str, size: float = 9.0) -> str:
    body = xml_escape(code).replace(" ", "&nbsp;")
    return f'<font name="Mono" size="{size}" color="{INLINE_CODE}">{body}</font>'


def inline_math(tex: str, size: float) -> str:
    rendered = mathkit.render(tex, size)
    if rendered is None:
        return code_span(tex, size - 1.5)
    return (f'<img src="{rendered.path}" width="{rendered.width:.2f}" height="{rendered.height:.2f}" '
            f'valign="{-rendered.depth:.2f}"/>')


def inline(text: str, font: str = "Body", size: float = 10.5) -> str:
    stash: list[str] = []

    def keep(markup: str) -> str:
        stash.append(markup)
        return f"\ue000{len(stash) - 1}\ue001"

    text = _CODE.sub(lambda m: keep(code_span(m.group(2).strip(), size - 1.5)), text)
    text = _ESCAPED.sub(lambda m: keep(xml_escape(m.group(1))), text)
    text = _MATH.sub(lambda m: keep(inline_math(m.group(1), size)), text)
    text = _LINEBREAK.sub(lambda m: keep("<br/>"), text)
    text = xml_escape(text)
    text = _LINK.sub(lambda m: f'<link href="{keep(xml_escape(m.group(2)))}" color="{LINK}">{m.group(1)}</link>', text)
    text = _BOLD_ITALIC.sub(r"<b><i>\1</i></b>", text)
    text = _BOLD.sub(lambda m: f"<b>{m.group(1) or m.group(2)}</b>", text)
    text = _ITALIC.sub(lambda m: f"<i>{m.group(1) or m.group(2)}</i>", text)
    text = _STRIKE.sub(r"<strike>\1</strike>", text)
    text = wrap_missing_glyphs(text, font)
    return _PLACEHOLDER.sub(lambda m: stash[int(m.group(1))], text)


def plain(text: str) -> str:
    text = _CODE.sub(r"\2", text)
    text = _LINK.sub(r"\1", text)
    text = re.sub(r"[*~$]+|(?<!\w)_+|_+(?!\w)", "", text)
    return text.strip()


def style(name: str, font: str, size: float, leading: float | None = None, color=INK, **kw) -> ParagraphStyle:
    return ParagraphStyle(name, fontName=font, fontSize=size, leading=leading or size * 1.4, textColor=color, **kw)


def make_styles() -> dict[str, ParagraphStyle]:
    return {
        "body": style("body", "Body", 10.5, 15.6, spaceAfter=6, alignment=TA_LEFT),
        "lead": style("lead", "Body-I", 12, 17.5, color=INDIGO_DARK, spaceAfter=10),
        "sec": style("sec", "HeadSB", 15, 20, color=INDIGO_DARK, spaceBefore=18, spaceAfter=7, keepWithNext=1),
        "sub": style("sub", "HeadM", 12, 16, color=INDIGO, spaceBefore=13, spaceAfter=5, keepWithNext=1),
        "subsub": style("subsub", "HeadM", 10, 14, color=MUTED, spaceBefore=10, spaceAfter=4, keepWithNext=1),
        "bullet": style("bullet", "Body", 10.5, 15, spaceAfter=2.5, bulletFontName="HeadB", bulletFontSize=9,
                        bulletColor=INDIGO),
        "box_body": style("box_body", "Body", 10, 14.2, spaceAfter=3),
        "box_bullet": style("box_bullet", "Body", 10, 14, spaceAfter=2, bulletFontName="HeadB", bulletFontSize=8.5),
        "box_label": style("box_label", "HeadB", 7.4, 10),
        "box_title": style("box_title", "HeadSB", 10.5, 14, color=INK, spaceAfter=2),
        "caption": style("caption", "Body-I", 9, 12, color=MUTED, alignment=TA_CENTER, spaceBefore=4, spaceAfter=10),
        "th": style("th", "HeadSB", 8.6, 11, color=HexColor("#FFFFFF")),
        "td": style("td", "Body", 9.6, 12.6),
        "code_label": style("code_label", "HeadM", 8.4, 11, color=INDIGO_DARK, spaceBefore=6, spaceAfter=3,
                            keepWithNext=1),
        "toc_title": style("toc_title", "HeadB", 24, 30, color=INDIGO_DARK, spaceAfter=18),
        "toc0": style("toc0", "HeadSB", 11, 15, color=INDIGO_DARK, spaceBefore=9, spaceAfter=1, leftIndent=0),
        "toc1": style("toc1", "Body", 11, 14.5, color=INK, leftIndent=18, spaceBefore=1),
        "kicker": style("kicker", "HeadM", 9, 12, color=HexColor("#A5B4FC")),
        "chapter": style("chapter", "HeadB", 24, 29, color=HexColor("#FFFFFF")),
        "cover_title": style("cover_title", "HeadB", 36, 44, color=HexColor("#FFFFFF"), alignment=TA_CENTER),
        "cover_sub": style("cover_sub", "HeadL", 16, 23, color=HexColor("#E0E7FF"), alignment=TA_CENTER),
        "cover_meta": style("cover_meta", "HeadM", 10, 15, color=HexColor("#C7D2FE"), alignment=TA_CENTER),
    }


def para(text: str, st: ParagraphStyle, **kw) -> Paragraph:
    return Paragraph(inline(text, st.fontName, st.fontSize), st, **kw)
