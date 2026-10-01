from pathlib import Path

import pytest

from md2textbook import convert
from md2textbook.mathkit import fix, split_lines
from md2textbook.parser import parse_blocks, parse_front_matter, plan_headings

EXAMPLES = Path(__file__).parent.parent / "examples"


def test_front_matter():
    meta, body = parse_front_matter("---\ntitle: Hello\nauthor: Me\n---\n# Body\n")
    assert meta == {"title": "Hello", "author": "Me"}
    assert body.startswith("# Body")


def test_block_kinds():
    text = "# T\n\npara\n\n- a\n- b\n\n| x | y |\n|---|---|\n| 1 | 2 |\n\n```py\nprint(1)\n```\n\n$$a+b$$\n"
    kinds = [block[0] for block in parse_blocks(text.splitlines())]
    assert kinds == ["heading", "para", "list", "table", "code", "math"]


def test_math_fixups():
    assert fix(r"\tfrac{1}{2} \big( x \big)") == r"\frac{1}{2} ( x )"
    assert split_lines("a &= b \\\\ c &= d") == ["a  = b", "c  = d"]


def test_sample_converts(tmp_path):
    out = convert(EXAMPLES / "sample.md", tmp_path / "sample.pdf")
    data = out.read_bytes()
    assert data.startswith(b"%PDF") and len(data) > 20_000


def test_showcase_converts(tmp_path):
    out = convert(EXAMPLES / "showcase.md", tmp_path / "showcase.pdf")
    assert out.stat().st_size > 50_000


def test_title_heading_matching_front_matter_is_not_a_chapter():
    text = "---\ntitle: My Book\n---\n# My Book\n\n# One\n\n## A\n\n# Two\n"
    blocks = parse_blocks(parse_front_matter(text)[1].splitlines())
    title_idx, chapter_level = plan_headings(blocks, "My Book")
    assert title_idx == 0 and chapter_level == 1


def test_short_latex_aliases():
    assert fix(r"a \le b \ge c \left( x \right)") == r"a \leq b \geq c \left( x \right)"


def test_degenerate_inputs(tmp_path):
    for name, text in {"empty": "", "plain": "just text", "bad_math": "$$\\nope{x}$$\n\n$\\also{y}$"}.items():
        src = tmp_path / f"{name}.md"
        src.write_text(text, encoding="utf-8")
        assert convert(src, tmp_path / f"{name}.pdf").exists()


@pytest.mark.parametrize("flag", [["--version"], ["--help"]])
def test_cli_flags(flag, capsys):
    from md2textbook.cli import main

    with pytest.raises(SystemExit) as exc:
        main(flag)
    assert exc.value.code == 0


def test_missing_and_corrupt_images_do_not_abort(tmp_path, capsys):
    (tmp_path / "bad.png").write_bytes(b"not an image")
    src = tmp_path / "doc.md"
    src.write_text("# T\n\n## S\n\n![a](missing.png)\n\n![b](bad.png)\n", encoding="utf-8")
    assert convert(src, tmp_path / "doc.pdf").exists()
    err = capsys.readouterr().err
    assert "missing.png (not found)" in err and "bad.png (unreadable" in err


def test_internal_links_resolve_or_degrade(tmp_path):
    src = tmp_path / "doc.md"
    src.write_text(
        "# Title\n\n# 1 — Names: CoRL\n\n## Part\n\n"
        "See [names](#1--names-corl), [part](#part) and [gone](#no-such-heading).\n\n"
        "> [!NOTE]\n> ## Heading inside a box\n> text\n\n# Second\n",
        encoding="utf-8",
    )
    out = convert(src, tmp_path / "doc.pdf")
    import pymupdf

    kinds = [link["kind"] for page in pymupdf.open(out) for link in page.get_links()]
    assert kinds.count(pymupdf.LINK_GOTO) >= 2  # the two resolvable links, plus TOC entries


def outline_titles(pdf: Path) -> list[str]:
    import pymupdf

    return [entry[1] for entry in pymupdf.open(pdf).get_toc()]


def test_manual_heading_numbers_are_stripped(tmp_path):
    src = tmp_path / "doc.md"
    src.write_text("# Book\n\n# 3. Dates\n\n## 3.1 Detail\n\n## 2) Other\n\n# Second\n", encoding="utf-8")
    titles = outline_titles(convert(src, tmp_path / "doc.pdf"))
    assert titles[0].endswith("Dates") and "3." not in titles[0]
    assert all("3.1 Detail" not in t and "2)" not in t for t in titles)


def test_emoji_use_fallback_font():
    from md2textbook import theme

    theme.register_fonts()
    assert '<font name="Emoji">' in theme.wrap_missing_glyphs("Trophy 🏆 time", "Body")
    assert "️" not in theme.wrap_missing_glyphs("tag \U0001f3f7️", "Body")


def test_headerless_table_and_wide_content(tmp_path):
    src = tmp_path / "doc.md"
    src.write_text(
        "# T\n\n## S\n\n| | |\n|---|---|\n| Website | https://example.com/a/very/long/path |\n| Date | Nov 12 |\n\n"
        "| Notification | Camera-ready |\n|---|---|\n| Oct 1 | Nov 5 |\n",
        encoding="utf-8",
    )
    assert convert(src, tmp_path / "doc.pdf").exists()
