# MDtoPDF

Turn a Markdown file into a coursebook-style PDF: gradient cover, table of contents, chapter banners, colored boxes, publication-quality equations and syntax-highlighted code. Runs fully offline; no network or AI involved.

## Setup

```powershell
pip install -r requirements.txt
python setup_fonts.py   # optional, one-time: Poppins + Caladea
```

Without the optional fonts the converter falls back to Segoe UI, Georgia and DejaVu.

## Usage

Double-click `MDtoPDF.bat` (or run `python md2pdf.py`), pick a `.md` file in the dialog, and the PDF is written next to it and opened. You can also pass a path: `python md2pdf.py notes.md`.

## Markdown support

| Markdown | Result |
|---|---|
| Front matter `title`, `subtitle`, `author`, `date` | Cover page |
| Single `# Title`, then `##` / `###` / `####` | Title on the cover; chapters, sections, subsections |
| Several `#` headings | Each `#` is a chapter |
| `$x^2$` and `$$ ... $$` (or a `math` fence) | Inline math and numbered display equations |
| Fenced code, ` ```python title="Loss" ` | Highlighted listing, line numbers, wrapping |
| Pipe tables, optional `Table: caption` line | Zebra tables with repeating header |
| `![caption](img.png)` | Numbered figure |
| `> [!DEFINITION] Title` | Colored box |
| `> **Example:** text` | Same, shorthand form |
| Plain `>` quote | Quiet unlabeled note |

Box kinds: `DEFINITION`, `EXAMPLE`, `INSIGHT`, `WARNING`, `RECAP`, `OBJECTIVE`, `CODE`, `IDEA`, `REVIEW`, `BRIEF`, `MATH`, `NOTE`, plus aliases such as `TIP`, `CAUTION`, `THEOREM`, `PROOF`, `SUMMARY`.

Code fence options: `title="..."`, `nonumbers`, `start=N`.

Equations use matplotlib's mathtext, so a few LaTeX constructs (matrices, `\substack`, ...) are unsupported and are shown as source instead. Remote and SVG images are skipped.

## Layout

| File | Role |
|---|---|
| `md2pdf.py` | File dialog and entry point |
| `mdparser.py` | Markdown parsing and mapping onto the book |
| `build.py` | ReportLab book builder (pages, boxes, code, tables) |
| `theme.py` | Fonts, palette, paragraph styles, inline markup |
| `mathkit.py` | LaTeX to PNG rendering with cache |
