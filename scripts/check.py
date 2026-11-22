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
MATH_ENVS = r"(?:equation|align|gather|multline|eqnarray|flalign|alignat)\*?"
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


CITE_RE = re.compile(
    r"\\(?:nocite|(?:[Cc]ite|[Pp]arencite|[Tt]extcite|[Aa]utocite|[Ff]ootcite|[Ss]upercite|[Ff]ullcite)(s?)[pt]?)\*?"
)
CITE_ARG_RE = re.compile(r"\s*(?:\([^)]*\)|\[[^\]]*\])*\s*\{([^}]+)\}")


def cited_keys(text):
    """Keys of every citation command, including \\cites{a}{b} and \\parencite[см.][с. 5]{x}."""
    for m in CITE_RE.finditer(text):
        pos, groups = m.end(), 0
        while True:
            arg = CITE_ARG_RE.match(text, pos)
            if not arg:
                break
            for key in arg.group(1).split(","):
                yield key.strip()
            pos, groups = arg.end(), groups + 1
            if not m.group(1):
                break
UK_ALPHABET = "абвгґдеєжзиіїйклмнопрстуфхцчшщьюя"


def sort_key(text):
    """ДСТУ 8302 alphabetical order: Cyrillic by the Ukrainian alphabet first, then Latin."""
    text = re.sub(r"\\[A-Za-z]+\*?|[{}~]", " ", text).strip().lower()
    return [(0, UK_ALPHABET.index(c)) if c in UK_ALPHABET else (1, ord(c)) for c in text if c.isalnum()]


def bib_entries(rows, doc):
    """Keys of the .bib files the document loads (\\addbibresource, \\kpisetup{bib-resource=...})."""
    names = []
    for _, _, text in rows:
        names += re.findall(r"\\addbibresource(?:\[[^\]]*\])?\{([^}]+)\}", text)
        for value in re.findall(r"bib-resource\s*=\s*(\{[^}]*\}|[^,}\s]+)", text):
            names += [n.strip() for n in value.strip("{}").split(",") if n.strip()]
    keys = {}
    for name in names:
        bib = doc.parent / name
        if not bib.exists():
            continue
        raw = bib.read_bytes()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            report(ERR, bib.name, "файл джерел не в UTF-8: збережіть його як UTF-8 (biber читатиме кракозябри)")
            text = raw.decode("utf-8", errors="replace")
        for n, line in enumerate(text.splitlines(), 1):
            if re.search(r"\\todo\{", line):
                todos.setdefault(bib, []).append(n)
        for m in re.finditer(r"^\s*@(\w+)\s*[{(]\s*([^,\s]+)\s*,", text, re.M):
            if m.group(1).lower() not in ("string", "comment", "preamble"):
                keys[m.group(2)] = (bib, text[: m.start()].count("\n") + 1)
    return names, keys


def check_bibliography(rows, root, doc=None):
    preamble = "".join(r[2] for r in rows)
    biblatex = bool(re.search(r"bibliography\s*=\s*biblatex|\\usepackage(?:\[[^\]]*\])?\{biblatex\}", preamble))
    order_rule = (re.search(r"sources\s*=\s*(alphabetical|chronological)", preamble) or [None, "citation"])[1]
    cites, bib = [], []
    in_bib = False
    for row in rows:
        text = row[2]
        if "\\begin{thebibliography}" in text:
            in_bib = True
        items = list(re.finditer(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}(.*)", text))
        for m in items:
            bib.append([m.group(1).strip(), row, m.group(2)])
        if in_bib and not items and bib and "\\end{thebibliography}" not in text:
            bib[-1][2] += " " + text.strip()
        if "\\end{thebibliography}" in text:
            in_bib = False
        if not in_bib:
            for key in cited_keys(text):
                if key not in [c for c, _ in cites]:
                    cites.append((key, row))
    if biblatex and doc is not None:
        names, keys = bib_entries(rows, doc)
        if not names:
            report(ERR, str(doc.relative_to(root)), "bibliography=biblatex без файлу джерел: додайте bib-resource=sources.bib")
        elif not keys:
            report(ERR, str(doc.relative_to(root)), f"не знайдено або порожній файл джерел: {', '.join(names)}")
        for key, row in cites:
            if key != "*" and keys and key not in keys:
                report(ERR, loc(row, root), f"\\cite{{{key}}} немає у файлі джерел ({', '.join(names)})")
        return
    if not bib:
        return
    bib_keys = [k for k, _, _ in bib]
    cite_keys = [k for k, _ in cites]
    for key, row in cites:
        if key not in bib_keys:
            report(
                ERR,
                loc(row, root),
                f"\\cite{{{key}}} немає у списку джерел (\\bibitem)",
            )
    for key, row, _ in bib:
        if key not in cite_keys:
            report(
                ERR,
                loc(row, root),
                f"на джерело «{key}» немає посилання в тексті (кожне джерело має бути процитоване)",
            )
    if order_rule != "citation":
        listed = [(k, row, rest) for k, row, rest in bib]
        if order_rule == "alphabetical":
            keyf = lambda e: sort_key(e[2])
            what = "за алфавітом"
        else:
            keyf = lambda e: int((re.search(r"(?<![:\d])\b(1[89]\d\d|20\d\d)\b", e[2]) or [0, 9999])[1])
            what = "за роком видання"
        for (a, row, rest), (b, _, _) in zip(listed, sorted(listed, key=keyf)):
            if a != b:
                report(ERR, loc(row, root), f"джерела не {what} (\\kpisetup{{sources={order_rule}}}): на цьому місці мало б стояти «{b}»")
                break
        return
    order = [k for k in bib_keys if k in cite_keys]
    expected = [k for k in cite_keys if k in bib_keys]
    if order != expected:
        for i, (a, b) in enumerate(zip(order, expected)):
            if a != b:
                row = next(r for k, r, _ in bib if k == a)
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
    in_bib = in_code = in_math = False
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
        if re.search(rf"\\begin\{{{MATH_ENVS}\}}|(?<!\\)\\\[", text):
            in_math = True
        math_line = in_math or "$$" in text
        if re.search(rf"\\end\{{{MATH_ENVS}\}}|(?<!\\)\\\]", text):
            in_math = False
        if text.count("$$") % 2:
            in_math = not in_math
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
        if re.search(r"\((?:\s*|[^()]*(?:формул\w*|див\.)[^()]*)\\eqref\{", text):
            report(WARN, loc(row, root), "посилання на формулу в дужках дає «((2.8))»: «за формулою (2.8)» без зовнішніх дужок")
        elif not math_line and re.search(r"\([^()]*\([^()]*\)(?:[^()]|\([^()]*\))*\)", re.sub(r"\$([^$]*)\$", r"\1", text)):
            report(WARN, loc(row, root), "дужки в дужках: перефразуйте або замініть зовнішні дужки комами чи тире")
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
    blg = log.with_suffix(".blg")
    if blg.exists():
        for line in blg.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.search(r"\]\s+\S+>\s+(WARN|ERROR) - (.+)", line)
            if m:
                report(ERR if m.group(1) == "ERROR" else WARN, str(blg.relative_to(root)), f"biber: {m.group(2).strip()}")
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


def expand_range(a, b):
    """«4.2–4.5» -> 4.2 4.3 4.4 4.5; a single number or a cross-chapter range stays as it is."""
    if b and "." in a and "." in b:
        (p1, x), (p2, y) = a.rsplit(".", 1), b.rsplit(".", 1)
        if p1 == p2 and x.isdigit() and y.isdigit():
            return [f"{p1}.{k}" for k in range(int(x), int(y) + 1)]
    return [a]


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
        item = rf"{NUM}(?:\s*[–-]\s*{NUM})?"
        for m in re.finditer(rf"(?i)(?<!\w)(рис(?:ун\w*|\.)|табл(?:иц\w*|\.))\s*({item}(?:\s*(?:,|і|й|та)\s*{item})*)", text):
            kind = "Р" if m.group(1).lower().startswith("рис") else "Т"
            for one in re.finditer(item, m.group(2)):
                for num in expand_range(one.group(1), one.group(2)):
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


HEADING = r"^\s*(?:\d+\s+)?[А-ЯІЇЄҐA-Z][А-ЯІЇЄҐA-Z0-9’'«»,:()\- –]{4,}\s*$"


def check_short_pages(doc, root):
    """A section that spills 1–3 lines onto its last page costs a whole page of volume."""
    pages = pdf_pages_text(doc_pdf(doc))
    if not pages:
        return
    where = str(doc_pdf(doc).relative_to(root))

    def lines(page):
        return [s for s in page.splitlines() if s.strip() and not re.fullmatch(r"\s*\d+\s*", s)]

    for i in range(1, len(pages) - 1):
        body, nxt = lines(pages[i]), lines(pages[i + 1])
        if (
            1 <= len(body) <= 3
            and not re.match(HEADING, body[0])
            and nxt
            and re.match(HEADING, nxt[0])
            and not any(re.match(r"\s*(Рисунок|Таблиця)\s", s) or re.search(r"(?:\. ?){4}", s) for s in body)
        ):
            report(WARN, where, f"с. {i + 1}: перед новим розділом лише {len(body)} ряд. тексту — скоротіть розділ на кілька рядків, і він стане на сторінку коротшим")


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


def bib_records(text):
    """(type, key, {field: value}, line) for each entry of a .bib file, with balanced braces."""
    out = []
    for m in re.finditer(r"@(\w+)\s*[{(]\s*([^,\s]+)\s*,", text):
        kind = m.group(1).lower()
        if kind in ("string", "comment", "preamble"):
            continue
        fields, i, depth = {}, m.end(), 1
        start = i
        while i < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        body = text[start : i - 1]
        parts, depth, quote, cur = [], 0, False, ""
        for c in body:
            if c == '"' and depth == 0:
                quote = not quote
            depth += {"{": 1, "}": -1}.get(c, 0)
            if c == "," and depth == 0 and not quote:
                parts.append(cur)
                cur = ""
            else:
                cur += c
        parts.append(cur)
        for part in parts:
            name, eq, val = part.partition("=")
            if eq and re.fullmatch(r"\s*\w+\s*", name):
                fields.setdefault(name.strip().lower(), val.strip().strip('{}"'))
        out.append((kind, m.group(2), fields, text[: m.start()].count("\n") + 1))
    return out


YEAR = r"(?<![:\d])\b(1[5-9]\d\d|20\d\d)\b"


def check_sources(rows, root, doc):
    """ДСТУ 8302 details that show up in a written description: URL with «URL:» and the access
    date, no «[Електронний ресурс]» / «Режим доступу» from the old ГОСТ 7.1, a year."""
    items, in_bib = [], False
    for row in rows:
        text = row[2]
        if "\\begin{thebibliography}" in text:
            in_bib = True
            continue
        if "\\end{thebibliography}" in text:
            in_bib = False
        if not in_bib:
            continue
        m = re.search(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}(.*)", text)
        if m:
            items.append([m.group(1).strip(), row, m.group(2)])
        elif items:
            items[-1][2] += " " + text.strip()
    for key, row, entry in items:
        where = loc(row, root)
        if re.search(r"Електронний ресурс|Режим доступу", entry, re.I):
            report(WARN, where, f"«{key}»: «[Електронний ресурс]» і «Режим доступу» — з ГОСТ 7.1; за ДСТУ 8302 — «URL: … (дата звернення: …)»")
        if re.search(r"\\url\{|https?://", entry):
            if "дата звернення" not in entry and "DOI" not in entry:
                report(WARN, where, f"«{key}»: URL без «(дата звернення: ДД.ММ.РРРР)»")
            if re.search(r"\\url\{", entry) and not re.search(r"(URL|DOI)\s*:[\s~]*\\url\{", entry):
                report(WARN, where, f"«{key}»: перед посиланням — «URL: »")
        plain = re.sub(r"\\url\{[^}]*\}|https?://\S+|дата звернення[^)]*", "", entry)
        if not re.search(YEAR, plain) and not re.search(r"б\.\s*р\.", plain) and not re.search(r"\\url\{|https?://", entry):
            report(WARN, where, f"«{key}»: немає року видання")
    if doc is None:
        return
    names, _ = bib_entries(rows, doc)
    for name in names:
        bib = doc.parent / name
        if not bib.exists():
            continue
        text = bib.read_bytes().decode("utf-8-sig", errors="replace")
        for kind, key, f, line in bib_records(text):
            where = f"{bib.relative_to(root)}:{line}"
            if "url" in f and "doi" not in f and "urldate" not in f:
                report(WARN, where, f"«{key}»: url без urldate — у списку не буде «(дата звернення: …)»")
            if re.search(r"Електронний ресурс|Режим доступу", " ".join(f.values()), re.I):
                report(WARN, where, f"«{key}»: «[Електронний ресурс]» / «Режим доступу» не потрібні — стиль сам друкує «URL: …»")
            if kind not in ("online", "software", "dataset", "www", "patent") and not ("date" in f or "year" in f):
                report(WARN, where, f"«{key}»: немає date (року видання)")


HEADING_CMDS = r"\\(?:section|subsection|subsubsection|structural|chapter)\*?(?:\[[^\]]*\])?\{"


def balanced(text, start):
    """The text of the brace group opening right before `start`."""
    depth, i = 1, start
    while i < len(text) and depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[start : i - 1] if depth == 0 else None


ABBR_END = r"(?:\bт\.\s?[дп]|\bін|\bст|\bрр?|\bс|\bім|\betc|\bal)\.\s*$"


def check_headings(rows, root):
    for n, row in enumerate(rows):
        for m in re.finditer(HEADING_CMDS, row[2]):
            title = balanced(" ".join([row[2]] + [r[2] for r in rows[n + 1 : n + 4]]), m.end())
            if not title:
                continue
            title = re.sub(r"\s+", " ", title).strip()
            if re.search(r"(?<!\.)\.$", title) and not re.search(ABBR_END, title):
                clause = "Д 7.1.20, М §6.1" if m.group(0).startswith(("\\section", "\\structural", "\\chapter")) else "Д 7.1.21, М §6.2"
                report(ERR, loc(row, root), f"заголовок «{title}» з крапкою в кінці ({clause})")


def check_abbreviations(rows, root):
    """Inside a run of Cyrillic or of Latin abbreviations the order is alphabetical; the guide
    lists abbreviations, then letter symbols, units and terms, so runs are compared separately."""
    active, entries = False, []
    for row in rows:
        text = row[2]
        if re.search(r"\\structural\{\s*ПЕРЕЛІК УМОВНИХ ПОЗНАЧЕНЬ", text):
            active = True
            continue
        if active and re.search(r"\\end\{(?:longtable|tabular\*?|kpitable)\}|\\structural\{", text):
            break
        if active:
            m = re.match(r"\s*(?:\\hline\s*)*([^&]+?)\s*&", text)
            if m and not re.search(r"Скорочення|Позначення|Значення|Розшифрування|Термін", m.group(1)):
                entries.append((m.group(1), row))

    def script(t):
        if "$" in t or "\\" in t or len(re.sub(r"\W", "", t)) == 1:
            return "other"
        c = next((c for c in t.lower() if c.isalpha()), "")
        return "cyr" if c in UK_ALPHABET else "lat" if c.isascii() and c.isalpha() else "other"
    run = []
    for item in entries + [(None, None)]:
        if item[0] is None or (run and script(item[0]) != script(run[-1][0])):
            for (a, _), (b, rb) in zip(run, run[1:]):
                if script(a) != "other" and sort_key(b) < sort_key(a):
                    report(WARN, loc(rb, root), f"перелік скорочень: «{b}» має стояти перед «{a}» (за алфавітом)")
                    break
            run = []
        if item[0] is not None:
            run.append(item)


LISTING_LINES = 80


def check_listings(rows, root, doc):
    """ПЗ carries listings up to a page (М §5.7); longer code goes to the program text."""
    start = None
    for row in rows:
        text = row[2]
        if "\\appendices" in text:
            break
        if re.search(r"\\begin\{(?:Verbatim|lstlisting|minted|verbatim)\}", text):
            start = row
            count = 0
            continue
        if start is not None:
            if re.search(r"\\end\{(?:Verbatim|lstlisting|minted|verbatim)\}", text):
                if count > LISTING_LINES:
                    report(WARN, loc(start, root), f"лістинг на {count} рядків довший за сторінку — у ПЗ до 1 с., повний код — у «Текст програми»")
                start = None
            else:
                count += 1
            continue
        for m in re.finditer(r"\\codeinput(?:\[([^\]]*)\])?\{([^}]+)\}", text):
            opts, name = m.group(1) or "", m.group(2)
            path = (row[0].parent / name)
            if not path.exists():
                path = doc.parent / name
            if not path.exists():
                continue
            n = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
            first = re.search(r"firstline\s*=\s*(\d+)", opts)
            last = re.search(r"lastline\s*=\s*(\d+)", opts)
            n = (int(last.group(1)) if last else n) - (int(first.group(1)) - 1 if first else 0)
            if n > LISTING_LINES:
                report(WARN, loc(row, root), f"\\codeinput{{{name}}}: {n} рядків — у ПЗ лістинги до 1 с., повний код — у «Текст програми»")


def check_unresolved(doc, root):
    pages = pdf_pages_text(doc_pdf(doc))
    if not pages or doc.stem in ("title", "source-code"):
        return
    bad = [i + 1 for i, p in enumerate(pages) if re.search(r"(?:рисун\w*|таблиц\w*|формул\w*|розділ\w*|пункт\w*|додат\w*|лістинг\w*|алгоритм\w*|с\.|[(\[~])\s*\?\?|\[\?\]", p, re.I)]
    if bad:
        report(WARN, str(doc_pdf(doc).relative_to(root)), f"«??» у PDF, с. {', '.join(map(str, bad[:10]))}: нерозв'язане посилання (або «??» у тексті — тоді пропустіть)")


def check_footnotes(doc, root):
    aux = doc.parent / "build" / f"{doc.stem}.aux"
    if not aux.exists():
        aux = doc.with_suffix(".aux")
    if not aux.exists():
        return
    pages = re.findall(r"\\kpi@footnote\{([^}]*)\}", aux.read_text(encoding="utf-8", errors="replace"))
    for page in dict.fromkeys(pages):
        if pages.count(page) > 4:
            report(WARN, str(doc_pdf(doc).relative_to(root)), f"с. {page} PDF: виносок {pages.count(page)}, не більше 4 на сторінці (Д 7.8)")


DIPLOMA_DOCS = ["title", "specification", "explanatory-note", "source-code", "test-plan", "user-manual", "graphics"]
SCHEMES = {"ССВ", "ССС", "ССД", "ССК", "ССМ", "СБД", "КЕ", "КЗ"}
PROGRAM = "Інженерія програмного забезпечення інформаційних систем"


def check_diploma(root):
    """Composition of the diploma package and the title data in meta.tex (normcontrol checklist)."""
    meta = root / "meta.tex"
    if not meta.exists() or not (root / "title").is_dir():
        return
    for name in DIPLOMA_DOCS:
        if not (root / name / f"{name}.tex").exists():
            report(ERR, name, f"немає документа {name}/{name}.tex — склад диплома (М §4)")
    graphics = root / "graphics" / "graphics.tex"
    if graphics.exists():
        rows = load(graphics)
        sheets = [(m.group(1).strip(), row) for row in rows
                  for m in re.finditer(r"\\(?:graphicsSheet|diagramPage)\{([^}]*)\}", row[2])]
        if len(sheets) < 3:
            report(ERR, str(graphics.relative_to(root)), f"аркушів графічного матеріалу {len(sheets)}, потрібно не менше 3 (М §4)")
        for code, row in sheets:
            if code not in SCHEMES:
                report(WARN, loc(row, root), f"код схеми «{code}» не з переліку М §5.4 ({', '.join(sorted(SCHEMES))}); плакати — за погодженням")
    note = root / "explanatory-note" / "explanatory-note.tex"
    if note.exists():
        text = "".join(r[2] for r in load(note))
        m = re.search(r"\\appendixpdf\{[^}]*(?:подібност|Unicheck|плагіат)[^}]*\}\{([^}]+)\}", text, re.I)
        if not m and not re.search(r"\\appendix\{[^}]*(?:подібност|Unicheck|плагіат)", text, re.I):
            report(WARN, str(note.relative_to(root)), "немає додатка зі звітом подібності (Unicheck) — \\appendixpdf{Звіт подібності}{...}")
        elif m and not (note.parent / m.group(1)).exists():
            report(WARN, str(note.relative_to(root)), f"звіт подібності: немає файлу {m.group(1)}")
    rows = load(meta)
    text = "\n".join(r[2] for r in rows)
    m = re.search(r"^\s*program\s*=\s*\{([^}]*)\}", text, re.M)
    if m and re.sub(r"[~\s]+", " ", m.group(1)).strip() != PROGRAM:
        report(WARN, "meta.tex", f"освітня програма «{m.group(1)}» — для 4 курсу ІПІ «{PROGRAM}» (чекліст)")
    blank = []
    for row in rows:
        km = re.match(r"\s*([\w-]+(?:stamp|short))\s*=\s*\{(.*)\}\s*,?\s*$", row[2])
        if km and (not km.group(2).strip() or re.search(r"Прізвище|ПРІЗВИЩЕ|\\todo", km.group(2))):
            blank.append((km.group(1), row))
    if blank:
        report(WARN, loc(blank[0][1], root), f"не заповнено {', '.join(k for k, _ in blank)} — прізвища в штампах і підписах перевіряє нормоконтроль")
    cal = re.search(r"\\kpiCalendarRows\}?\s*\{(.*?)\n\s*\}", text, re.S)
    if cal:
        empty = [r for r in re.split(r"\\\\", cal.group(1)) if "&" in r and not any(c.strip() for c in r.split("&")[2:])]
        if empty:
            report(WARN, "meta.tex", f"календарний план: без термінів {len(empty)} рядк. (\\kpiCalendarRows)")


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
        check_bibliography(rows, root, doc)
        check_refs(rows, root)
        check_text(rows, root, is_note)
        check_log(doc, root)
        check_volume(doc, root, volume_limits(doc))
        check_placement(doc, root)
        check_short_pages(doc, root)
        check_sources(rows, root, doc)
        check_headings(rows, root)
        if is_note:
            check_abbreviations(rows, root)
        if doc.stem == "explanatory-note":
            check_listings(rows, root, doc)
        check_unresolved(doc, root)
        check_footnotes(doc, root)
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
            m = re.search(r"\\(?:(?:re|provide)?newcommand\*?\s*\{?|def\s*)(\\[A-Za-z]+\d\w*)", row[2])
            if m:
                report(ERR, loc(row, root), f"«{m.group(1)}»: у імені макросу лише літери, LaTeX прочитає цифри як текст після нього (Missing \\begin{{document}})")
            if row[0].name != "meta.tex" and re.search(r"КПІ\.[А-ЯІ]{2}-\d", row[2]):
                report(
                    WARN,
                    loc(row, root),
                    "шифр документа вписано вручну; використайте \\kpiCode{...} з meta.tex",
                )
    check_annotations(root)
    check_diploma(root)
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
