"""Download the optional Poppins and Caladea fonts into ./fonts (one-time, needs internet)."""
import urllib.request
from pathlib import Path

BASE = "https://github.com/google/fonts/raw/main/"
FILES = {
    "ofl/poppins": ["Poppins-Light", "Poppins-Regular", "Poppins-Medium", "Poppins-SemiBold", "Poppins-Bold"],
    "ofl/caladea": ["Caladea-Regular", "Caladea-Bold", "Caladea-Italic", "Caladea-BoldItalic"],
}


def main() -> None:
    target = Path(__file__).parent / "fonts"
    target.mkdir(exist_ok=True)
    for folder, names in FILES.items():
        for name in names:
            dest = target / f"{name}.ttf"
            if dest.exists():
                continue
            print("downloading", dest.name)
            try:
                urllib.request.urlretrieve(f"{BASE}{folder}/{name}.ttf", dest)
            except OSError as exc:
                print("  failed:", exc)


if __name__ == "__main__":
    main()
