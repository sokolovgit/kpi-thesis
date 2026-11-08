#!/usr/bin/env python3
"""Normcontrol checks for a kpi-thesis work (diploma package or a single coursework).

Usage: check.py [--stats] <work-dir>
Exit code 1 when any error is found; warnings don't fail.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

ERR, WARN = "error", "warning"
issues = []
todos = {}  # file -> line numbers with \todo


def report(level, where, msg):
    issues.append((level, where, msg))


def strip_comments(text):
    return re.sub(r"(?<!\\)%.*", "", text)


def load(path, seen=None):
    """Source of a .tex file with \\input/\\include expanded, as (file, line, text) rows."""
    seen = seen or set()
    path = path.resolve()
    if path in seen or not path.exists():
        return []
    seen.add(path)
    rows = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = strip_comments(raw)
        for m in re.finditer(r"\\(?:input|include)\{([^}]+)\}", line):
            child = path.parent / m.group(1)
            if child.suffix != ".tex":
                child = child.with_suffix(".tex")
            rows.extend(load(child, seen))
        rows.append((path, n, line))
    return rows


def find_documents(root):
    docs = []
    for tex in sorted(root.glob("*/*.tex")):
        if tex.stem == tex.parent.name and "\\documentclass" in tex.read_text(
            encoding="utf-8"
        ):
            docs.append(tex)
    for tex in sorted(root.glob("*.tex")):
        if "\\documentclass" in tex.read_text(encoding="utf-8"):
            docs.append(tex)
    return docs


def loc(row, root):
    path, n, _ = row
    try:
        path = path.relative_to(root)
    except ValueError:
        pass
    return f"{path}:{n}"


def check_bibliography(rows, root):
    cites, bib = [], []
    in_bib = False
    for row in rows:
        text = row[2]
        if "\\begin{thebibliography}" in text:
            in_bib = True
        for m in re.finditer(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}", text):
            bib.append((m.group(1).strip(), row))
        if not in_bib:
            for m in re.finditer(r"\\cite[pt]?\*?(?:\[[^\]]*\])?\{([^}]+)\}", text):
                for key in m.group(1).split(","):
                    key = key.strip()
                    if key not in [c for c, _ in cites]:
                        cites.append((key, row))
    if not bib:
        return
    bib_keys = [k for k, _ in bib]
    cite_keys = [k for k, _ in cites]
    for key, row in cites:
        if key not in bib_keys:
            report(ERR, loc(row, root), f"\\cite{{{key}}} has no \\bibitem")
    for key, row in bib:
        if key not in cite_keys:
            report(
                ERR,
                loc(row, root),
                f"source «{key}» is never cited (every source must be cited)",
            )
    order = [k for k in bib_keys if k in cite_keys]
    expected = [k for k in cite_keys if k in bib_keys]
    if order != expected:
        for i, (a, b) in enumerate(zip(order, expected)):
            if a != b:
                row = dict(bib)[a]
                report(
                    ERR,
                    loc(row, root),
                    f"sources not in order of first citation: position {i + 1} is «{a}», "
                    f"but «{b}» is cited first",
                )
                break


def check_refs(rows, root):
    labels = []  # (key, row, kind)
    env_stack = []
    for row in rows:
        text = row[2]
        for m in re.finditer(r"\\(begin|end)\{([^}]+)\}", text):
            if m.group(1) == "begin":
                env_stack.append(m.group(2))
            elif env_stack and env_stack[-1] == m.group(2):
                env_stack.pop()
        for m in re.finditer(r"\\label\{([^}]+)\}", text):
            env = next(
                (
                    e
                    for e in reversed(env_stack)
                    if e in ("figure", "table", "longtable")
                ),
                None,
            )
            kind = {"figure": "figure", "table": "table", "longtable": "table"}.get(env)
            if kind is None and m.group(1).startswith(("fig:", "tab:")):
                kind = "figure" if m.group(1).startswith("fig:") else "table"
            if kind:
                labels.append((m.group(1), row, kind))
    body = "\n".join(r[2] for r in rows)
    refs = set(re.findall(r"\\(?:auto|c|C|page)?ref\{([^}]+)\}", body))
    order = [k for k, _, _ in labels]
    # «таблиці 2.1–2.16»: a range covers every label defined between its ends
    for a, b in re.findall(r"\\ref\{([^}]+)\}\s*(?:--|–|—|-)\s*\\ref\{([^}]+)\}", body):
        if a in order and b in order:
            i, j = sorted((order.index(a), order.index(b)))
            refs.update(order[i : j + 1])
    for key, row, kind in labels:
        if key not in refs:
            word = "рисунок" if kind == "figure" else "таблицю"
            report(
                ERR,
                loc(row, root),
                f"{kind} «{key}» is never referenced (потрібне посилання на {word})",
            )


def check_text(rows, root, is_note):
    in_bib = in_code = False
    sections = []
    for row in rows:
        text = row[2]
        if "\\begin{thebibliography}" in text:
            in_bib = True
        if re.search(r"\\begin\{(lstlisting|verbatim)\}", text):
            in_code = True
        if re.search(r"\\end\{(lstlisting|verbatim)\}", text):
            in_code = False
            continue
        if in_code:
            continue
        for m in re.finditer(r"\\begin\{(figure|table)\}\[([^\]]*)\]", text):
            if "H" not in m.group(2):
                report(
                    WARN,
                    loc(row, root),
                    f"{m.group(1)}[{m.group(2)}] may float away from its text; drop the option (H is the default)",
                )
        if re.search(r"(^|[^\w])[Дд]е\s*:", text) and not in_bib:
            report(
                ERR,
                loc(row, root),
                "«де:» — the explanation after a formula starts with «де» without a colon (use \\begin{where})",
            )
        if "—" in text and not in_bib:
            report(
                WARN, loc(row, root), "em dash «—»: use the en dash «–» (`--` in LaTeX)"
            )
        if not in_bib:
            plain = re.sub(
                r"\\(?:url|path|href|ref|label|cite|includegraphics|input|lstinputlisting|texttt|codefile)\*?(\[[^\]]*\])?\{[^}]*\}",
                " ",
                text,
            )
            plain = re.sub(r"\$[^$]*\$", " ", plain)
            # Only quantities (percent or a unit after the number): «1.2» alone is usually a section/figure/ID.
            for m in re.finditer(r"(?<![\w.\\-])(\d+)\.(\d+)(?=(?:\s|~|\\,)*(?:\\?%|(?:с|мс|хв|год|кг|т|г|грн|USD|ГБ|МБ|КБ|Гб|Мб|км|м|см|мм|пікс|кадр\w*|раз\w*)(?![\w]))|(?:\s|~)+(?:відсот\w*|секунд\w*|хвилин\w*|разу|рази))", plain):
                report(WARN, loc(row, root), f"«{m.group(0)}» — decimal separator in Ukrainian text is a comma ({m.group(1)},{m.group(2)})")
        if re.search(r"\\todo\{", text):
            todos.setdefault(row[0], []).append(row[1])
        if is_note:
            sec = re.search(r"\\section\{([^}]+)\}", text)
            if sec:
                sections.append([sec.group(1), row, False])
            if re.search(r"\\subsection\*?\{Висновки до розділу\}", text) and sections:
                sections[-1][2] = True
    for title, row, has in sections:
        if not has:
            report(
                WARN, loc(row, root), f"chapter «{title}» has no «Висновки до розділу»"
            )


def check_log(doc, root):
    log = doc.with_suffix(".log")
    if not log.exists():
        log = doc.parent / "build" / log.name
    if not log.exists():
        report(
            WARN,
            str(doc.relative_to(root)),
            "not built yet (no .log) — run `just build`",
        )
        return
    text = log.read_text(encoding="utf-8", errors="replace")
    over = [
        float(x) for x in re.findall(r"Overfull \\hbox \(([\d.]+)pt too wide\)", text)
    ]
    big = [x for x in over if x > 1.0]
    if big:
        report(
            WARN,
            str(log.relative_to(root)),
            f"{len(big)} line(s) stick out past the margin, worst {max(big):.1f}pt (search the log for «Overfull»)",
        )
    for key in sorted(set(re.findall(r"Reference `([^']+)' on page", text))):
        report(ERR, str(log.relative_to(root)), f"undefined reference «{key}»")
    for key in sorted(set(re.findall(r"Citation `([^']+)' on page", text))):
        report(ERR, str(log.relative_to(root)), f"undefined citation «{key}»")
    for name in sorted(set(re.findall(r"File `([^']+)' not found", text))):
        report(ERR, str(log.relative_to(root)), f"missing file «{name}»")
    if "Rerun to get" in text or "Label(s) may have changed" in text:
        report(
            WARN,
            str(log.relative_to(root)),
            "needs another LaTeX run (references may be stale)",
        )


def built_pdf(root, doc):
    """<doc>/build/<doc>.pdf, or <doc>/<doc>.pdf for works built in place."""
    pdf = root / doc / "build" / f"{doc}.pdf"
    return pdf if pdf.exists() else root / doc / f"{doc}.pdf"


def pdf_pages_text(pdf):
    if not shutil.which("pdftotext") or not pdf.exists():
        return None
    out = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8", str(pdf), "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return out.stdout.split("\f") if out.returncode == 0 else None


def check_annotations(root):
    pages = pdf_pages_text(built_pdf(root, "title"))
    if not pages:
        return
    pages = [p for p in pages if p.strip()]
    if len(pages) != 6:
        report(WARN, "title/build/title.pdf",
               f"{len(pages)} pages; expected 6 (title 1, assignment 2, annotations 2, Відомість 1) — "
               "shorten the assignment items so it fits one sheet printed on both sides")
    for page in pages:
        for head, kw in (("АНОТАЦІЯ", "КЛЮЧОВІ СЛОВА"), ("ABSTRACT", "KEYWORDS")):
            if re.search(rf"^\s*{head}\s*$", page, re.M):
                body = page.split(head, 1)[1].split(kw, 1)[0]
                body = re.sub(r"-\n\s*", "", body)
                body = re.sub(r"\s+", " ", body).strip()
                if len(body) > 1000:
                    report(
                        ERR,
                        "title/build/title.pdf",
                        f"{head}: {len(body)} characters, the limit is 1000 (guide §5.3)",
                    )
                if "??" in body:
                    report(
                        WARN,
                        "title/build/title.pdf",
                        f"{head}: «??» counts — build the other documents first (`just all`)",
                    )
                keywords = page.split(kw, 1)[1] if kw in page else ""
                n = len(
                    [
                        k
                        for k in re.sub(r"\s+", " ", keywords).strip(" :.").split(",")
                        if k.strip()
                    ]
                )
                if kw in page and not 3 <= n <= 10:
                    report(
                        WARN, "title/build/title.pdf", f"{kw}: {n} keywords, expected 3–10"
                    )


def check_volume(root):
    pages = pdf_pages_text(built_pdf(root, "explanatory-note"))
    if not pages:
        return

    def first(pattern, start=0):
        for i in range(start, len(pages)):
            if re.search(pattern, pages[i], re.M):
                return i
        return None

    toc_end = first(r"^\s*ВСТУП\s*\.{3,}") or 0
    intro = first(r"^\s*ВСТУП\s*$", toc_end + 1)
    ch1 = first(r"^\s*1\s+[А-ЯІЇЄҐ’' ]{6,}\s*$", (intro or toc_end) + 1)
    ch2 = first(r"^\s*2\s+[А-ЯІЇЄҐ’' ]{6,}\s*$", (ch1 or 0) + 1)
    concl = first(r"^\s*ВИСНОВКИ\s*$", (ch1 or 0) + 1)
    if None in (intro, ch1, concl):
        return
    intro_pages, main_pages = ch1 - intro, concl - ch1
    if intro_pages > 4:
        report(WARN, "explanatory-note/build/explanatory-note.pdf", f"ВСТУП takes {intro_pages} pages, the limit is 4")
    if not 60 <= main_pages <= 70:
        report(
            WARN,
            "explanatory-note/build/explanatory-note.pdf",
            f"main part is {main_pages} pages, the guide recommends 60–70",
        )
    if ch2 and main_pages and (ch2 - ch1) / main_pages > 0.30:
        report(
            WARN,
            "explanatory-note/build/explanatory-note.pdf",
            f"chapter 1 is {100 * (ch2 - ch1) // main_pages}% of the main part, the limit is 30%",
        )


def stats(root):
    for f in sorted([*root.glob("*.kpistats"), *root.glob("*/*.kpistats"), *root.glob("*/build/*.kpistats"), *root.glob("build/*.kpistats")]):
        vals = dict(re.findall(r"\\kpistat\{(\w+)\}\{(\d+)\}", f.read_text()))
        print(f"{f.stem:17} " + "  ".join(f"{k} {v}" for k, v in vals.items()))


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8")
    show_stats = "--stats" in argv
    args = [a for a in argv if not a.startswith("--")]
    root = Path(args[0] if args else ".").resolve()
    if show_stats:
        stats(root)
        return 0
    docs = find_documents(root)
    if not docs:
        print(f"no LaTeX documents found in {root}")
        return 1
    for doc in docs:
        rows = load(doc)
        is_note = doc.stem in ("explanatory-note", "main")
        check_bibliography(rows, root)
        check_refs(rows, root)
        check_text(rows, root, is_note)
        check_log(doc, root)
        if (
            "meta.tex" not in "".join(r[2] for r in rows if "\\input" in r[2])
            and (root / "meta.tex").exists()
        ):
            report(
                WARN,
                str(doc.relative_to(root)),
                "doesn't \\input{../meta.tex} — codes and names may drift",
            )
        for row in rows:
            if row[0].name != "meta.tex" and re.search(r"КПІ\.[А-ЯІ]{2}-\d", row[2]):
                report(
                    WARN,
                    loc(row, root),
                    "hard-coded document code; use \\kpiCode{...} from meta.tex",
                )
    check_annotations(root)
    check_volume(root)
    for path, lines in todos.items():
        lines = sorted(set(lines))
        where = loc((path, lines[0], ""), root)
        more = f" (lines {', '.join(map(str, lines))})" if len(lines) > 1 else ""
        report(ERR, where, f"{len(lines)} \\todo placeholder(s) left{more}")
    seen = set()
    issues[:] = [i for i in issues if not (i in seen or seen.add(i))]

    errors = [i for i in issues if i[0] == ERR]
    for level, where, msg in issues:
        print(f"{where}: {level}: {msg}")
    print(
        f"\n{len(errors)} error(s), {len(issues) - len(errors)} warning(s) in {len(docs)} document(s)"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
