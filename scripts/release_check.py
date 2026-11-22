#!/usr/bin/env python3
"""Чи узгоджені версії перед релізом: CHANGELOG, \\Provides* у tex/, опис для CTAN, документація.

python3 scripts/release_check.py [корінь] [--tag v2.1.0]
"""

import re
import sys
from pathlib import Path


def check(root, tag=None):
    root = Path(root)
    errors = []
    m = re.search(
        r"^## v(\d+)\.(\d+)\.(\d+) — (.+)$", (root / "CHANGELOG.md").read_text(), re.M
    )
    if not m:
        return ["CHANGELOG.md: немає розділу «## vX.Y.Z — дата»"]
    major, minor, patch, date = m.groups()
    version = f"{major}.{minor}.{patch}"
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        return [f"CHANGELOG.md: v{version} ще без дати релізу («{date}»)"]
    tex_date = date.replace("-", "/")

    for f in sorted((root / "tex").glob("*.[cs][lt][sy]")):
        for name, d, v in re.findall(
            r"\\Provides(?:Class|Package)\{([^}]+)\}\[(\S+) v(\S+)", f.read_text()
        ):
            if d != tex_date:
                errors.append(
                    f"tex/{f.name}: {name} датовано {d}, а реліз — {tex_date}"
                )
            if v not in (f"{major}.{minor}", version):
                errors.append(
                    f"tex/{f.name}: {name} має v{v}, а реліз — v{major}.{minor}"
                )

    pkg = re.search(
        r"^\\version\{([^}]*)\}", (root / "ctan/kpi-thesis.pkg").read_text(), re.M
    )
    if not pkg or pkg.group(1) != version:
        errors.append(
            f"ctan/kpi-thesis.pkg: \\version{{{pkg.group(1) if pkg else ''}}}, а реліз — {version}"
        )

    if f"Версія {version}," not in (root / "docs/kpi-thesis-doc.tex").read_text():
        errors.append(f"docs/kpi-thesis-doc.tex: у шапці не «Версія {version}»")

    if tag is not None and tag != f"v{version}":
        errors.append(f"тег {tag}, а в CHANGELOG — v{version}")
    return errors


def main(argv):
    tag = None
    if "--tag" in argv:
        i = argv.index("--tag")
        tag = argv[i + 1]
        argv = argv[:i] + argv[i + 2 :]
    root = argv[0] if argv else Path(__file__).resolve().parent.parent
    errors = check(root, tag)
    for e in errors:
        print(f"помилка: {e}")
    if not errors:
        print("версії узгоджені")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
