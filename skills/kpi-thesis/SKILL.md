---
name: kpi-thesis
description: Write and build a KPI FICE (кафедра ІПІ) diploma or coursework in LaTeX — the full diploma package (титул, завдання, анотації, відомість, ТЗ, ПЗ, текст програми, ПМТ, КК, графічний матеріал) with ДСТУ 3008:2015 formatting and normcontrol checks. Use when the user works on the diploma or a coursework ("дипломна", "курсова", "пояснювальна записка", "нормоконтроль", "/kpi-thesis"), starts a new one, or asks about thesis formatting or submission rules.
---

# Дипломний проєкт і курсова (КПІ ФІОТ, кафедра ІПІ) у LaTeX

Інструмент — репозиторій [kpi-thesis](https://github.com/sokolovgit/kpi-thesis): клас
`kpi-thesis.cls` з пакетами `kpi-titles`, `kpi-graphics` (тека `tex/`), шаблони (`templates/`),
лінтер нормоконтролю (`scripts/check.py`) і `justfile`. Збирання — XeLaTeX.

Основа — формат диплома кафедри ІПІ 2026 року, що пройшов нормоконтроль, з виправленнями
зауважень, які в ньому знайшлися. Правила: методичка кафедри 2024 → ДСТУ 3008:2015 → ДСТУ 8302:2015 → ЄСПД.
Повний перелік з номерами пунктів і посиланнями: `references/requirements.md`.

## Де лежить репозиторій

Клас встановлено симлінком, тож корінь репозиторію знаходиться так:

```sh
cls=$(kpsewhich kpi-thesis.cls) && repo=$(cd "$(dirname "$(realpath "$cls")")/.." && pwd) \
  && test -f "$repo/justfile" && test -d "$repo/templates" && echo "$repo"
```

Усередині роботи шлях до репозиторію вже записаний у її `justfile` (`KPI := '...'`).
На Windows `just install` копіює клас замість симлінка, і перевірка вище не пройде — тоді
запитати, куди клоновано репозиторій. Якщо `kpsewhich` не знаходить клас або сам `kpsewhich`
відсутній — це перший запуск: пройти «Перше налаштування».

## Перше налаштування

Плагін дає лише цей скіл; TeX, клас і шаблони ставляться окремо. Іти по кроках, не
вгадувати з помилок збірки.

1. **Перевірити все одним викликом** і показати користувачу, чого бракує:

   ```sh
   [ -d /Library/TeX/texbin ] && PATH="/Library/TeX/texbin:$PATH"
   for c in xelatex latexmk kpsewhich just pdfunite pdftotext git; do
     command -v "$c" >/dev/null && echo "ok  $c" || echo "--  $c"
   done
   command -v python3 >/dev/null || command -v python >/dev/null && echo "ok  python" || echo "--  python"
   command -v fc-list >/dev/null && for f in "Times New Roman" "Courier New"; do
     fc-list | grep -q "$f" && echo "ok  $f" || echo "--  $f"; done
   ```

   Шрифти перевіряються лише там, де є `fc-list` (Linux); у macOS і Windows вони вбудовані.

2. **Поставити відсутнє** — дати команди для ОС користувача і виконувати лише з його згоди.
   Привілейовані команди (`sudo apt …`, інсталятори з GUI) користувач запускає сам.
   - macOS: `brew install --cask mactex-no-gui` (кілька ГБ, 10–20 хв) і `brew install just poppler`.
     Після MacTeX бінарники в `/Library/TeX/texbin` — у новому терміналі вони вже в PATH.
   - Linux (Debian/Ubuntu): `sudo apt install texlive-xetex texlive-latex-extra
     texlive-fonts-recommended texlive-plain-generic texlive-lang-cyrillic latexmk
     poppler-utils python3 ttf-mscorefonts-installer`; `just` ≥ 1.21 — бінарник із
     https://github.com/casey/just/releases (в apt часто старий або відсутній).
   - Windows: TeX Live (https://tug.org/texlive/windows.html), Git for Windows (усі команди —
     у Git Bash), `winget install Casey.Just Python.Python.3.12`, `scoop install poppler`.
     Альтернатива — WSL з кроками для Linux.

3. **Клонувати й встановити клас.** Запитати місце; за замовчуванням `~/kpi-thesis`, окремо від
   тек із роботами (репозиторій — інструмент, не місце для курсової):

   ```sh
   git clone https://github.com/sokolovgit/kpi-thesis ~/kpi-thesis && cd ~/kpi-thesis && just install
   ```

4. **Переконатися, що все збирається:** `just test` у репозиторії (1–2 хв). Обидва шаблони
   мають зібратися; помилки `check` лише про `\todo` — норма. Якщо збірка падає, лог
   покаже причину (бракує пакета TeX — доставити; `fontspec` не знаходить шрифт — крок 2).

5. Далі — «Нова робота». Оновлення класу пізніше: `git pull` у репозиторії
   (на Windows після цього ще раз `just install`).

## Нова робота

```sh
cd "$repo"
just new diploma ~/kpi/diploma        # або: just new coursework <dir>
cd ~/kpi/diploma
# заповнити meta.tex (курсова — шапку main.tex)
just all        # усі документи + зведений build/<OUT>.pdf
just check      # перевірки нормоконтролю
```

## Структура диплома

| Папка | Документ | Шифр |
|---|---|---|
| `title/` | титул, завдання, анотації укр/англ, відомість | `.00.90` |
| `specification/` | технічне завдання | `.01.91` |
| `explanatory-note/` | пояснювальна записка (`chapters/*.tex`) | `.02.81` |
| `source-code/` | текст програми | `.03.12` |
| `test-plan/` | програма та методика тестування | `.04.51` |
| `user-manual/` | керівництво користувача | `.05.34` |
| `graphics/` | графічний матеріал (А3) | `.06.99` |

- **`meta.tex` — єдине джерело** теми, ПІБ, шифрів, дат наказу. Жодних шифрів і дат руками в
  документах: інакше дата наказу легко розходиться між завданням і ТЗ.
- **Числа рахуються самі.** Кожен документ збирається у свою `build/` і пише туди `<doc>.kpistats` (сторінки, рисунки, таблиці,
  джерела, додатки). Титул бере їх для анотації (`\kpiAnnotationStats`) і відомості.
  Тому `title` збирається останнім — `just all` це робить.
- `just build explanatory-note`, `just watch explanatory-note` — один документ; `just stats` — числа.

## Команди класу

| Що | Як |
|---|---|
| Структурний елемент без номера | `\structural{ВСТУП}` |
| Нумерація сторінок після титулу | `\mainmatter` |
| Таблиця з «Продовження таблиці N» | `\begin{kpitable}{|p{4cm}|p{10cm}|}{Назва\label{tab:key}}{\textbf{А} & \textbf{Б}} ... \end{kpitable}` |
| Пояснення до формули | `\begin{where} M & маса, кг; \\ F & сила, Н. \end{where}` |
| Переліки | `itemize` → «–»; `enumerate` → «а)», вкладений → «1)» |
| Додатки | `\appendices`, далі `\appendix{Назва}` або `\appendixpdf{Звіт подібності}{../media/report.pdf}` (шлях — від файлу документа) |
| Код у тексті програми | `\codefile{path}{задача}` + `\lstinputlisting[firstline=..,lastline=..]{../../repo/file}` |
| Аркуш А3 | `\diagramPage{ССВ}{Назва схеми}{file.png}` або `\graphicsSheet{код}{назва}{вміст}` |
| Заглушка | `\todo{...}` — червона в PDF, `just check` рахує |

Рисунки й таблиці за замовчуванням `[H]` (стоять де написані). Картинки — у `media/`.

## Як писати

- **Тільки коротке тире** `--` (–). Довге `—` check позначає.
- **Десяткова кома**: `62,1~\%`, не `62.1`.
- **Формула — частина речення**, після неї «де» без двокрапки (`where`). Нумерувати лише ті,
  на які є посилання (`\eqref` / «(1.2)»).
- **На кожен рисунок і таблицю — посилання в тексті** («на рисунку~\ref{fig:x}»,
  «(таблиця~\ref{tab:x})»). Діапазон `\ref{a}--\ref{b}` покриває все між ними.
- **Джерела — у порядку першої згадки** (`thebibliography` руками, ДСТУ 8302, мітка `1)`).
- **Кожен розділ закінчується** `\subsection{Висновки до розділу}`.
- **Вступ ≤ 4 с., розділ 1 ≤ 30 %, основна частина 60–70 с.**; анотації ≤ 1000 знаків, 3–10
  ключових слів, однаковий зміст укр/англ.
- **Тема** — дослівно як у наказі. **ОП** — «Інженерія програмного забезпечення інформаційних систем».
- **Числа в тексті — з реальних прогонів**, а не з голови; суми й частки мають сходитися
  (наприклад, кількості в анотації й у розділі тестування).

## Перед здачею (нормоконтроль)

- [ ] `just check` без помилок; попередження переглянуті
- [ ] тема збігається з наказом; номер і дата наказу правильні (денна/заочна/поновлені різні)
- [ ] на титулі є керівник (рецензента можна пізніше); консультант і нормоконтроль у штампах
- [ ] календарний план заповнений (`\kpiCalendarRows` у `meta.tex`)
- [ ] усі частини: титул, завдання, 2 анотації, відомість, ТЗ (з прототипами екранних форм!),
      ПЗ + звіт Unicheck, текст програми, ПМТ, КК, графічний матеріал (≥ 3 аркуші)
- [ ] шифри в штампах графіки відповідають типу схем (ССВ, ССМ, СБД, КЕ…)
- [ ] у PDF немає «??» (усе зібрано через `just all`)
- [ ] зведений PDF з `build/` — саме він іде на нормоконтроль

## Довідники

- `references/requirements.md` — вимоги з номерами пунктів методички й ДСТУ, розбіжності між
  ними, посилання на першоджерела.
- `references/gotchas.md` — граблі LaTeX/XeLaTeX, на які вже наступили.
