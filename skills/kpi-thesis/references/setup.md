# Перше налаштування

Плагін дає лише скіл; TeX, клас і шаблони ставляться окремо. Іти по кроках, не вгадувати з
помилок збірки.

1. **Перевірити все одним викликом** і показати користувачу, чого бракує:

   ```sh
   [ -d /Library/TeX/texbin ] && PATH="/Library/TeX/texbin:$PATH"
   for c in xelatex latexmk kpsewhich just git; do
     command -v "$c" >/dev/null && echo "ok  $c" || echo "--  $c"
   done
   command -v python3 >/dev/null || command -v python >/dev/null && echo "ok  python" || echo "--  python"
   command -v pdfunite >/dev/null && echo "ok  poppler" || echo "--  poppler (необов'язково)"
   command -v fc-list >/dev/null && for f in "Times New Roman" "Courier New"; do
     fc-list | grep -q "$f" && echo "ok  $f" || echo "--  $f"; done
   ```

   Шрифти перевіряються лише там, де є `fc-list` (Linux); у macOS і Windows вони вбудовані.
   poppler необов'язковий: без нього `just all` зводить PDF самим XeLaTeX, а `just check`
   пропускає перевірки анотації й обсягу за готовим PDF.

2. **Поставити відсутнє.** Дати команди для ОС користувача. Інсталятори, що питають пароль
   адміністратора, **користувач запускає сам** у своєму терміналі (у Claude Code — з префіксом
   `!`): з неінтерактивної оболонки вони зависнуть на запиті пароля. Решту — лише з його згоди.
   - macOS:
     - сам: `brew install --cask mactex-no-gui` — це `.pkg`, просить пароль; кілька ГБ, 10–20 хв.
       Після нього бінарники в `/Library/TeX/texbin`, у новому терміналі вже в PATH;
     - можна з Claude: `brew install just poppler`.
   - Linux (Debian/Ubuntu), сам: `sudo apt install texlive-xetex texlive-latex-extra
     texlive-fonts-recommended texlive-plain-generic texlive-lang-cyrillic latexmk
     poppler-utils python3 ttf-mscorefonts-installer`. `just` ≥ 1.21 — бінарник із
     https://github.com/casey/just/releases (в apt часто старий або відсутній).
   - Windows: TeX Live (https://tug.org/texlive/windows.html) і Git for Windows ставить сам
     (усі команди далі — у Git Bash); потім `winget install Casey.Just` і
     `winget install Python.Python.3.12`. Альтернатива — WSL з кроками для Linux.

3. **Клонувати й встановити клас.** Запитати місце; за замовчуванням `~/kpi-thesis`, окремо від
   тек із роботами (репозиторій — інструмент, не місце для курсової):

   ```sh
   git clone https://github.com/sokolovgit/kpi-thesis ~/kpi-thesis && cd ~/kpi-thesis && just install
   ```

   На Windows `just install` робить junction; якщо не вийшло — копіює клас і пише про це, тоді
   після кожного `git pull` треба ще раз `just install`.

4. **Переконатися, що все збирається:** `just test` у репозиторії (1–2 хв). Має закінчитися
   рядком `OK`. Якщо збірка падає, лог покаже причину (бракує пакета TeX — доставити;
   `fontspec` не знаходить шрифт — крок 2).

5. Далі — «Нова робота» в SKILL.md. Оновлення класу пізніше: `git pull` у репозиторії.
