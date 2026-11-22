# kpi-thesis: клас, шаблони й перевірки для диплома та курсових КПІ ФІОТ (кафедра ІПІ).
ROOT := replace(justfile_directory(), '\', '/')
# MacTeX puts its binaries here; GUI-launched shells don't always have it on PATH.
export PATH := if path_exists('/Library/TeX/texbin') == "true" { '/Library/TeX/texbin:' + env('PATH') } else { env('PATH') }

[private]
default:
    @just --list

# Зробити клас видимим для TeX (у TEXMFHOME: ~/Library/texmf на macOS, ~/texmf деінде)
install:
    #!/usr/bin/env bash
    set -euo pipefail
    texmf=$(kpsewhich -var-value TEXMFHOME)
    dest="$texmf/tex/latex/kpi-thesis"
    mkdir -p "$texmf/tex/latex"
    case "$(uname -s)" in
      MINGW*|MSYS*|CYGWIN*)
        # Git Bash's ln -s copies; a junction needs no admin rights and follows git pull.
        # rmdir drops a junction without touching its target.
        [ -e "$dest" ] && { cmd //c rmdir "$(cygpath -w "$dest")" 2>/dev/null || rm -rf "$dest"; }
        if ! cmd //c mklink /J "$(cygpath -w "$dest")" "$(cygpath -w "{{ROOT}}/tex")" >/dev/null; then
          cp -R "{{ROOT}}/tex" "$dest"
          echo "{{ROOT}}" > "$dest/.repo"
          echo "junction failed, class copied: rerun 'just install' after every git pull"
        fi ;;
      *)
        rm -rf "$dest"
        ln -s "{{ROOT}}/tex" "$dest" ;;
    esac
    kpsewhich kpi-thesis.cls

# Прибрати клас з TEXMFHOME
uninstall:
    #!/usr/bin/env bash
    dest="$(kpsewhich -var-value TEXMFHOME)/tex/latex/kpi-thesis"
    case "$(uname -s)" in
      MINGW*|MSYS*|CYGWIN*) cmd //c rmdir "$(cygpath -w "$dest")" 2>/dev/null || rm -rf "$dest" ;;
      *) rm -rf "$dest" ;;
    esac

# Скіл без плагіна: симлінк у ~/.claude/skills (не разом із плагіном)
install-skill:
    mkdir -p "$HOME/.claude/skills"
    ln -sfn "{{ROOT}}/skills/kpi-thesis" "$HOME/.claude/skills/kpi-thesis"

# Нова робота з шаблону: just new diploma ~/kpi/diploma
[no-cd]
new kind dir:
    test -d "{{ROOT}}/templates/{{kind}}" || { echo "kind: diploma | coursework"; exit 1; }
    test ! -e "{{dir}}" || { echo "{{dir}} already exists"; exit 1; }
    mkdir -p "$(dirname "{{dir}}")"
    cp -R "{{ROOT}}/templates/{{kind}}" "{{dir}}"
    { printf "KPI := '%s'\n" "{{ROOT}}"; tail -n +2 "{{ROOT}}/templates/{{kind}}/justfile"; } > "{{dir}}/justfile"
    @echo "-> {{dir}}: заповніть {{ if kind == 'diploma' { 'meta.tex' } else { 'шапку main.tex' } }}, далі \`just all\`"

# Зібрати шаблони в тимчасовій папці й прогнати check
test:
    #!/usr/bin/env bash
    set -euo pipefail
    tmp=$(mktemp -d)
    for kind in diploma coursework; do
      just new $kind "$tmp/$kind" >/dev/null 2>&1
      if ! log=$(cd "$tmp/$kind" && just all 2>&1); then
        echo "$log" | tail -40; echo "$kind: збірка впала, див. $tmp/$kind"; exit 1
      fi
      out=$(cd "$tmp/$kind" && just check 2>/dev/null || true)
      # a fresh template may only fail on its \todo placeholders
      if echo "$out" | grep ': помилка:' | grep -vq 'заглушок'; then
        echo "$out" | grep ': помилка:' | grep -v 'заглушок'; echo "$kind: check знайшов помилки"; exit 1
      fi
      echo "$kind: зібрано, check без помилок (крім заглушок \todo — у свіжому шаблоні це норма)"
    done
    mkdir -p "$tmp/kpitable"
    latexmk -lualatex -silent -outdir="$tmp/kpitable" "{{ROOT}}/tests/tex/kpitable.tex" >/dev/null 2>&1 \
      || { grep -m5 -A3 '^!' "$tmp/kpitable/kpitable.log"; echo "kpitable: збірка впала"; exit 1; }
    if command -v pdftotext >/dev/null; then
      pdftotext "$tmp/kpitable/kpitable.pdf" - | grep -q "Продовження таблиці 1.1" \
        || { echo "kpitable: немає «Продовження таблиці 1.1» на другій сторінці"; exit 1; }
      echo "kpitable: продовження на наступній сторінці є"
    fi
    mkdir -p "$tmp/bib"
    for t in bibliography alphabetical more; do
      latexmk -lualatex -silent -cd -outdir="$tmp/bib" "{{ROOT}}/tests/tex/bib/$t.tex" >/dev/null 2>&1 \
        || { grep -m5 -A3 '^!' "$tmp/bib/$t.log"; echo "bibliography ($t): збірка впала"; exit 1; }
      if command -v pdftotext >/dev/null; then
        pdftotext -layout "$tmp/bib/$t.pdf" - | sed 's/^ *//;s/  */ /g' | grep -E '^[0-9]+\) ' \
          | diff "{{ROOT}}/tests/tex/bib/expected-$t.txt" - \
          || { echo "bibliography ($t): список відрізняється від tests/tex/bib/expected-$t.txt"; exit 1; }
      fi
    done
    echo "bibliography: описи ДСТУ 8302, алфавітний порядок і крайні випадки як в еталонах"
    echo "OK. PDF шаблонів: $tmp"

# Архів для CTAN: build/kpi-thesis.zip (клас, пакети, документація, README, LICENSE)
ctan:
    #!/usr/bin/env bash
    set -euo pipefail
    rm -rf build/ctan build/kpi-thesis.zip
    mkdir -p build/ctan/kpi-thesis/doc build/doc
    TEXINPUTS="{{ROOT}}/tex//:" latexmk -lualatex -silent -outdir="{{ROOT}}/build/doc" docs/kpi-thesis-doc.tex >/dev/null \
      || { grep -m5 -A3 '^!' build/doc/kpi-thesis-doc.log; exit 1; }
    cp tex/*.cls tex/*.sty tex/*.bbx tex/*.cbx build/ctan/kpi-thesis/
    cp ctan/README.md LICENSE build/ctan/kpi-thesis/
    cp docs/kpi-thesis-doc.tex build/doc/kpi-thesis-doc.pdf build/ctan/kpi-thesis/doc/
    (cd build/ctan && zip -qrX ../kpi-thesis.zip kpi-thesis)
    unzip -l build/kpi-thesis.zip | tail -n +4 | sed '$d' | sed '$d' | awk '{print $4}'
    echo "-> build/kpi-thesis.zip"

# Перевірити архів і опис на сервері CTAN (нічого не публікує): just ctan-validate you@example.com
ctan-validate email: ctan
    #!/usr/bin/env bash
    set -euo pipefail
    e='{{email}}'
    sed "s|^\\\\email{}|\\\\email{$e}|" ctan/kpi-thesis.pkg > build/ctan/kpi-thesis.pkg
    cd build/ctan && PERL_LWP_SSL_CA_FILE="${PERL_LWP_SSL_CA_FILE:-/etc/ssl/cert.pem}" \
      ctan-o-mat --validate kpi-thesis.pkg

# Чи узгоджені версії: CHANGELOG, \Provides* у tex/, ctan/kpi-thesis.pkg, документація (just release-check v2.1.0)
release-check tag="":
    python3 scripts/release_check.py {{ if tag == "" { "" } else { "--tag " + tag } }}

# Подати реліз на CTAN: перевірки, архів, валідація на сервері, підтвердження, подання
ctan-submit email: release-check (ctan-validate email)
    #!/usr/bin/env bash
    set -euo pipefail
    grep -q '^\\update{true}' build/ctan/kpi-thesis.pkg || { echo "ctan/kpi-thesis.pkg: потрібен \\update{true}"; exit 1; }
    awk '/^\\begin{announcement}/,/^\\end{announcement}/' build/ctan/kpi-thesis.pkg
    read -r -p "Подати kpi-thesis $(sed -n 's/^\\version{\(.*\)}/\1/p' build/ctan/kpi-thesis.pkg) на CTAN від {{email}}? [y/N] " a
    [ "$a" = y ] || { echo "скасовано"; exit 1; }
    cd build/ctan && PERL_LWP_SSL_CA_FILE="${PERL_LWP_SSL_CA_FILE:-/etc/ssl/cert.pem}" \
      ctan-o-mat --submit kpi-thesis.pkg

# Zip шаблону курсової для Overleaf (Upload Project): build/kpi-thesis-coursework-overleaf.zip
overleaf:
    #!/usr/bin/env bash
    set -euo pipefail
    d=build/overleaf; rm -rf "$d" build/kpi-thesis-coursework-overleaf.zip; mkdir -p "$d"
    cp -R templates/coursework/main.tex templates/coursework/sources.bib templates/coursework/chapters "$d/"
    mkdir -p "$d/media" && touch "$d/media/.keep"
    cp tex/kpi-thesis.cls tex/kpi-thesis-*.sty tex/kpi-thesis-dstu.bbx tex/kpi-thesis-dstu.cbx "$d/"
    printf '%s\n' '$pdf_mode = 4;' > "$d/latexmkrc"
    (cd "$d" && zip -qrX ../kpi-thesis-coursework-overleaf.zip .)
    echo "-> build/kpi-thesis-coursework-overleaf.zip (Overleaf: New Project → Upload Project)"
