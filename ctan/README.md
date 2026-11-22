# kpi-thesis

LaTeX class for the bachelor diploma project and courseworks of Igor Sikorsky Kyiv
Polytechnic Institute (KPI), Faculty of Informatics and Computer Engineering, typeset per
the Ukrainian standard DSTU 3008:2015 and the department guide.

It covers the whole diploma package: title page, assignment with the calendar plan,
Ukrainian and English abstracts with automatically counted pages, figures, tables, sources
and appendices, the project sheet and A3 drawing sheets with ESKD title blocks, technical
specification, explanatory note, program text, test plan and user manual. Tables continue
across pages under «Продовження таблиці N», formula symbols are explained in a `where`
environment, lists use Ukrainian labels.

## Files

- `kpi-thesis.cls` — the class (options `diploma`, `coursework`, `main-font=`, `mono-font=`);
- `kpi-thesis-titles.sty` — work data (`\kpiset`), title pages, assignment, abstracts,
  project sheet;
- `kpi-thesis-graphics.sty` — A3 sheets with the ESKD title block;
- `kpi-thesis-tables.sty`, `kpi-thesis-where.sty`, `kpi-thesis-lists.sty`,
  `kpi-thesis-stats.sty` — loaded by the class, usable on their own;
- `kpi-thesis-dstu.bbx`, `kpi-thesis-dstu.cbx` — biblatex style per DSTU 8302:2015
  (`\kpisetup{bibliography=biblatex, bib-resource=sources.bib}`; needs biber);
- `kpi-titles.sty`, `kpi-graphics.sty` — the pre-2.0 names of the two packages above;
- `doc/kpi-thesis-doc.pdf` — documentation (in Ukrainian, the language of the documents).

## Requirements

LuaLaTeX (XeLaTeX still works, with a warning). The guide requires Times New Roman and
Courier New; where they are missing the class falls back to TeX Gyre Termes and TeX Gyre
Cursor and says so.

Templates for the diploma and the coursework, a normcontrol linter and a Claude Code plugin
are in the project repository: https://github.com/sokolovgit/kpi-thesis

## License

MIT, see `LICENSE`. Copyright (c) 2026 Oleksandr Sokolov.
