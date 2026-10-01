import ctypes
import os
import sys
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox

from mdparser import convert

STATE = Path(os.environ.get("APPDATA", Path.home())) / "md2pdf" / "last_dir.txt"


def last_dir() -> str:
    try:
        saved = STATE.read_text(encoding="utf-8").strip()
        if Path(saved).is_dir():
            return saved
    except OSError:
        pass
    return str(Path.home() / "Documents")


def remember_dir(path: Path) -> None:
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(str(path.parent), encoding="utf-8")
    except OSError:
        pass


def pick_file() -> Path | None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    chosen = filedialog.askopenfilename(
        parent=root,
        title="Select a Markdown file to convert",
        initialdir=last_dir(),
        filetypes=[("Markdown", "*.md *.markdown *.mdown"), ("All files", "*.*")],
    )
    root.destroy()
    return Path(chosen) if chosen else None


def free_target(path: Path) -> Path:
    candidate = path
    for n in range(2, 100):
        if not candidate.exists():
            return candidate
        try:
            candidate.open("ab").close()
            return candidate
        except PermissionError:
            candidate = path.with_name(f"{path.stem} ({n}){path.suffix}")
    return candidate


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else pick_file()
    if source is None:
        return 0
    remember_dir(source)
    target = free_target(source.with_suffix(".pdf"))
    try:
        convert(source, target)
    except Exception as exc:
        traceback.print_exc()
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Markdown to PDF", f"Conversion failed:\n\n{exc}")
        root.destroy()
        return 1
    os.startfile(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
