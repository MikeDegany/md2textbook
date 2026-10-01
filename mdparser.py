import re
from pathlib import Path
from urllib.parse import unquote

import mathkit
from build import Book, today
from theme import box_spec

FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})\s*(.*)$")
ATX = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)(?:\s+#+)?\s*$")
HR = re.compile(r"^\s{0,3}([-*_])(?:\s*\1){2,}\s*$")
LIST = re.compile(r"^(\s*)([-*+]|\d{1,9}[.)])\s+(.*)$")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
IMAGE = re.compile(r'^\s*!\[(.*?)\]\(\s*(<[^>]+>|[^)\s]+)(?:\s+"(.*?)")?\s*\)\s*$')
QUOTE = re.compile(r"^\s{0,3}>\s?(.*)$")
TAG_ONLY = re.compile(r"^\s*</?[a-zA-Z][^>]*>\s*$")
CALLOUT = re.compile(r"^\[!([A-Za-z ]+)\]\s*(.*)$")
BOLD_LEAD = re.compile(r"^\*\*([A-Za-z ]+?)(?::\*\*|\*\*:?)\s*(.*)$")
MATRIX_ENV = re.compile(r"\\begin\{(?:cases|[pbvBV]?matrix|array)\}")
MATH_LANGS = {"math", "latex", "tex", "equation"}


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    match = re.match(r"^\ufeff?---\s*\n(.*?)\n(?:---|\.\.\.)\s*(?:\n|$)", text, re.S)
    if not match:
        return {}, text
    meta = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip():
            meta[key.strip().lower()] = value.strip().strip("\"'")
    return meta, text[match.end():]


def split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    return [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", line)]


def column_aligns(sep: str) -> list[str]:
    aligns = []
    for cell in split_row(sep):
        left, right = cell.startswith(":"), cell.endswith(":")
        aligns.append("center" if left and right else "right" if right else "left")
    return aligns


def is_block_start(lines: list[str], i: int) -> bool:
    line = lines[i]
    if (FENCE.match(line) or ATX.match(line) or HR.match(line) or QUOTE.match(line) or LIST.match(line)
            or IMAGE.match(line) or line.strip().startswith(("$$", "\\["))):
        return True
    return "|" in line and i + 1 < len(lines) and "-" in lines[i + 1] and bool(TABLE_SEP.match(lines[i + 1]))


def parse_blocks(lines: list[str]) -> list[tuple]:
    blocks: list[tuple] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith("<!--"):
            while i < n and "-->" not in lines[i]:
                i += 1
            i += 1
            continue
        if TAG_ONLY.match(line):
            i += 1
            continue

        if m := FENCE.match(line):
            fence, info = m.group(1), m.group(2)
            indent = len(line) - len(line.lstrip())
            body = []
            i += 1
            while i < n and not (lines[i].strip().startswith(fence[0] * len(fence)) and not lines[i].strip().strip(fence[0])):
                body.append(lines[i][indent:] if lines[i][:indent].strip() == "" else lines[i])
                i += 1
            i += 1
            blocks.append(("code", info, "\n".join(body)))
            continue

        if stripped.startswith("$$") or stripped.startswith("\\["):
            opener = "$$" if stripped.startswith("$$") else "\\["
            closer = "$$" if opener == "$$" else "\\]"
            rest = stripped[2:]
            if closer in rest:
                tex = rest[:rest.index(closer)]
                i += 1
            else:
                parts = [rest]
                i += 1
                while i < n and closer not in lines[i]:
                    parts.append(lines[i])
                    i += 1
                if i < n:
                    parts.append(lines[i][:lines[i].index(closer)])
                i += 1
                tex = "\n".join(parts)
            blocks.append(("math", tex))
            continue

        if m := ATX.match(line):
            blocks.append(("heading", len(m.group(1)), m.group(2)))
            i += 1
            continue

        if HR.match(line):
            blocks.append(("hr",))
            i += 1
            continue

        if m := IMAGE.match(line):
            blocks.append(("image", m.group(1), m.group(2).strip("<>"), m.group(3) or ""))
            i += 1
            continue

        if "|" in line and i + 1 < n and "-" in lines[i + 1] and TABLE_SEP.match(lines[i + 1]):
            header = split_row(line)
            aligns = column_aligns(lines[i + 1])
            rows = []
            i += 2
            while i < n and lines[i].strip() and "|" in lines[i]:
                rows.append(split_row(lines[i]))
                i += 1
            blocks.append(("table", header, rows, aligns))
            continue

        if QUOTE.match(line):
            inner = []
            while i < n and lines[i].strip():
                q = QUOTE.match(lines[i])
                if q:
                    inner.append(q.group(1))
                elif is_block_start(lines, i):
                    break
                else:
                    inner.append(lines[i])
                i += 1
            blocks.append(("quote", inner))
            continue

        if LIST.match(line):
            items, i = parse_list(lines, i)
            blocks.append(("list", items))
            continue

        buf = [line]
        i += 1
        while i < n and lines[i].strip() and not is_block_start(lines, i):
            if re.match(r"^\s{0,3}=+\s*$", lines[i]):
                break
            buf.append(lines[i])
            i += 1
        if i < n and re.match(r"^\s{0,3}=+\s*$", lines[i]):
            blocks.append(("heading", 1, " ".join(s.strip() for s in buf)))
            i += 1
            continue
        text = ""
        for ln in buf:
            ln_stripped = ln.strip()
            hard = ln.endswith("  ") or ln_stripped.endswith("\\")
            ln_stripped = ln_stripped.rstrip("\\").rstrip() if ln_stripped.endswith("\\") else ln_stripped
            text += ln_stripped + ("<br>" if hard else " ")
        text = text.strip()
        if text.lower().startswith("table:"):
            blocks.append(("tablecaption", text[6:].strip()))
        else:
            blocks.append(("para", text))
    return blocks


def parse_list(lines: list[str], i: int) -> tuple[list[tuple[int, str | None, str]], int]:
    items: list[list] = []
    indents: list[int] = []
    counters: dict[int, int] = {}
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            j = i
            while j < n and not lines[j].strip():
                j += 1
            if j < n and (LIST.match(lines[j]) or (lines[j].startswith("  ") and not is_block_start(lines, j))):
                i = j
                continue
            break
        m = LIST.match(line.expandtabs(4))
        if m:
            indent = len(m.group(1))
            while indents and indent < indents[-1]:
                indents.pop()
            if not indents or indent > indents[-1]:
                indents.append(indent)
            level = len(indents) - 1
            marker_src, text = m.group(2), m.group(3)
            for deeper in [k for k in counters if k > level]:
                del counters[deeper]
            marker = None
            if marker_src[0].isdigit():
                counters.setdefault(level, int(marker_src[:-1]))
                marker = f"{counters[level]}."
                counters[level] += 1
            else:
                counters.pop(level, None)
            if text.startswith("[ ] "):
                text = "\u2610 " + text[4:]
            elif text[:4].lower() == "[x] ":
                text = "\u2611 " + text[4:]
            items.append([level, marker, text.strip()])
        elif line.startswith((" ", "\t")) or not is_block_start(lines, i):
            if items:
                items[-1][2] += " " + line.strip()
        else:
            break
        i += 1
    return [tuple(item) for item in items], i


def parse_info(info: str) -> tuple[str, dict]:
    parts = info.strip().strip("{}").split(None, 1)
    lang = parts[0].lstrip(".").lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""
    opts: dict = {}
    if m := re.search(r"""title=(?:"([^"]*)"|'([^']*)'|(\S+))""", rest):
        opts["label"] = next(g for g in m.groups() if g is not None)
    if re.search(r"\b(nonumbers|linenos=false|numbers=false)\b", rest):
        opts["numbers"] = False
    elif re.search(r"\b(linenos|numbers)\b", rest):
        opts["numbers"] = True
    if m := re.search(r"\bstart=(\d+)", rest):
        opts["start_line"] = int(m.group(1))
    return lang, opts


class Renderer:
    def __init__(self, book: Book, base: Path, title_heading: int | None, chapter_level: int):
        self.book, self.base = book, base
        self.title_heading = title_heading
        self.chapter_level = chapter_level
        self.last_out = 0
        self.heading_seen = 0

    def render(self, blocks: list[tuple]) -> None:
        b = self.book
        pending_caption = None
        i = 0
        while i < len(blocks):
            kind, *args = blocks[i]
            i += 1
            if kind == "tablecaption":
                nxt = blocks[i][0] if i < len(blocks) else None
                if nxt == "table":
                    pending_caption = args[0]
                else:
                    b.para(args[0])
                continue
            if kind == "heading":
                self.heading(*args)
            elif kind == "para":
                b.para(re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", args[0]))
            elif kind == "list":
                for level, marker, text in args[0]:
                    b.item(text, level, marker)
                if not b.depth:
                    b.space(4)
            elif kind == "code":
                self.code(*args)
            elif kind == "math":
                self.math(args[0])
            elif kind == "table":
                caption = pending_caption
                pending_caption = None
                if not caption and i < len(blocks) and blocks[i][0] == "tablecaption":
                    caption = blocks[i][1]
                    i += 1
                b.table(args[0], args[1], args[2], caption)
            elif kind == "image":
                self.image(*args)
            elif kind == "quote":
                self.quote(args[0])
            elif kind == "hr":
                b.rule()

    def heading(self, level: int, text: str) -> None:
        b = self.book
        index = self.heading_seen
        self.heading_seen += 1
        if index == self.title_heading:
            return
        if b.depth:
            b.para(f"**{text}**")
            return
        out = max(1, min(level - self.chapter_level + 1, self.last_out + 1))
        self.last_out = out
        if out == 1:
            b.chapter(text)
        elif out == 2:
            b.section(text)
        elif out == 3:
            b.sub(text)
        else:
            b.subsub(text)

    def code(self, info: str, source: str) -> None:
        lang, opts = parse_info(info)
        if lang in MATH_LANGS:
            self.math(source)
        else:
            self.book.code(source, lang, **opts)

    def math(self, tex: str) -> None:
        if MATRIX_ENV.search(tex):
            self.book.eq(tex)
        else:
            self.book.eq_flow(mathkit.split_lines(tex) or [tex])

    def image(self, alt: str, src: str, title: str) -> None:
        b = self.book
        if re.match(r"^[a-z]+://", src, re.I) or src.lower().endswith(".svg"):
            b.para(f"*[image skipped (offline/unsupported): {alt or src}]*")
            return
        b.figure((self.base / unquote(src)).resolve(), alt or title)

    def quote(self, inner: list[str]) -> None:
        kind, label, title = "quote", None, ""
        lines = list(inner)
        first = next((k for k, ln in enumerate(lines) if ln.strip()), None)
        if first is not None:
            text = lines[first].strip()
            if (m := CALLOUT.match(text)) and (spec := box_spec(m.group(1))):
                (kind, label), title = spec, m.group(2).strip()
                del lines[first]
            elif (m := BOLD_LEAD.match(text)) and (spec := box_spec(m.group(1))):
                (kind, label), lines[first] = spec, m.group(2)
        with self.book.boxed() as items:
            self.render(parse_blocks(lines))
        self.book.box(kind, title, items, label=label)


def plan_headings(blocks: list[tuple]) -> tuple[int | None, int]:
    levels = [blk[1] for blk in blocks if blk[0] == "heading"]
    if not levels:
        return None, 1
    top = min(levels)
    title_idx = 0 if levels[0] == top and levels.count(top) == 1 and len(levels) > 1 else None
    rest = [lv for k, lv in enumerate(levels) if k != title_idx]
    return title_idx, min(rest) if rest else top


def convert(md_path: Path, pdf_path: Path) -> Path:
    text = md_path.read_text(encoding="utf-8-sig")
    meta, body = parse_front_matter(text)
    blocks = parse_blocks(body.splitlines())
    title_idx, chapter_level = plan_headings(blocks)
    headings = [blk for blk in blocks if blk[0] == "heading"]
    title = meta.get("title") or (headings[title_idx][2] if title_idx is not None else None)
    title = title or md_path.stem.replace("_", " ").replace("-", " ").strip().title()
    author = meta.get("author", "")
    book = Book(pdf_path, re.sub(r"[*_`]", "", title), author)
    book.cover(title, meta.get("subtitle", ""), (author, meta.get("date") or today()))
    book.toc()
    Renderer(book, md_path.parent, title_idx, chapter_level).render(blocks)
    return Path(book.build())
