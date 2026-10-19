import shutil

import pytest

from twoaday.latex import compile_pdf, page_count

DOC = r"""\documentclass{article}\begin{document}%s\end{document}"""


@pytest.mark.skipif(not shutil.which("pdflatex"), reason="pdflatex not installed")
@pytest.mark.parametrize("body,pages", [("Hello", 1), (r"One\newpage Two", 2)])
def test_page_count(tmp_path, body, pages):
    assert page_count(compile_pdf(DOC % body, tmp_path / "x.pdf")) == pages
