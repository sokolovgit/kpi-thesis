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
    mkdir -p "$texmf/tex/latex"
    rm -rf "$texmf/tex/latex/kpi-thesis"
    ln -s "{{ROOT}}/tex" "$texmf/tex/latex/kpi-thesis"
    kpsewhich kpi-thesis.cls

# Прибрати клас з TEXMFHOME
uninstall:
    rm -rf "$(kpsewhich -var-value TEXMFHOME)/tex/latex/kpi-thesis"

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
    @echo "-> {{dir}}: fill {{ if kind == 'diploma' { 'meta.tex' } else { 'main.tex' } }}, then \`just all\`"

# Зібрати шаблони в тимчасовій папці й прогнати check
test:
    #!/usr/bin/env bash
    set -euo pipefail
    tmp=$(mktemp -d)
    for kind in diploma coursework; do
      just new $kind "$tmp/$kind" >/dev/null 2>&1
      if ! log=$(cd "$tmp/$kind" && just all 2>&1); then
        echo "$log" | tail -40; echo "$kind: build failed in $tmp/$kind"; exit 1
      fi
      echo "$kind: built"
      out=$(cd "$tmp/$kind" && just check 2>/dev/null || true)
      echo "$out" | tail -1
      # a fresh template may only fail on its \todo placeholders
      if echo "$out" | grep ': error:' | grep -vq 'placeholder'; then
        echo "$out" | grep ': error:' | grep -v 'placeholder'; exit 1
      fi
    done
    echo "output: $tmp"
