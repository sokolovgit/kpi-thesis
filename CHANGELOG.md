# Зміни

Версії класу — у `\ProvidesClass` / `\ProvidesPackage` (`tex/`) і в git-тегах.
Оновлення: `git pull` у клоні репозиторію; плагін — `/plugin marketplace update kpi-thesis`.

## v2.0.0 — не випущено

Рушій — LuaLaTeX (#19). Команда LaTeX більше не розвиває XeTeX і радить LuaTeX
([LaTeX News 40](https://www.latex-project.org/news/latex2e-news/ltnews40.pdf)).
- Шаблони збираються `lualatex` (`$pdf_mode = 4` у `.latexmkrc`). XeLaTeX ще працює, клас
  лише попереджає; pdfLaTeX — зрозуміла помилка замість збою fontspec.
- Без Times New Roman / Courier New (Overleaf, Linux без mscorefonts) клас бере TeX Gyre
  Termes / Cursor і попереджає, що для здачі потрібен Times New Roman.
- Аркуші А3 і зведення PDF без poppler працюють під LuaLaTeX.

Клас (#21):
- Пакети з префіксом класу: `kpi-thesis-titles`, `kpi-thesis-graphics`; старі `kpi-titles`,
  `kpi-graphics` лишаються і просто підключають нові.
- `kpitable`, `where`, переліки «а)» і підрахунок для анотації — окремі пакети
  `kpi-thesis-{tables,where,lists,stats}`; клас підключає їх сам, нічого міняти не треба.
- Опції класу — ключі ядра LaTeX (`\DeclareKeys`): `main-font=`, `mono-font=`.
- Без `xparse`, `etoolbox`, `pdftexcmds`: те саме тепер робить ядро LaTeX. Якщо робота
  користується командами `etoolbox` напряму, підключіть його в преамбулі (зараз його й так
  підвантажують інші пакети).
- `just test` збирає `kpitable` на дві сторінки й перевіряє «Продовження таблиці».

### Перехід з 1.3

- Нічого не обов'язково: робота з `xelatex` у `.latexmkrc` збирається як раніше, з попередженням.
- Щоб перейти на LuaLaTeX, у `.latexmkrc` роботи: `$pdf_mode = 4;` і
  `$lualatex = 'lualatex -interaction=nonstopmode -file-line-error -synctex=1 %O %S';`
  замість рядка з `xelatex`. Розкладка може зсунутися (рисунок чи таблиця переходить на іншу
  сторінку) — роботу, що вже на здачі, краще не перемикати.
- Linux: `texlive-luatex` замість `texlive-xetex`.
- `\usepackage{kpi-titles}` / `{kpi-graphics}` працюють; нові імена — `kpi-thesis-titles` /
  `kpi-thesis-graphics`.

## v1.3.0 — 2026-11-15

Змінює вигляд PDF:
- `kpitable`: лінія після рядка, що закінчився на краю сторінки, більше не дублюється вгорі
  наступної (#12).
- URL розривається лише після `/ . - _` (`url` замість `xurl`), а не посеред слова. Для дуже
  довгих адрес — `\kpisetup{url-breaks=anywhere}` (#16). Посилання можуть перейти на інші рядки.

Збірка (#14):
- `just build` після збою показує перші помилки з журналу і скидає `.fdb_latexmk`, тож після
  виправлення latexmk збирає наново, а не пише «Nothing to do».
- `just clean-aux` — прибрати проміжні файли, лишивши PDF (після двох збірок одночасно).
- `just freeze` — заморозити клас для роботи, що вже на здачі: `git pull` її не змінює (#17).

`just check`:
- переліки «таблицях 4.2 і 4.3», «рисунках 3.1, 3.2 та 3.3» — згадка кожного номера (#13);
- цифри в іменах макросів (`\resultChi2`) — помилка (#15);
- «(формула (2.8))», дужки в дужках, майже порожня остання сторінка розділу (#15).

Клас: тип колонки `L` не перевизначає власний `L` роботи (#17).

### Перехід з 1.2

- Робота з `\usepackage{xurl}` у преамбулі так і рветиме URL будь-де — прибрати, якщо не треба.
- Справжні `justfile` робіт оновлюються лише вручну: нові рецепти `build`, `clean-aux`, `freeze`
  можна перенести з `templates/*/justfile` (рядок `KPI := ...` лишити свій).

## v1.2.0 — 2026-11-15

Змінює вигляд PDF:
- Анотація: рисунки й таблиці рахуються разом із додатками, як і сторінки (#8).
- `kpitable` не лишає підпис і шапку самих унизу сторінки (#6).
- Код у тексті програми — `fvextra` (`\codeinput`, `Verbatim`) замість `listings`: кирилиця в
  коментарях більше не псується (#7).
- Титул курсової: «Номер залікової книжки» (`gradebook`) (#8).

Нове:
- `\kpisetup{...}` для курсових, де методичка розходиться з дипломною: `left-margin`,
  `hyphenation=false`, `enumerate=arabic`, `table-caption=left`, `appendix-title=inline`,
  `algorithms` (#5, #7). Тип колонки `L{...}` — по лівому краю без переносів.
- `just check`: розміщення рисунків і таблиць відносно першої згадки (за PDF), порядок
  перших згадок, обсяг розділів курсової (`% check: chapter-pages=3-15`), `\ldots` між
  знаками операцій, звичайний пробіл перед `\ref`, запис чисел (4000 / 10 000), формули з
  номером без посилання (#9).
- `.chktexrc` у шаблонах і ті самі правила для texlab (Zed) і LaTeX Workshop (#10).
- Скіл: курсова (склад з методички дисципліни, `\kpisetup` як єдине місце рішень),
  рецензування перед здачею (#10).

### Перехід з 1.1

Робота, створена на v1.1, збирається й далі, але частину преамбули тепер робить клас (#17):

| Було в преамбулі роботи | Тепер |
|---|---|
| `\newcolumntype{L}...` | є в класі; власний `L` лишається (з v1.3 без попередження) |
| `\geometry{left=20mm}` | `\kpisetup{left-margin=20mm}` |
| `\setlength{\headwidth}{\textwidth}` | клас робить сам — прибрати |
| `\hyphenpenalty`, `\exhyphenpenalty`, `\emergencystretch`, `\hbadness` | `\kpisetup{hyphenation=false}` |
| `\setlist[enumerate,...]{label=\arabic*)}` | `\kpisetup{enumerate=arabic}` |
| `\usepackage{algorithm}`, `algpseudocode`, `\floatname`... | `\kpisetup{algorithms}` |
| `\usepackage{needspace}`, `\usepackage{fvextra}` | підключає клас — прибрати |
| `\Needspace{...}` перед `kpitable` | `kpitable` тримає шапку сам; прибрати або `[N]` |
| `lstlisting` / `\lstinputlisting` у тексті програми | `Verbatim` / `\codeinput` (кирилиця) |

Дублі не ламають збірку, але `\kpisetup` і ручні налаштування можуть розійтися.

## v1.1.0 — 2026-11-13

Змінює вигляд PDF:
- `where`: тире одразу після кожного позначення, після «де» звичайний пробіл (#2).

Інше (#3):
- Ім'я зведеного PDF береться з `meta.tex` (прізвище зі `student-stamp` + `group`), у курсовій —
  з шапки `main.tex`. Змінна `OUT` у justfile шаблону більше не потрібна.
- Без poppler `just all` зводить PDF самим XeLaTeX (аркуші А3 лишаються А3).
- `just check` українською; ловить довге тире `---`; не перевіряє текст у `Verbatim` / `minted`;
  правильно підключає `\input` файлів з крапкою в імені.
- `just test` пише «OK» і пояснює, що заглушки `\todo` у свіжому шаблоні — норма.
- Windows: `just install` робить junction замість копії, тож `git pull` одразу оновлює клас.
- Завідувач кафедри — явне поле в `meta.tex`.
- Шаблони мають налаштування VS Code (LaTeX Workshop).
- `templates/` додатково під MIT-0: у роботах ліцензію зберігати не треба.
- Скіл: перше налаштування винесено в `references/setup.md`; цикл «зібрати → перевірити →
  виправити»; перевірка, чи клон не відстає від GitHub; MacTeX ставить користувач сам.
- Тести `check.py` і перевірка маніфестів плагіна в CI.

## v1.0.0 — 2026-11-08

Перший публічний реліз: клас, шаблони диплома й курсової, `just check`, плагін для Claude Code.
