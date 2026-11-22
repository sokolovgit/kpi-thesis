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
        body = "".join(rf"\begin{{figure}}\label{{fig:{i}}}\end{{figure}}" for i in range(3))
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

    def test_cdots_and_ref_tilde(self):
        code, out = run(doc(r"$b_1 + \ldots + b_5$ і в таблиці \ref{x}."))
        self.assertIn("потрібне \\cdots", out)
        self.assertIn("перед \\ref", out)
        code, out = run(doc(r"$b_1 + \cdots + b_5$ і в таблиці~\ref{x}, (\ref{x})."))
        self.assertNotIn("\\cdots", out)
        self.assertNotIn("перед \\ref", out)

    def test_number_grouping(self):
        code, out = run(doc("Було 4 000 прогонів і 25000 подій, разом 1 000 000."))
        self.assertIn("«4 000»", out)
        self.assertIn("«25000»", out)
        self.assertNotIn("1 000 000", out)
        code, out = run(doc("Було 4000 прогонів, 25~000 подій, шифр 045440, частка 0,12345."))
        self.assertNotIn("розряди", out)
        self.assertNotIn("чотирицифрове", out)

    def test_preamble_is_not_text(self):
        files = {
            "main.tex": "\\documentclass{kpi-thesis}\n\\hyphenpenalty=10000\n"
            "\\kpiset{title = {\\todo{Тема}}}\n\\begin{document}\nТекст.\n\\end{document}\n"
        }
        code, out = run(files)
        self.assertNotIn("розряди", out)
        self.assertIn("заглушок \\todo: 1", out)

    def test_unreferenced_equation_is_a_warning(self):
        code, out = run(doc("\\begin{equation}\\label{eq:a} x = 1 \\end{equation}"))
        self.assertEqual(code, 0, out)
        self.assertIn("на формулу «eq:a»", out)
        code, out = run(
            doc("\\begin{equation}\\label{eq:a} x = 1 \\end{equation} За~\\eqref{eq:a}.")
        )
        self.assertNotIn("eq:a", out)

    def test_mention_order(self):
        figs = r"\begin{figure}\label{fig:a}\end{figure}\begin{figure}\label{fig:b}\end{figure}"
        code, out = run(doc(r"Див. рисунок~\ref{fig:b}, потім рисунок~\ref{fig:a}." + figs))
        self.assertIn("згадано раніше за попередню", out)
        app = r"\appendices\appendix{X}" + figs + r"Рисунки~\ref{fig:b} і~\ref{fig:a}."
        code, out = run(doc(app))
        self.assertNotIn("згадано раніше", out)

    def test_macro_name_with_digit(self):
        files = doc(r"\input{gen}")
        files["gen.tex"] = "\\newcommand\\resultChi2{281}\n\\newcommand{\\okName}{1}\n"
        code, out = run(files)
        self.assertEqual(code, 1)
        self.assertIn("\\resultChi2", out)
        self.assertNotIn("okName", out)

    def test_parentheses(self):
        code, out = run(doc(r"Отже (формула~\eqref{eq:a}) і (\eqref{eq:a})."))
        self.assertIn("((2.8))", out)
        code, out = run(doc(r"За формулою~\eqref{eq:a} (див. рисунок~\ref{x})."))
        self.assertNotIn("дужк", out)
        code, out = run(doc("Стани (помінялися лише $(0, 1)$ і $(1, 0)$) далі."))
        self.assertIn("дужки в дужках", out)
        code, out = run(doc("\\begin{equation}\n f(g(x)) \\\\[2pt]\n\\end{equation}\nТекст (тут)."))
        self.assertNotIn("дужки в дужках", out)


class BiblatexTest(unittest.TestCase):
    BIBFILE = "@book{a,\n  title = {Перше},\n}\n@online{b,\n  title = {Друге},\n}\n"

    def files(self, body, preamble="\\kpisetup{bibliography=biblatex, bib-resource=sources.bib}\n"):
        return {
            "main.tex": "\\documentclass{kpi-thesis}\n" + preamble + "\\begin{document}\n"
            + body + "\n\\printbibliography\n\\end{document}\n",
            "sources.bib": self.BIBFILE,
        }

    def test_cited_keys_from_bib_are_fine(self):
        code, out = run(self.files(r"Текст \parencite{b} і \textcite[с.~5]{a}."))
        self.assertEqual(code, 0, out)

    def test_missing_key_is_error(self):
        code, out = run(self.files(r"Текст \autocite{nope}."))
        self.assertEqual(code, 1)
        self.assertIn("немає у файлі джерел", out)

    def test_uncited_bib_entry_and_order_are_not_errors(self):
        code, out = run(self.files(r"Лише \cite{b}."))
        self.assertEqual(code, 0, out)

    def test_addbibresource_is_read(self):
        code, out = run(self.files(r"\cite{a}", "\\kpisetup{bibliography=biblatex}\n\\addbibresource{sources.bib}\n"))
        self.assertEqual(code, 0, out)

    def test_no_resource_is_error(self):
        code, out = run(self.files(r"\cite{a}", "\\kpisetup{bibliography=biblatex}\n"))
        self.assertEqual(code, 1)
        self.assertIn("без файлу джерел", out)

    def test_alphabetical_thebibliography(self):
        bib = "\n\\begin{thebibliography}{9}\n\\bibitem{a} Шевченко Т. Кобзар.\n\\bibitem{b} Андрухович Ю. Рекреації.\n\\end{thebibliography}\n"
        files = doc(r"\cite{a} \cite{b}" + bib)
        files["main.tex"] = files["main.tex"].replace("}\n\\begin{document}", "}\n\\kpisetup{sources=alphabetical}\n\\begin{document}", 1)
        code, out = run(files)
        self.assertEqual(code, 1)
        self.assertIn("не за алфавітом", out)

    def test_cite_variants_and_multicite(self):
        code, out = run(self.files(r"\Parencite[см.][с.~5]{a} і \cites[1]{b}{nope}."))
        self.assertEqual(code, 1)
        self.assertIn("\\cite{nope}", out)
        self.assertNotIn("\\cite{b}", out)

    def test_several_bib_resources(self):
        files = self.files(r"\cite{a} \cite{c}", "\\kpisetup{bibliography=biblatex, bib-resource={sources.bib,more.bib}}\n")
        files["more.bib"] = "@book(c,\n  title = {Третє},\n)\n"
        code, out = run(files)
        self.assertEqual(code, 0, out)

    def test_bib_with_bom_and_todo(self):
        files = self.files(r"\cite{a}")
        files["sources.bib"] = "\ufeff@book{a,\n  title = {\\todo{Назва}},\n}\n"
        code, out = run(files)
        self.assertEqual(code, 1)
        self.assertNotIn("немає у файлі джерел", out)
        self.assertIn("sources.bib:2", out)
        self.assertIn("заглушок \\todo", out)

    def test_biber_warnings_from_blg(self):
        files = self.files(r"\cite{a}")
        files["build/main.log"] = "This is LuaHBTeX\n"
        files["build/main.blg"] = (
            "[116] Biber.pm:132> WARN - Duplicate entry key 'a' in file 'sources.bib', skipping ...\n"
            "[120] Utils.pm:479> ERROR - BibTeX subsystem: sources.bib, line 3, syntax error\n"
        )
        code, out = run(files)
        self.assertIn("попередження: biber: Duplicate entry key", out)
        self.assertIn("помилка: biber: BibTeX subsystem", out)

    def test_alphabetical_thebibliography_multiline_items(self):
        bib = "\n\\begin{thebibliography}{9}\n\\bibitem{a}\nШевченко Т. Кобзар.\n\\bibitem{b}\nАндрухович Ю. Рекреації.\n\\end{thebibliography}\n"
        files = doc(r"\cite{a} \cite{b}" + bib)
        files["main.tex"] = files["main.tex"].replace("}\n\\begin{document}", "}\n\\kpisetup{sources=alphabetical}\n\\begin{document}", 1)
        code, out = run(files)
        self.assertIn("не за алфавітом", out)

    def test_alphabetical_order_ok_and_cyrillic_before_latin(self):
        self.assertLess(check.sort_key("Ґудзь"), check.sort_key("Дума"))
        self.assertLess(check.sort_key("Їжак"), check.sort_key("Йорданія"))
        self.assertLess(check.sort_key("Яковенко"), check.sort_key("Adams"))


class PdfChecksTest(unittest.TestCase):
    """Checks that read the built PDF, fed with page texts instead of pdftotext."""

    def run_pdf(self, pages, tex="\\documentclass{kpi-thesis}\n"):
        orig = check.pdf_pages_text
        check.pdf_pages_text = lambda pdf: pages
        try:
            return run({"main.tex": tex})
        finally:
            check.pdf_pages_text = orig

    def test_placement(self):
        pages = [
            "як показано на рисунку 1.1 і в таблицях 1.1–1.2",
            "текст",
            "Рисунок 1.1 – Схема\n",
            "Таблиця 1.1 – A\nТаблиця 1.2 – Б\n",
            "Рисунок 2.1 – Рано\nпро рисунок 2.1",
        ]
        code, out = self.run_pdf(pages)
        self.assertIn("Рисунок 1.1 — на с. 3, а вперше згадана на с. 1", out)
        self.assertIn("Таблиця 1.2 — на с. 4", out)
        self.assertNotIn("Рисунок 2.1", out)

    def test_number_lists_count_as_mentions(self):
        pages = [
            "наведено в таблицях 4.2 і 4.3, на рисунках 3.1, 3.2 та 3.3",
            "Таблиця 4.2 – А\nТаблиця 4.3 – Б\nРисунок 3.1 – В\nРисунок 3.2 – Г\nРисунок 3.3 – Д",
        ]
        code, out = self.run_pdf(pages)
        self.assertNotIn("раніше за першу згадку", out)

    def test_short_page_before_section(self):
        pages = ["ЗМІСТ", "1 АНАЛІЗ\nтекст", "      7\nостанній рядок висновків", "2 ПРОЄКТУВАННЯ\nтекст", "Рисунок 2.1 – Схема", "3 РЕАЛІЗАЦІЯ"]
        code, out = self.run_pdf(pages)
        self.assertIn("с. 3: перед новим розділом лише 1", out)
        self.assertNotIn("с. 5", out)

    def test_coursework_chapter_pages(self):
        pages = [
            "ЗМІСТ\nВСТУП ........ 3",
            "ВСТУП",
            "1 АНАЛІЗ ПРЕДМЕТНОЇ ОБЛАСТІ",
            *["текст"] * 17,
            "2 ПРОЄКТУВАННЯ",
            "текст",
            "ВИСНОВКИ",
        ]
        code, out = self.run_pdf(
            pages, "% check: chapter-pages=3-15\n\\documentclass{kpi-thesis}\n"
        )
        self.assertIn("розділ 1, сторінок: 18, за методичкою 3–15", out)
        self.assertIn("розділ 2, сторінок: 2, за методичкою 3–15", out)
        code, out = self.run_pdf(pages)
        self.assertNotIn("розділ 1, сторінок", out)


if __name__ == "__main__":
    unittest.main()


class MoreChecksTest(unittest.TestCase):
    def test_heading_with_period(self):
        code, out = run(doc(r"\section{Аналіз предметної області.}" "\n" r"\subsection{Огляд}"))
        self.assertEqual(code, 1)
        self.assertIn("«Аналіз предметної області.» з крапкою", out)
        self.assertNotIn("«Огляд»", out)

    def test_written_sources(self):
        bib = (
            "\n\\begin{thebibliography}{9}\n"
            "\\bibitem{a} Сайт [Електронний ресурс]. Режим доступу: \\url{https://a.ua}\n"
            "\\bibitem{b} Документація. URL: \\url{https://b.ua} (дата звернення: 01.11.2026).\n"
            "\\bibitem{c} Іванов І. Книга. Київ : Наука.\n"
            "\\end{thebibliography}\n"
        )
        code, out = run(doc(r"\cite{a} \cite{b} \cite{c}" + bib))
        self.assertIn("«a»: «[Електронний ресурс]»", out)
        self.assertIn("«a»: URL без «(дата звернення", out)
        self.assertIn("«a»: перед посиланням — «URL: »", out)
        self.assertNotIn("«b»", out)
        self.assertIn("«c»: немає року видання", out)

    def test_bib_fields(self):
        files = {
            "main.tex": "\\documentclass{kpi-thesis}\n\\kpisetup{bibliography=biblatex, bib-resource=sources.bib}\n"
            "\\begin{document}\n\\cite{a,b,c}\n\\printbibliography\n\\end{document}\n",
            "sources.bib": "@online{a, title={Сайт}, url={https://a.ua}}\n"
            "@online{b, title={Сайт}, url={https://b.ua}, urldate={2026-11-01}}\n"
            "@book{c, title = {Книга {з дужками}}, location={Київ}}\n",
        }
        code, out = run(files)
        self.assertIn("«a»: url без urldate", out)
        self.assertNotIn("«b»", out)
        self.assertIn("sources.bib:3: попередження: «c»: немає date", out)

    def test_abbreviations_order(self):
        body = (
            "\\structural{ПЕРЕЛІК УМОВНИХ ПОЗНАЧЕНЬ}\n\\begin{longtable}{ll}\n"
            "API & -- & інтерфейс.\\\\\nREST & -- & стиль.\\\\\n"
            "СУБД & -- & система.\\\\\nБД & -- & база даних.\\\\\n\\end{longtable}\n"
        )
        code, out = run(doc(body))
        self.assertIn("«БД» має стояти перед «СУБД»", out)
        self.assertNotIn("«REST»", out)

    def test_long_listing_in_note(self):
        code_lines = "\n".join(f"x = {i}" for i in range(90))
        code, out = run(doc("\\begin{Verbatim}\n" + code_lines + "\n\\end{Verbatim}\n\\begin{Verbatim}\nshort\n\\end{Verbatim}"))
        self.assertEqual(out.count("довший за сторінку"), 1)
        self.assertIn("на 90 рядків", out)

    def test_footnotes_per_page(self):
        files = doc("Текст.")
        files["build/main.aux"] = "\\relax\n" + "\\kpi@footnote{3}\n" * 5 + "\\kpi@footnote{4}\n" * 4
        code, out = run(files)
        self.assertIn("с. 3: виносок 5", out)
        self.assertNotIn("с. 4:", out)

    def test_diploma_composition_and_meta(self):
        meta = (
            "\\kpiset{\n  program = {Комп'ютерні науки},\n  student-stamp = {Прізвище І.П.},\n"
            "  advisor-stamp = {Петренко П.П.},\n}\n\\renewcommand\\kpiCalendarRows{%\n"
            "  1 & Вивчення & березень & \\\\ \\hline\n  2 & Розробка & & \\\\ \\hline\n}\n"
        )
        graphics = "\\documentclass{kpi-thesis}\n\\begin{document}\n\\graphicsSheet{ССВ}{a}{b}\n\\diagramPage{ПЛК}{c}{d.png}\n\\end{document}\n"
        files = {"meta.tex": meta, "graphics/graphics.tex": graphics}
        for name in ("title", "explanatory-note"):
            files[f"{name}/{name}.tex"] = "\\documentclass{kpi-thesis}\n\\input{../meta.tex}\n\\begin{document}\nТекст.\n\\end{document}\n"
        code, out = run(files)
        self.assertIn("немає документа specification/specification.tex", out)
        self.assertNotIn("немає документа title/", out)
        self.assertIn("аркушів графічного матеріалу 2", out)
        self.assertIn("код схеми «ПЛК»", out)
        self.assertNotIn("«ССВ»", out)
        self.assertIn("звітом подібності", out)
        self.assertIn("освітня програма «Комп'ютерні науки»", out)
        self.assertIn("не заповнено student-stamp —", out)
        self.assertIn("без термінів 1 рядк.", out)


class UnresolvedPdfTest(PdfChecksTest):
    def test_question_marks_in_pdf(self):
        code, out = self.run_pdf(["Вступ", "на рисунку ?? видно", "Кінець"], "\\documentclass{kpi-thesis}\n\\begin{document}\nx\n\\end{document}\n")
        self.assertIn("«??» у PDF (нерозв'язане посилання), с. 2", out)
