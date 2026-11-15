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

ERR, WARN = "помилка", "попередження"
CODE_ENVS = r"(?:lstlisting|verbatim|Verbatim|BVerbatim|LVerbatim|minted)\*?"
issues = []
todos = {}  # file -> line numbers with \todo


def report(level, where, msg):
    issues.append((level, where, msg))


def strip_comments(text):
    return re.sub(r"(?<!\\)%.*", "", text)


def resolve_input(parent, name):
    child = parent / name
    if child.is_file():
        return child
    return child if name.endswith(".tex") else parent / f"{name}.tex"


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
            rows.extend(load(resolve_input(path.parent, m.group(1).strip()), seen))
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
            report(
                ERR,
                loc(row, root),
                f"\\cite{{{key}}} немає у списку джерел (\\bibitem)",
            )
    for key, row in bib:
        if key not in cite_keys:
            report(
                ERR,
                loc(row, root),
                f"на джерело «{key}» немає посилання в тексті (кожне джерело має бути процитоване)",
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
                    f"джерела не в порядку першої згадки: на місці {i + 1} стоїть «{a}», "
                    f"а першим згадано «{b}»",
                )
                break


KINDS = {
    "figure": "figure",
    "table": "table",
    "longtable": "table",
    "kpitable": "table",
    **{e: "equation" for e in ("equation", "align", "gather", "multline", "eqnarray")},
}
WORDS = {"figure": ("рисунок", "рисунка"), "table": ("таблицю", "таблиці"), "equation": ("формулу", "формули")}


def check_refs(rows, root):
    labels = []  # (key, row, kind, offset in body); appendix objects are left out of the order check
    env_stack = []
    offset = 0
    in_appendix = False
    for row in rows:
        text = row[2]
        in_appendix = in_appendix or "\\appendices" in text
        for m in re.finditer(r"\\(begin|end|label)\{([^}]+)\}", text):
            if m.group(1) == "begin":
                env_stack.append(m.group(2).rstrip("*"))
                continue
            if m.group(1) == "end":
                if env_stack and env_stack[-1] == m.group(2).rstrip("*"):
                    env_stack.pop()
                continue
            pos, m = m.start(), re.match(r"\\label\{([^}]+)\}", m.group(0))
            env = next((e for e in reversed(env_stack) if e in KINDS), None)
            kind = KINDS.get(env)
            if kind is None and m.group(1).startswith(("fig:", "tab:")):
                kind = "figure" if m.group(1).startswith("fig:") else "table"
            if kind:
                labels.append((m.group(1), row, kind if not in_appendix else f"{kind}-appendix", offset + pos))
        offset += len(text) + 1
    body = "\n".join(r[2] for r in rows)
    first = {}  # key -> offset of its first reference
    for m in re.finditer(r"\\(?:auto|c|C|page|eq)?ref\{([^}]+)\}", body):
        first.setdefault(m.group(1), m.start())
    order = [k for k, *_ in labels]
    # «таблиці 2.1–2.16»: a range covers every label defined between its ends
    for m in re.finditer(r"\\ref\{([^}]+)\}\s*(?:--|–|—|-)\s*\\ref\{([^}]+)\}", body):
        a, b = m.groups()
        if a in order and b in order:
            i, j = sorted((order.index(a), order.index(b)))
            for k in order[i : j + 1]:
                first.setdefault(k, m.start())
    for key, row, kind, _ in labels:
        kind = kind.removesuffix("-appendix")
        if key in first:
            continue
        if kind == "equation":
            report(WARN, loc(row, root),
                   f"на формулу «{key}» немає посилання — нумерують лише ті, на які посилаються (equation*)")
        else:
            report(ERR, loc(row, root), f"на {WORDS[kind][0]} «{key}» немає посилання в тексті")
    for kind in ("figure", "table"):
        seen = [(k, r) for k, r, kd, _ in labels if kd == kind and k in first]
        for (a, _), (b, row) in zip(seen, seen[1:]):
            if first[b] < first[a]:
                report(WARN, loc(row, root),
                       f"{WORDS[kind][0]} «{b}» згадано раніше за попередню «{a}» — нумерація має йти за першою згадкою")
                break


def check_text(rows, root, is_note):
    in_bib = in_code = False
    in_body = not any("\\begin{document}" in r[2] for r in rows)
    sections = []
    for row in rows:
        text = row[2]
        if "\\begin{thebibliography}" in text:
            in_bib = True
        if re.search(rf"\\begin\{{{CODE_ENVS}\}}", text):
            in_code = True
        if re.search(rf"\\end\{{{CODE_ENVS}\}}", text):
            in_code = False
            continue
        if in_code:
            continue
        if not in_body:
            in_body = "\\begin{document}" in text
            if re.search(r"\\todo\{", text):
                todos.setdefault(row[0], []).append(row[1])
            continue
        for m in re.finditer(r"\\begin\{(figure|table)\}\[([^\]]*)\]", text):
            if "H" not in m.group(2):
                report(
                    WARN,
                    loc(row, root),
                    f"{m.group(1)}[{m.group(2)}] може відплисти від свого тексту; приберіть параметр (типово H)",
                )
        if re.search(r"(^|[^\w])[Дд]е\s*:", text) and not in_bib:
            report(
                ERR,
                loc(row, root),
                "«де:» — пояснення після формули починається з «де» без двокрапки (\\begin{where})",
            )
        if ("—" in text or re.search(r"(?<!-)---(?!-)", text)) and not in_bib:
            report(
                WARN, loc(row, root), "довге тире: потрібне коротке «–» (`--` у LaTeX)"
            )
        if re.search(r"(?:[+=<>-]|\\cdot|\\times)\s*\\ldots|\\ldots\s*(?:[+=<>-]|\\cdot|\\times)", text):
            report(WARN, loc(row, root), "\\ldots між знаками операцій: потрібне \\cdots (a_1 + \\cdots + a_n)")
        if re.search(r"[^\s~(\[{]\s+\\(?:ref|eqref)\{", text):
            report(WARN, loc(row, root), "перед \\ref — звичайний пробіл: номер може перенестися на новий рядок (рисунок~\\ref{...})")
        if not in_bib and row[0].name != "meta.tex" and not re.match(r"\s*(?:\\kpiset|[a-z-]+\s*=)", text):
            plain = re.sub(
                r"\\(?:url|path|href|ref|label|cite|includegraphics|input|lstinputlisting|codeinput|texttt|codefile|kpiCode)\*?(\[[^\]]*\])?\{[^}]*\}",
                " ",
                text,
            )
            plain = re.sub(r"\$[^$]*\$", " ", plain)
            numbers(plain, row, root)
            # Only quantities (percent or a unit after the number): «1.2» alone is usually a section/figure/ID.
            for m in re.finditer(
                r"(?<![\w.\\-])(\d+)\.(\d+)(?=(?:\s|~|\\,)*(?:\\?%|(?:с|мс|хв|год|кг|т|г|грн|USD|ГБ|МБ|КБ|Гб|Мб|км|м|см|мм|пікс|кадр\w*|раз\w*)(?![\w]))|(?:\s|~)+(?:відсот\w*|секунд\w*|хвилин\w*|разу|рази))",
                plain,
            ):
                report(
                    WARN,
                    loc(row, root),
                    f"«{m.group(0)}» — у десяткових дробах кома: {m.group(1)},{m.group(2)}",
                )
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
                WARN,
                loc(row, root),
                f"розділ «{title}» без підрозділу «Висновки до розділу»",
            )


def numbers(plain, row, root):
    """ДСТУ 3008: four-digit numbers are written solid, from five digits in groups of three."""
    for m in re.finditer(r"(?<![\d.,\w])([1-9])(?:\s|~|\\,)(\d{3})(?![\d]|(?:\s|~|\\,)\d{3})", plain):
        report(WARN, loc(row, root), f"«{m.group(0)}» — чотирицифрове число пишуть без пробілу: {m.group(1)}{m.group(2)}")
    for m in re.finditer(r"(?<![\d.,\w\-])([1-9]\d{4,})(?![\d\w])", plain):
        n = m.group(1)
        grouped = f"{int(n):,}".replace(",", "~")
        report(WARN, loc(row, root), f"«{n}» — від п'яти цифр розряди відділяють пробілом: {grouped}")


def check_log(doc, root):
    log = doc.with_suffix(".log")
    if not log.exists():
        log = doc.parent / "build" / log.name
    if not log.exists():
        report(
            WARN,
            str(doc.relative_to(root)),
            "ще не зібрано (немає .log) — запустіть `just build`",
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
            f"рядків, що виходять за поле: {len(big)}, найбільше на {max(big):.1f}pt (шукайте «Overfull» у журналі)",
        )
    for key in sorted(set(re.findall(r"Reference `([^']+)' on page", text))):
        report(ERR, str(log.relative_to(root)), f"невизначене посилання «{key}»")
    for key in sorted(set(re.findall(r"Citation `([^']+)' on page", text))):
        report(ERR, str(log.relative_to(root)), f"невизначене джерело «{key}»")
    for name in sorted(set(re.findall(r"File `([^']+)' not found", text))):
        report(ERR, str(log.relative_to(root)), f"не знайдено файл «{name}»")
    if "Rerun to get" in text or "Label(s) may have changed" in text:
        report(
            WARN,
            str(log.relative_to(root)),
            "потрібен ще один прохід LaTeX (посилання можуть бути застарілі)",
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
        report(
            WARN,
            "title/build/title.pdf",
            f"сторінок: {len(pages)}, очікується 6 (титул 1, завдання 2, анотації 2, відомість 1) — "
            "скоротіть пункти завдання, щоб воно вмістилося на одному аркуші з двох боків",
        )
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
                        f"{head}: {len(body)} знаків, межа — 1000 (методичка §5.3)",
                    )
                if "??" in body:
                    report(
                        WARN,
                        "title/build/title.pdf",
                        f"{head}: «??» замість чисел — спершу зберіть інші документи (`just all`)",
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
                        WARN,
                        "title/build/title.pdf",
                        f"{kw}: ключових слів {n}, потрібно 3–10",
                    )


def doc_pdf(doc):
    pdf = doc.parent / "build" / f"{doc.stem}.pdf"
    return pdf if pdf.exists() else doc.with_suffix(".pdf")


def volume_limits(doc):
    """`% check: chapter-pages=3-15, intro-pages=1-4` anywhere in the document's main .tex."""
    limits = {}
    if doc.stem == "explanatory-note":
        limits = {"intro-pages": (0, 4), "main-pages": (60, 70), "chapter1-share": (0, 30)}
    for line in doc.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*%\s*check:\s*(.+)", line)
        if m:
            for k, lo, hi in re.findall(r"([\w-]+)\s*=\s*(\d+)(?:\s*-\s*(\d+))?", m.group(1)):
                limits[k] = (int(lo), int(hi)) if hi else (0, int(lo))
    return limits


CHAPTER = r"^\s*{n}\s+[А-ЯІЇЄҐA-Z][А-ЯІЇЄҐA-Z0-9’'«»,:()\- –]{{4,}}\s*$"


def check_volume(doc, root, limits):
    pages = pdf_pages_text(doc_pdf(doc))
    if not pages or not limits:
        return
    where = str(doc_pdf(doc).relative_to(root))

    def first(pattern, start=0):
        for i in range(start, len(pages)):
            if re.search(pattern, pages[i], re.M):
                return i
        return None

    toc_end = first(r"^\s*ВСТУП\s*\.{3,}") or 0
    intro = first(r"^\s*ВСТУП\s*$", toc_end + 1)
    starts = []
    while True:
        i = first(CHAPTER.format(n=len(starts) + 1), (starts[-1] if starts else (intro or toc_end)) + 1)
        if i is None:
            break
        starts.append(i)
    concl = first(r"^\s*ВИСНОВКИ\s*$", (starts[-1] if starts else 0) + 1)
    if intro is None or not starts or concl is None:
        return

    def out_of(key, value, what):
        lo, hi = limits.get(key, (None, None))
        if lo is not None and not lo <= value <= hi:
            bound = f"{lo}–{hi}" if lo else f"до {hi}"
            report(WARN, where, f"{what}: {value}, за методичкою {bound}")

    out_of("intro-pages", starts[0] - intro, "ВСТУП, сторінок")
    main_pages = concl - starts[0]
    out_of("main-pages", main_pages, "основна частина, сторінок")
    for n, (a, b) in enumerate(zip(starts, [*starts[1:], concl]), 1):
        out_of("chapter-pages", b - a, f"розділ {n}, сторінок")
    if len(starts) > 1 and main_pages:
        out_of("chapter1-share", 100 * (starts[1] - starts[0]) // main_pages, "розділ 1, % основної частини")


NUM = r"([А-ЯA-Z]?\d*\.?\d+|[А-ЯA-Z]\.\d+)"


def check_placement(doc, root):
    """ДСТУ 3008: a figure or table goes after its first mention, on that page or the next."""
    pages = pdf_pages_text(doc_pdf(doc))
    if not pages:
        return
    where = str(doc_pdf(doc).relative_to(root))
    caption = re.compile(rf"^\s*(Рисунок|Таблиця)\s+{NUM}\s+[–-]", re.M)
    placed, mentioned = {}, {}
    for i, page in enumerate(pages):
        for m in caption.finditer(page):
            placed.setdefault((m.group(1)[0], m.group(2)), i)
        text = caption.sub(" ", page)
        text = re.sub(r"Продовження\s+таблиці\s+\S+", " ", text)
        text = re.sub(r"-\n\s*", "", text)
        text = re.sub(r"\s+", " ", text)
        for m in re.finditer(rf"(?i)(?<!\w)(рис(?:ун\w*|\.)|табл(?:иц\w*|\.))\s*{NUM}(?:\s*[–-]\s*{NUM})?", text):
            kind = "Р" if m.group(1).lower().startswith("рис") else "Т"
            nums = [m.group(2)]
            if m.group(3) and "." in m.group(2) and "." in m.group(3):
                (p1, a), (p2, b) = m.group(2).rsplit(".", 1), m.group(3).rsplit(".", 1)
                if p1 == p2 and a.isdigit() and b.isdigit():
                    nums = [f"{p1}.{k}" for k in range(int(a), int(b) + 1)]
            for num in nums:
                mentioned.setdefault((kind, num), i)
    for (kind, num), c in sorted(placed.items(), key=lambda x: x[1]):
        m = mentioned.get((kind, num))
        if m is None or not num[0].isdigit():  # appendix objects live in their appendix
            continue
        name = ("Рисунок" if kind == "Р" else "Таблиця") + f" {num}"
        if c > m + 1:
            report(WARN, where, f"{name} — на с. {c + 1}, а вперше згадана на с. {m + 1}: має стояти на тій самій або наступній сторінці")
        elif c < m:
            report(WARN, where, f"{name} — на с. {c + 1}, раніше за першу згадку (с. {m + 1})")


def stats(root):
    for f in sorted(
        [
            *root.glob("*.kpistats"),
            *root.glob("*/*.kpistats"),
            *root.glob("*/build/*.kpistats"),
            *root.glob("build/*.kpistats"),
        ]
    ):
        vals = dict(re.findall(r"\\kpistat\{(\w+)\}\{(\d+)\}", f.read_text()))
        print(f"{f.stem:17} " + "  ".join(f"{k} {v}" for k, v in vals.items()))


def main(argv):
    issues.clear()
    todos.clear()
    show_stats = "--stats" in argv
    args = [a for a in argv if not a.startswith("--")]
    root = Path(args[0] if args else ".").resolve()
    if show_stats:
        stats(root)
        return 0
    docs = find_documents(root)
    if not docs:
        print(f"не знайдено документів LaTeX у {root}")
        return 1
    for doc in docs:
        rows = load(doc)
        is_note = doc.stem in ("explanatory-note", "main")
        check_bibliography(rows, root)
        check_refs(rows, root)
        check_text(rows, root, is_note)
        check_log(doc, root)
        check_volume(doc, root, volume_limits(doc))
        check_placement(doc, root)
        if (
            "meta.tex" not in "".join(r[2] for r in rows if "\\input" in r[2])
            and (root / "meta.tex").exists()
        ):
            report(
                WARN,
                str(doc.relative_to(root)),
                "не підключає \\input{../meta.tex} — шифри й імена можуть розійтися",
            )
        for row in rows:
            if row[0].name != "meta.tex" and re.search(r"КПІ\.[А-ЯІ]{2}-\d", row[2]):
                report(
                    WARN,
                    loc(row, root),
                    "шифр документа вписано вручну; використайте \\kpiCode{...} з meta.tex",
                )
    check_annotations(root)
    for path, lines in todos.items():
        lines = sorted(set(lines))
        where = loc((path, lines[0], ""), root)
        more = f" (рядки {', '.join(map(str, lines))})" if len(lines) > 1 else ""
        report(ERR, where, f"заглушок \\todo: {len(lines)}{more}")
    seen = set()
    issues[:] = [i for i in issues if not (i in seen or seen.add(i))]

    errors = [i for i in issues if i[0] == ERR]
    for level, where, msg in issues:
        print(f"{where}: {level}: {msg}")
    print(
        f"\nпомилок: {len(errors)}, попереджень: {len(issues) - len(errors)}, документів: {len(docs)}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
