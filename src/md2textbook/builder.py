import sys
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from pygments import lex
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.token import Token
from pygments.util import ClassNotFound
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, HRFlowable, Image, KeepTogether,
                                NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

from . import mathkit, theme
from .theme import (BOXES, INDIGO, INDIGO_DARK, INDIGO_SOFT, INK, MB, ML, MR, MT, MUTED, PAGE_H, PAGE_W, PURPLE, RULE,
                   TEXT_W, ZEBRA, code_span, inline, para, plain, xml_escape)

FRAME_H = PAGE_H - MT - MB

CODE_BG = HexColor("#282C34")
CODE_FG = "#ABB2BF"
CODE_STYLES = {
    Token.Keyword: "#C678DD",
    Token.Keyword.Constant: "#D19A66",
    Token.Name.Function: "#61AFEF",
    Token.Name.Class: "#E5C07B",
    Token.Name.Builtin: "#56B6C2",
    Token.Name.Decorator: "#61AFEF",
    Token.Name.Tag: "#E06C75",
    Token.Name.Attribute: "#D19A66",
    Token.Name.Exception: "#E5C07B",
    Token.Literal.String: "#98C379",
    Token.Literal.Number: "#D19A66",
    Token.Comment: "#7F848E",
    Token.Operator: "#56B6C2",
    Token.Generic.Heading: "#E5C07B",
    Token.Generic.Deleted: "#E06C75",
    Token.Generic.Inserted: "#98C379",
}
PLAIN_LANGS = {"", "text", "txt", "bash", "sh", "shell", "console", "powershell", "ps1", "cmd", "bat"}
MONO_SIZE = 7.8
MONO_W = 0.602 * MONO_SIZE
BOX_INSET = 26


class Heading(Paragraph):
    toc = None


class Equation(Flowable):
    PAD = 7

    def __init__(self, rendered: mathkit.Rendered, label: str | None):
        super().__init__()
        self.rendered, self.label = rendered, label

    def wrap(self, aw, ah):
        side = 40 if self.label else 0
        scale = min(1.0, (aw - 2 * side) / self.rendered.width)
        self.w, self.h = self.rendered.width * scale, self.rendered.height * scale
        self.aw = aw
        return aw, self.h + 2 * self.PAD

    def draw(self):
        c = self.canv
        c.drawImage(self.rendered.path, (self.aw - self.w) / 2, self.PAD, self.w, self.h, mask="auto")
        if self.label:
            c.setFont("Body", 10)
            c.setFillColor(MUTED)
            c.drawRightString(self.aw, self.PAD + self.h / 2 - 3, self.label)


def _code_color(ttype) -> str | None:
    while ttype is not Token:
        if ttype in CODE_STYLES:
            return CODE_STYLES[ttype]
        ttype = ttype.parent
    return None


def _highlight_lines(code: str, lang: str) -> list[list[tuple[str | None, str, bool]]]:
    try:
        lexer = get_lexer_by_name(lang or "text", stripnl=False, ensurenl=False)
    except ClassNotFound:
        lexer = TextLexer(stripnl=False, ensurenl=False)
    lines: list[list[tuple[str | None, str, bool]]] = [[]]
    for ttype, value in lex(code, lexer):
        italic = ttype in Token.Comment
        color = _code_color(ttype)
        for i, chunk in enumerate(value.split("\n")):
            if i:
                lines.append([])
            if chunk:
                lines[-1].append((color, chunk, italic))
    return lines


def _wrap_segments(segments, width: int) -> list[list[tuple[str | None, str, bool]]]:
    rows, current, used = [], [], 0
    for color, text, italic in segments:
        while text:
            room = width - used
            if room <= 0:
                rows.append(current)
                current, used = [], 2
                room = width - used
            piece, text = text[:room], text[room:]
            current.append((color, piece, italic))
            used += len(piece)
    rows.append(current)
    return rows


def _markup(segments, continuation: bool) -> str:
    out = ['<font name="Sym" color="#5C6370">↪</font>&nbsp;'] if continuation else []
    for color, text, italic in segments:
        body = xml_escape(text).replace(" ", "&nbsp;")
        body = f"<i>{body}</i>" if italic else body
        out.append(f'<font color="{color or CODE_FG}">{body}</font>')
    return "".join(out) or "&nbsp;"


class Book:
    def __init__(self, path: str | Path, title: str, author: str = ""):
        theme.register_fonts()
        self.path, self.title, self.author = str(path), title, author
        self.S = theme.make_styles()
        self._story: list = []
        self._sink = self._story
        self.depth = 0
        self._cover: dict | None = None
        self._want_toc = False
        self._counters = {"ch": 0, "sec": 0, "sub": 0, "eq": 0, "fig": 0, "lst": 0, "tbl": 0}
        self._headings = 0
        self._last_level = -1
        self._list_styles: dict[tuple, ParagraphStyle] = {}

    @property
    def avail(self) -> float:
        return TEXT_W - self.depth * BOX_INSET

    def _add(self, *flowables) -> "Book":
        self._sink.extend(flowables)
        return self

    def _add_kept(self, parts: list, keep: bool = True) -> "Book":
        if keep and not self.depth:
            return self._add(KeepTogether(parts))
        return self._add(*parts)

    @contextmanager
    def boxed(self):
        saved, items = self._sink, []
        self._sink = items
        self.depth += 1
        try:
            yield items
        finally:
            self._sink = saved
            self.depth -= 1

    def _tag(self) -> str:
        ch = self._counters["ch"]
        return f"{ch}." if ch else ""

    def cover(self, title: str, subtitle: str = "", lines: tuple[str, ...] = ()) -> "Book":
        self._cover = {"title": title, "subtitle": subtitle, "lines": [ln for ln in lines if ln]}
        return self

    def toc(self) -> "Book":
        self._want_toc = True
        return self

    def _heading(self, level: int, title: str, number: str, style_name: str, slug: str = "") -> Heading:
        level = min(level, self._last_level + 1)
        self._last_level = level
        self._headings += 1
        label = f"{number}  {plain(title)}" if number else plain(title)
        style = self.S[style_name]
        prefix = f'<font color="#4F46E5">{number}</font>&nbsp;&nbsp;' if number else ""
        heading = Heading(prefix + inline(title, style.fontName, style.fontSize), style)
        heading.toc = (level, label, f"h{self._headings}", slug)
        return heading

    def chapter(self, title: str, kicker: str | None = None, slug: str = "") -> "Book":
        c = self._counters
        c["ch"] += 1
        c["sec"] = c["sub"] = c["eq"] = c["fig"] = c["lst"] = c["tbl"] = 0
        self._headings += 1
        self._last_level = 0
        number = f"{c['ch']}"
        kick = kicker or f"CHAPTER {c['ch']}"
        rows = [["", para(kick, self.S["kicker"])], ["", para(title, self.S["chapter"])]]
        banner = Table(rows, colWidths=[7, TEXT_W - 7], spaceAfter=16)
        banner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), HexColor("#818CF8")),
            ("BACKGROUND", (1, 0), (1, -1), INDIGO_DARK),
            ("LEFTPADDING", (0, 0), (0, -1), 0), ("RIGHTPADDING", (0, 0), (0, -1), 0),
            ("LEFTPADDING", (1, 0), (1, -1), 17), ("RIGHTPADDING", (1, 0), (1, -1), 20),
            ("TOPPADDING", (0, 0), (-1, 0), 20), ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
            ("TOPPADDING", (0, 1), (-1, 1), 0), ("BOTTOMPADDING", (0, 1), (-1, 1), 22),
        ]))
        banner.toc = (0, f"{number}  {plain(title)}", f"h{self._headings}", slug)
        banner.is_chapter = True
        banner.chapter_title = plain(title)
        return self._add(CondPageBreak(FRAME_H - 1), banner)

    def section(self, title: str, slug: str = "") -> "Book":
        c = self._counters
        c["sec"] += 1
        c["sub"] = 0
        number = f"{c['ch']}.{c['sec']}" if c["ch"] else f"{c['sec']}"
        return self._add(self._heading(1, title, number, "sec", slug))

    def sub(self, title: str, slug: str = "") -> "Book":
        c = self._counters
        c["sub"] += 1
        base = f"{c['ch']}.{c['sec']}" if c["ch"] else f"{c['sec']}"
        return self._add(self._heading(2, title, f"{base}.{c['sub']}", "sub", slug))

    def subsub(self, title: str, slug: str = "") -> "Book":
        return self._add(self._heading(3, title, "", "subsub", slug))

    def para(self, text: str, lead: bool = False) -> "Book":
        style = self.S["lead"] if lead else self.S["box_body" if self.depth else "body"]
        return self._add(para(text, style))

    def _item_style(self, level: int, ordered: bool, symbol: bool = False) -> ParagraphStyle:
        key = (level, ordered, bool(self.depth), symbol)
        if key not in self._list_styles:
            base = self.S["box_bullet" if self.depth else "bullet"]
            indent = 18 + level * 16 + (4 if ordered else 0)
            extra = {"bulletFontName": "Sym"} if symbol else {}
            self._list_styles[key] = ParagraphStyle(f"item{key}", parent=base, leftIndent=indent,
                                                    bulletIndent=indent - (18 if ordered else 12), **extra)
        return self._list_styles[key]

    def item(self, text: str, level: int = 0, marker: str | None = None) -> "Book":
        ordered = bool(marker and marker[0].isdigit())
        marker = marker or ("•", "–", "▪")[min(level, 2)]
        symbol = ord(marker[0]) not in theme.coverage(self.S["bullet"].bulletFontName)
        st = self._item_style(level, ordered, symbol)
        flowable = Paragraph(inline(text, st.fontName, st.fontSize), st, bulletText=marker)
        return self._add(flowable)

    def bullets(self, items: list[str]) -> "Book":
        for text in items:
            self.item(text)
        return self

    def numbered(self, items: list[str]) -> "Book":
        for n, text in enumerate(items, 1):
            self.item(text, marker=f"{n}.")
        return self

    def rule(self) -> "Book":
        return self._add(HRFlowable(width="100%", thickness=0.8, color=RULE, spaceBefore=8, spaceAfter=10))

    def space(self, points: float = 8) -> "Book":
        return self._add(Spacer(1, points))

    def condbreak(self, height: float = 140) -> "Book":
        return self._add(CondPageBreak(height))

    def box(self, kind: str, title: str = "", items=(), label: str | None = None) -> "Book":
        name, bar, tint = BOXES[kind]
        label = label or name
        head: list = []
        if label:
            head.append(Paragraph(label, ParagraphStyle("lbl", parent=self.S["box_label"], textColor=HexColor(bar))))
        if title:
            head.append(para(title, self.S["box_title"]))
        rows = [["", head]] if head else []
        for entry in items:
            if isinstance(entry, str):
                if entry.startswith("- "):
                    with self.boxed() as made:
                        self.item(entry[2:])
                    rows.extend([["", f] for f in made])
                else:
                    rows.append(["", para(entry, self.S["box_body"])])
            else:
                rows.append(["", entry])
        if not rows:
            return self
        table = Table(rows, colWidths=[3.2, self.avail - 3.2], splitByRow=1, spaceBefore=4, spaceAfter=10)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), HexColor(bar)),
            ("BACKGROUND", (1, 0), (1, -1), HexColor(tint)),
            ("LEFTPADDING", (0, 0), (0, -1), 0), ("RIGHTPADDING", (0, 0), (0, -1), 0),
            ("LEFTPADDING", (1, 0), (1, -1), 12), ("RIGHTPADDING", (1, 0), (1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("TOPPADDING", (0, 0), (-1, 0), 9), ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
        ]))
        return self._add_kept([table])

    def define(self, term: str, text: str) -> "Book":
        return self.box("definition", term, [text])

    def eq(self, tex: str, numbered: bool = True) -> "Book":
        numbered = numbered and not self.depth
        label = None
        if numbered:
            self._counters["eq"] += 1
            label = f"({self._tag()}{self._counters['eq']})"
        rendered = mathkit.render(tex, 12.5)
        if rendered is None:
            style = ParagraphStyle("eqfail", parent=self.S["body"], alignment=TA_CENTER)
            return self._add(Paragraph(code_span(tex, 9), style))
        return self._add(Equation(rendered, label))

    def eq_flow(self, lines: list[str], numbered: bool = True) -> "Book":
        for tex in lines:
            self.eq(tex, numbered)
        return self

    def code(self, source: str, lang: str = "", label: str | None = None, numbers: bool | None = None,
             start_line: int = 1) -> "Book":
        source = source.expandtabs(4).rstrip("\n")
        if numbers is None:
            numbers = lang.lower() not in PLAIN_LANGS
        num_w = 30 if numbers else 0
        width = max(30, int((self.avail - num_w - 26) / MONO_W))
        base = ParagraphStyle("code", fontName="Mono", fontSize=MONO_SIZE, leading=10.8, textColor=HexColor(CODE_FG))
        num_style = ParagraphStyle("codenum", parent=base, alignment=TA_RIGHT, textColor=HexColor("#636D83"))
        rows = []
        for offset, segments in enumerate(_highlight_lines(source, lang)):
            for i, chunk in enumerate(_wrap_segments(segments, width)):
                number = str(start_line + offset) if numbers and i == 0 else ""
                cells = [Paragraph(_markup(chunk, i > 0), base)]
                rows.append([Paragraph(number or "&nbsp;", num_style), *cells] if numbers else cells)
        widths = [num_w, self.avail - num_w] if numbers else [self.avail]
        table = Table(rows, colWidths=widths, splitByRow=1, spaceAfter=10)
        pad_left = 8 if numbers else 12
        style = [
            ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, 0), 9), ("BOTTOMPADDING", (0, -1), (-1, -1), 9),
            ("LEFTPADDING", (-1, 0), (-1, -1), pad_left + (4 if numbers else 0)),
            ("ROUNDEDCORNERS", [5, 5, 5, 5]),
        ]
        if numbers:
            style.append(("RIGHTPADDING", (0, 0), (0, -1), 0))
        table.setStyle(TableStyle(style))
        parts: list = []
        if label:
            self._counters["lst"] += 1
            tag = f"Listing {self._tag()}{self._counters['lst']}"
            parts.append(Paragraph(f'<font color="#4F46E5">{tag}</font>&nbsp;&nbsp;{inline(label, "HeadM", 8.4)}',
                                   self.S["code_label"]))
        parts.append(table)
        return self._add_kept(parts, len(rows) <= 28)

    def table(self, header: list[str], rows: list[list[str]], aligns: list[str] | None = None,
              caption: str | None = None) -> "Book":
        cols = len(header)
        aligns = (aligns or []) + ["left"] * cols
        amap = {"left": TA_LEFT, "center": TA_CENTER, "right": TA_RIGHT}
        th = [ParagraphStyle(f"th{i}", parent=self.S["th"], alignment=amap[aligns[i]]) for i in range(cols)]
        td = [ParagraphStyle(f"td{i}", parent=self.S["td"], alignment=amap[aligns[i]]) for i in range(cols)]
        data = [[para(h, th[i]) for i, h in enumerate(header)]]
        for row in rows:
            row = (row + [""] * cols)[:cols]
            data.append([para(cell, td[i]) for i, cell in enumerate(row)])
        lengths = [max([len(header[i])] + [len(r[i]) if i < len(r) else 0 for r in rows]) for i in range(cols)]
        weights = [max(6, min(n, 60)) ** 0.8 for n in lengths]
        widths = [self.avail * w / sum(weights) for w in weights]
        table = Table(data, colWidths=widths, repeatRows=1, splitByRow=1, spaceAfter=10, spaceBefore=4)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), INDIGO_DARK),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, ZEBRA]),
            ("LINEBELOW", (0, 1), (-1, -1), 0.4, RULE),
            ("BOX", (0, 0), (-1, -1), 0.6, RULE),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"), ("VALIGN", (0, 1), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ]))
        parts: list = []
        if caption:
            self._counters["tbl"] += 1
            tag = f"Table {self._tag()}{self._counters['tbl']}"
            cap = ParagraphStyle("tcap", parent=self.S["code_label"], fontSize=9, spaceBefore=8)
            parts.append(Paragraph(f'<font color="#4F46E5">{tag}</font>&nbsp;&nbsp;{inline(caption, "HeadM", 9)}', cap))
        parts.append(table)
        return self._add_kept(parts, len(data) <= 18)

    def figure(self, path: str | Path, caption: str = "") -> "Book":
        path = Path(path)
        try:
            if not path.is_file():
                raise FileNotFoundError(f"no such file: {path}")
            px_w, px_h = ImageReader(str(path)).getSize()
        except Exception as exc:
            reason = "not found" if isinstance(exc, FileNotFoundError) else f"unreadable, {type(exc).__name__}"
            note = f"[image skipped: {path.name} ({reason})]"
            print(f"warning: {note} {path}: {' '.join(str(exc).split())}", file=sys.stderr)
            style = self.S["box_body" if self.depth else "body"]
            return self._add(Paragraph(f"<i>{xml_escape(note)}</i>", style))
        width = min(self.avail, px_w * 0.75)
        height = width * px_h / px_w
        limit = FRAME_H * 0.62
        if height > limit:
            width, height = width * limit / height, limit
        parts: list = [Image(str(path), width, height, hAlign="CENTER")]
        self._counters["fig"] += 1
        if caption:
            tag = f"Figure {self._tag()}{self._counters['fig']}"
            parts.append(Paragraph(f'<font name="HeadM" color="#4F46E5">{tag}</font>&nbsp;&nbsp;'
                                   f"{inline(caption, 'Body-I', 9)}", self.S["caption"]))
        return self._add_kept([Spacer(1, 4), *parts])

    def _draw_cover(self, c, doc):
        data = self._cover or {"title": self.title, "subtitle": "", "lines": []}
        c.saveState()
        clip = c.beginPath()
        clip.rect(0, 0, PAGE_W, PAGE_H)
        c.clipPath(clip, stroke=0, fill=0)
        c.linearGradient(0, PAGE_H, PAGE_W, 0, (INDIGO_DARK, INDIGO, PURPLE), (0, 0.55, 1))
        accents = [HexColor(h) for h in ("#A5B4FC", "#C4B5FD", "#F0ABFC", "#67E8F9", "#FDE68A")]
        for row in range(12):
            for col in range(22):
                c.setFillColor(accents[(row * 3 + col) % len(accents)])
                c.setFillAlpha(max(0.0, 0.5 - row * 0.045))
                c.circle(26 + col * 27, 26 + row * 27, 2.1, stroke=0, fill=1)
        c.setFillAlpha(1)
        width = TEXT_W - 30
        title = Paragraph(inline(data["title"], "HeadB", 36), self.S["cover_title"])
        _, th = title.wrap(width, 400)
        top = PAGE_H * 0.62
        title.drawOn(c, (PAGE_W - width) / 2, top)
        y = top - 18
        c.setFillColor(HexColor("#F0ABFC"))
        c.roundRect((PAGE_W - 64) / 2, y, 64, 4, 2, stroke=0, fill=1)
        y -= 18
        if data["subtitle"]:
            sub = Paragraph(inline(data["subtitle"], "HeadL", 16), self.S["cover_sub"])
            _, sh = sub.wrap(width, 300)
            y -= sh
            sub.drawOn(c, (PAGE_W - width) / 2, y)
        meta_y = PAGE_H * 0.2 + 15 * len(data["lines"])
        for line in data["lines"]:
            meta = Paragraph(inline(line, "HeadM", 10), self.S["cover_meta"])
            meta.wrap(width, 40)
            meta.drawOn(c, (PAGE_W - width) / 2, meta_y)
            meta_y -= 16
        c.restoreState()

    def _footer(self, c, doc):
        text = str(doc.page)
        w = max(28, stringWidth(text, "HeadM", 8.5) + 16)
        c.saveState()
        c.setFillColor(INDIGO_SOFT)
        c.roundRect((PAGE_W - w) / 2, 30, w, 15, 7.5, stroke=0, fill=1)
        c.setFillColor(INDIGO_DARK)
        c.setFont("HeadM", 8.5)
        c.drawCentredString(PAGE_W / 2, 34.6, text)
        c.restoreState()

    def _header(self, c, doc):
        if doc.page in doc.opener_pages:
            return
        c.saveState()
        y = PAGE_H - 44
        c.setFont("HeadL", 8)
        c.setFillColor(MUTED)
        title = self.title
        limit = TEXT_W * 0.55
        while stringWidth(title, "HeadL", 8) > limit and len(title) > 4:
            title = title[:-2].rstrip() + "…"
        c.drawString(ML, y, title)
        chapter = doc.chapter_name
        if chapter:
            while stringWidth(chapter, "HeadM", 8) > TEXT_W * 0.4 and len(chapter) > 4:
                chapter = chapter[:-2].rstrip() + "…"
            c.setFont("HeadM", 8)
            c.setFillColor(INDIGO)
            c.drawRightString(PAGE_W - MR, y, chapter)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.8)
        c.line(ML, y - 7, PAGE_W - MR, y - 7)
        c.restoreState()

    def _document(self) -> BaseDocTemplate:
        book = self

        class Doc(BaseDocTemplate):
            def afterFlowable(self, flowable):
                for f in _walk(flowable):
                    info = getattr(f, "toc", None)
                    if info is None:
                        continue
                    level, text, key, slug = info
                    self.canv.bookmarkPage(key)
                    if slug:
                        self.canv.bookmarkPage(theme.anchor_key(slug))
                    self.canv.addOutlineEntry(text, key, level, closed=0)
                    if level < 2:
                        self.notify("TOCEntry", (level, inline(text, "Body", 10), self.page, key))
                    if getattr(f, "is_chapter", False):
                        self.chapter_name = f.chapter_title
                        self.opener_pages.add(self.page)

        doc = Doc(self.path, pagesize=(PAGE_W, PAGE_H), title=self.title, author=self.author,
                  leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB, creator="md2textbook")
        doc.chapter_name = ""
        doc.opener_pages = set()
        frame = lambda: Frame(ML, MB, TEXT_W, FRAME_H, 0, 0, 0, 0, id="body")
        doc.addPageTemplates([
            PageTemplate("cover", [Frame(0, 0, PAGE_W, PAGE_H, id="cover")], onPage=book._draw_cover),
            PageTemplate("front", [frame()], onPageEnd=book._footer),
            PageTemplate("main", [frame()], onPageEnd=lambda c, d: (book._header(c, d), book._footer(c, d))),
        ])
        return doc

    def build(self) -> str:
        front: list = [NextPageTemplate("front"), PageBreak()]
        if self._want_toc and self._headings:
            toc = TableOfContents()
            toc.levelStyles = [self.S["toc0"], self.S["toc1"]]
            toc.dotsMinLevel = 0
            front += [Paragraph("Contents", self.S["toc_title"]), toc]
        front += [NextPageTemplate("main"), PageBreak()]
        story = front + self._story
        self._document().multiBuild(story)
        return self.path


def _walk(flowable):
    yield flowable
    for child in getattr(flowable, "_content", None) or ():
        yield from _walk(child)


def today() -> str:
    return date.today().strftime("%B %d, %Y").replace(" 0", " ")
