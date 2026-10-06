# Markdown to Textbook PDF

![Version](https://img.shields.io/visual-studio-marketplace/v/mikedegany.md2textbook) ![Installs](https://img.shields.io/visual-studio-marketplace/i/mikedegany.md2textbook)

Turn long Markdown files (AI-written reports, notes, documentation) into a clean textbook-style PDF with one click, straight from VS Code. The PDF is saved next to the Markdown file, ready to open in whichever PDF reader you like, so you can highlight, comment and search it there.

The conversion is done by [md2textbook](https://github.com/MikeDegany/md2textbook), which runs fully offline: gradient cover, table of contents, colored boxes for callouts, numbered equations, highlighted code, tables and figures.

![Cover, chapter opener and equations](https://raw.githubusercontent.com/MikeDegany/md2textbook/main/docs/images/overview-1.png)

## Quick start

1. Install this extension: search for **Markdown to Textbook PDF** in the Extensions view (`Ctrl+Shift+X`), or run `code --install-extension mikedegany.md2textbook`. Cursor, VSCodium and similar editors can get it from [Open VSX](https://open-vsx.org/extension/mikedegany/md2textbook).
2. Open a `.md` file and click the **PDF icon** at the top right of the editor, or press `Ctrl+Alt+P` (`Cmd+Alt+P` on a Mac).
3. If md2textbook is not installed yet, the extension offers to install it for you (it needs Python 3.10 or newer).
4. The PDF is saved next to the Markdown file, with the same name and a `.pdf` ending. Nothing is opened for you; if you want that, see `md2textbook.openWith` below.

You can also right-click a Markdown file, in the editor or in the Explorer, and choose **Convert Markdown to PDF**.

## Commands

| Command | What it does |
|---|---|
| **md2textbook: Convert Markdown to PDF** | Converts the open (or right-clicked) Markdown file and saves the PDF next to it |
| **md2textbook: Open Generated PDF** | Opens the existing PDF in your default reader (or a VS Code tab) without converting again |
| **md2textbook: Check Installation** | Shows which md2textbook it found, or offers to install it |

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `md2textbook.openWith` | `none` | `none` only saves the PDF. `external` also opens it in your default PDF reader, `vscode` opens a tab in VS Code (needs a PDF viewer extension) |
| `md2textbook.convertOnSave` | `false` | Convert every Markdown file when you save it |
| `md2textbook.openAfterAutoConvert` | `false` | Also open the PDF after a convert-on-save conversion (only if `openWith` is not `none`) |
| `md2textbook.command` | `md2textbook` | The command to run. If it is not found, `python -m md2textbook` and `py -m md2textbook` are tried too |

## If the PDF is open in your reader

Some readers, Adobe on Windows in particular, lock a PDF while it is open, so it cannot be replaced. The extension notices this and asks you to close the PDF and press **Retry**. With convert-on-save it quietly skips the update instead and says so in the status bar.

## Remote windows (SSH, containers, WSL)

The extension runs where your files are, so md2textbook must be installed on that machine, and the PDF is created there, next to the Markdown file. To get it onto your own computer, right-click the PDF in the Explorer and choose **Download**.

## Troubleshooting

- **"md2textbook is not installed":** accept the install offer, or run `python -m pip install --user md2textbook` yourself, then run **md2textbook: Check Installation**.
- **Nothing happens or it fails:** open **View > Output** and pick **md2textbook** to see the full message.
- **Wrong or old version:** `python -m pip install --upgrade --no-cache-dir md2textbook`.
- **Python is missing:** install it from [python.org](https://www.python.org/downloads/) and tick **Add python.exe to PATH**.

## Privacy

Nothing leaves your computer. The extension only runs the md2textbook program installed on your machine, on the files you choose.

## Links

- [md2textbook on GitHub](https://github.com/MikeDegany/md2textbook) and [PyPI](https://pypi.org/project/md2textbook/)
- [Report a problem](https://github.com/MikeDegany/md2textbook/issues/new/choose)

MIT licensed.
