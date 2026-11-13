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
    echo "OK. PDF шаблонів: $tmp"
