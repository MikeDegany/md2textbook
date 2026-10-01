import argparse
import os
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

from . import __version__
from .parser import convert

MD_SUFFIXES = (".md", ".markdown", ".mdown")


def state_file() -> Path:
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "md2textbook" / "last_dir.txt"


def last_dir() -> str:
    try:
        saved = state_file().read_text(encoding="utf-8").strip()
        if Path(saved).is_dir():
            return saved
    except OSError:
        pass
    docs = Path.home() / "Documents"
    return str(docs if docs.is_dir() else Path.home())


def remember_dir(path: Path) -> None:
    try:
        state_file().parent.mkdir(parents=True, exist_ok=True)
        state_file().write_text(str(path.resolve().parent), encoding="utf-8")
    except OSError:
        pass


def pick_with_tk() -> Path | None:
    import tkinter as tk
    from tkinter import filedialog

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
        chosen = filedialog.askopenfilename(
            parent=root,
            title="Select a Markdown file to convert",
            initialdir=last_dir(),
            filetypes=[("Markdown", "*.md *.markdown *.mdown"), ("All files", "*.*")],
        )
    finally:
        root.destroy()
    return Path(chosen) if chosen else None


def pick_with_helper() -> Path | None:
    title = "Select a Markdown file to convert"
    if zenity := shutil.which("zenity"):
        cmd = [zenity, "--file-selection", f"--title={title}", f"--filename={last_dir()}/",
               "--file-filter=Markdown | *.md *.markdown *.mdown"]
    elif kdialog := shutil.which("kdialog"):
        cmd = [kdialog, "--getopenfilename", last_dir(), "*.md *.markdown *.mdown|Markdown"]
    else:
        return None
    result = subprocess.run(cmd, capture_output=True, text=True)
    return Path(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip() else None


def pick_file() -> Path | None:
    try:
        return pick_with_tk()
    except ImportError:
        pass
    except Exception as exc:  # no display, broken Tk install, ...
        print(f"File dialog unavailable ({exc}).", file=sys.stderr)
    if sys.platform.startswith("linux") and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        picked = pick_with_helper()
        if picked is not None:
            return picked
    if sys.stdin and sys.stdin.isatty():
        answer = input("Path to a Markdown file: ").strip().strip("\"'")
        return Path(answer).expanduser() if answer else None
    print("No file dialog available. Run: md2textbook FILE.md", file=sys.stderr)
    return None


def show_error(message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("md2textbook", message)
        root.destroy()
    except Exception:
        pass


def open_file(path: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        elif shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


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


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="md2textbook",
        description="Convert a Markdown file into a coursebook-style PDF. "
                    "Without a file argument a file chooser opens.",
    )
    ap.add_argument("file", nargs="?", type=Path, help="Markdown file to convert")
    ap.add_argument("-o", "--output", type=Path, help="output PDF path (default: next to the input)")
    ap.add_argument("--no-open", action="store_true", help="do not open the PDF afterwards")
    ap.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    interactive = args.file is None
    source = pick_file() if interactive else args.file
    if source is None:
        return 0
    if not source.is_file():
        message = f"File not found: {source}"
        print(message, file=sys.stderr)
        if interactive:
            show_error(message)
        return 2
    remember_dir(source)
    target = args.output or free_target(source.with_suffix(".pdf"))
    try:
        convert(source, target)
    except Exception as exc:
        traceback.print_exc()
        if interactive:
            show_error(f"Conversion failed:\n\n{exc}")
        return 1
    print(target)
    if not args.no_open:
        open_file(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
