import hashlib
import re
import tempfile
from pathlib import Path
from typing import NamedTuple

import matplotlib

matplotlib.use("Agg")
import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.mathtext import MathTextParser
from PIL import Image

matplotlib.rcParams["mathtext.fontset"] = "cm"

DPI = 420
_parser = MathTextParser("agg")


def _cache_dir() -> Path:
    path = Path(__file__).parent / ".cache" / "math"
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        return Path(tempfile.mkdtemp(prefix="md2pdf-math-"))


CACHE = _cache_dir()


class Rendered(NamedTuple):
    path: str
    width: float
    height: float
    depth: float


_SIMPLE = [
    (r"\\[td]frac", r"\\frac"),
    (r"\\(?:bigg?|Bigg?)[lrm]?(?![a-zA-Z])\s*", ""),
    (r"\\operatorname\*?\{([^}]*)\}", r"\\mathrm{\1}"),
    (r"\\(?:textrm|textbf|textit|textnormal|mbox)\{", r"\\mathrm{"),
    (r"\\(?:boldsymbol|bm)\{", r"\\mathbf{"),
    (r"\\mathds\{", r"\\mathbb{"),
    (r"\\(?:label|tag)\{[^}]*\}", ""),
    (r"\\(?:nonumber|notag|displaystyle|textstyle|limits|nolimits)(?![a-zA-Z])", ""),
    (r"\\[;:]", r"\\ "),
    (r"\\qquad", r"\\quad\\quad"),
    (r"\\lVert|\\rVert|\\Vert", r"\\|"),
    (r"\\lvert|\\rvert|\\vert", "|"),
    (r"\\argmax", r"\\mathrm{arg\\,max}"),
    (r"\\argmin", r"\\mathrm{arg\\,min}"),
    (r"\\top(?![a-zA-Z])", r"\\mathrm{T}"),
    (r"\\mathbbm\{", r"\\mathbb{"),
]


def fix(tex: str) -> str:
    tex = tex.strip()
    for pattern, repl in _SIMPLE:
        tex = re.sub(pattern, repl, tex)
    return re.sub(r"\s+", " ", tex).strip()


def split_lines(tex: str) -> list[str]:
    tex = re.sub(r"\\(?:begin|end)\{(?:aligned|align\*?|gather\*?|split|equation\*?)\}", "", tex)
    parts = re.split(r"\\\\(?:\[[^\]]*\])?", tex)
    return [p.replace("&", " ").strip() for p in parts if p.strip()]


def render(tex: str, size: float = 11.0, color: str = "#111827") -> Rendered | None:
    tex = fix(tex)
    if not tex:
        return None
    key = hashlib.sha1(f"{tex}|{size}|{color}|{DPI}".encode()).hexdigest()[:20]
    png = CACHE / f"{key}.png"
    scale = 72 / DPI
    try:
        _, _, width, height, depth, image = _parser.parse(f"${tex}$", dpi=DPI, prop=FontProperties(size=size))
    except Exception:
        return None
    if not png.exists():
        alpha = np.asarray(image, dtype=np.uint8)
        rgb = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
        rgba = np.zeros((*alpha.shape, 4), dtype=np.uint8)
        rgba[..., :3] = rgb
        rgba[..., 3] = alpha
        Image.fromarray(rgba, "RGBA").save(png, dpi=(DPI, DPI))
    return Rendered(str(png), width * scale, height * scale, depth * scale)
