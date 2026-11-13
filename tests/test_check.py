"""Tests for scripts/check.py on small generated works (no TeX needed).

Run: python3 -m unittest discover -s tests
"""

import contextlib
import importlib.util
import io
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("check", ROOT / "scripts" / "check.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

BIB = r"""
\begin{thebibliography}{9}
\bibitem{a} Перше джерело.
\bibitem{b} Друге джерело.
\end{thebibliography}
"""


def run(files):
    """Write files into a temp work dir, run check.py on it; return (exit code, output)."""
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in files.items():
            path = Path(tmp) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(textwrap.dedent(text), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check.main([tmp])
        return code, out.getvalue()


def doc(body):
    return {
        "main.tex": "\\documentclass{kpi-thesis}\n\\begin{document}\n"
        + body
        + "\n\\end{document}\n"
    }


class CheckTest(unittest.TestCase):
    def test_clean_document_has_no_errors(self):
        code, out = run(doc(r"Текст \cite{a}, потім \cite{b}." + BIB))
        self.assertEqual(code, 0, out)
        self.assertIn("помилок: 0", out)

    def test_sources_out_of_order(self):
        code, out = run(doc(r"Спершу \cite{b}, потім \cite{a}." + BIB))
        self.assertEqual(code, 1)
        self.assertIn("не в порядку першої згадки", out)

    def test_uncited_source(self):
        code, out = run(doc(r"Лише \cite{a}." + BIB))
        self.assertIn("на джерело «b» немає посилання", out)

    def test_unreferenced_figure(self):
        code, out = run(doc(r"\begin{figure}\caption{X}\label{fig:x}\end{figure}"))
        self.assertIn("на рисунок «fig:x» немає посилання", out)

    def test_figure_range_counts_as_reference(self):
        body = "".join(
            rf"\begin{{figure}}\label{{fig:{i}}}\end{{figure}}" for i in range(3)
        )
        code, out = run(doc(body + r"Рисунки \ref{fig:0}--\ref{fig:2}."))
        self.assertNotIn("немає посилання", out)

    def test_de_with_colon(self):
        code, out = run(doc("$$x = y$$\nде: x -- щось"))
        self.assertIn("«де:»", out)

    def test_de_with_colon_inside_code_is_ignored(self):
        for env in ("lstlisting", "Verbatim", "minted"):
            extra = "{python}" if env == "minted" else ""
            code, out = run(doc(f"\\begin{{{env}}}{extra}\nде: x\n\\end{{{env}}}"))
            self.assertNotIn("«де:»", out, env)

    def test_em_dash_unicode_and_triple_hyphen(self):
        for text in ("Текст — тут.", "Текст --- тут."):
            code, out = run(doc(text))
            self.assertIn("довге тире", out, text)
        code, out = run(doc("Текст -- тут."))
        self.assertNotIn("довге тире", out)

    def test_decimal_point(self):
        code, out = run(doc(r"Точність 62.1~\% на тестах."))
        self.assertIn("«62.1", out)
        code, out = run(doc(r"У розділі 1.2 описано."))
        self.assertNotIn("десяткових", out)

    def test_todo_counted(self):
        code, out = run(doc(r"\todo{написати} і \todo{ще}"))
        self.assertEqual(code, 1)
        self.assertIn("заглушок \\todo: 1", out)

    def test_input_with_dot_in_name(self):
        files = doc(r"\input{chapters/1.2-x}")
        files["chapters/1.2-x.tex"] = "Текст — тут.\n"
        code, out = run(files)
        self.assertIn("chapters/1.2-x.tex:1", out)


if __name__ == "__main__":
    unittest.main()
