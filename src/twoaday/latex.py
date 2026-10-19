from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def slug(text: str, n: int = 40) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")[:n]


def page_count(pdf: Path) -> int:
    """Pages in a PDF built by compile_pdf (read from the pdflatex log saved beside it)."""
    log = pdf.with_suffix(".pages")
    if log.exists():
        return int(log.read_text().strip() or 0)
    data = pdf.read_bytes()
    m = re.findall(rb"/Count\s+(\d+)", data)
    return max((int(x) for x in m), default=0)


def compile_pdf(tex: str, out_pdf: Path) -> Path:
    if not shutil.which("pdflatex"):
        raise RuntimeError("pdflatex not found; install texlive (see README) or use the Docker image")
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "cv.tex"
        src.write_text(tex, encoding="utf-8")
        for _ in range(2):
            proc = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "cv.tex"],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=120,
            )
        built = Path(tmp) / "cv.pdf"
        if proc.returncode != 0 or not built.exists():
            tail = "\n".join(proc.stdout.splitlines()[-25:])
            raise RuntimeError(f"pdflatex failed:\n{tail}")
        shutil.copy(built, out_pdf)
        m = re.search(r"Output written on cv\.pdf \((\d+) pages?", proc.stdout)
        if m:
            out_pdf.with_suffix(".pages").write_text(m.group(1))
    return out_pdf
