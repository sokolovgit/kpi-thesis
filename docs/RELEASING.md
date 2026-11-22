# Реліз

Реліз — це git-тег, GitHub Release і оновлення на CTAN (звідти — TeX Live і MiKTeX).

## 1. Версії

Нумерація — `MAJOR.MINOR.PATCH`: MAJOR ламає роботи, MINOR додає можливості, PATCH — виправлення.

- `CHANGELOG.md`: розділ `## vX.Y.Z — РРРР-ММ-ДД`, а для MAJOR і MINOR ще `### Перехід з X.Y`
  (що змінити в уже створених роботах).
- `tex/*.cls`, `tex/*.sty`: дата й версія в `\ProvidesClass` / `\ProvidesPackage`
  (`[РРРР/ММ/ДД vX.Y ...]`).
- `ctan/kpi-thesis.pkg`: `\version{X.Y.Z}`; для MAJOR і MINOR — текст `announcement` англійською
  (що нового), для PATCH його лишають порожнім, і CTAN не розсилає анонс. `note` — для команди
  CTAN, якщо є що пояснити.
- `docs/kpi-thesis-doc.tex`: «Версія X.Y.Z, дата» у шапці.

`just release-check` звіряє все це між собою; `just release-check vX.Y.Z` — ще й з тегом.

## 2. GitHub

Зміни йдуть звичайним PR. Після злиття, на `main`:

```sh
just release-check vX.Y.Z
just test
just overleaf
git tag -a vX.Y.Z -m vX.Y.Z && git push origin vX.Y.Z
gh release create vX.Y.Z --title vX.Y.Z --notes-file <розділ CHANGELOG> build/kpi-thesis-coursework-overleaf.zip
```

Zip для Overleaf обов'язково йде в реліз: на нього веде кнопка «Open in Overleaf» у README.

## 3. CTAN

```sh
just ctan-submit you@example.com
```

Рецепт ще раз перевіряє версії, збирає `build/kpi-thesis.zip`, проганяє `ctan-o-mat --validate`,
показує анонс і подає лише після підтвердження. Адреса не зберігається в репозиторії; на неї
приходить лист від команди CTAN, відповідати — англійською, без HTML.

- Кожне подання команда CTAN переглядає вручну, тож подаємо лише релізи, а не кожен PR, і не з CI.
- TeX Live підхоплює оновлення за кілька днів (`tlmgr update kpi-thesis`), MiKTeX — так само.
- TeX Live заморожує оновлення перед щорічним випуском (для TeX Live 2027 — приблизно з кінця
  лютого 2027): реліз, поданий тоді, з'явиться вже в новому випуску.
- Overleaf оновлює TeX Live раз на рік, тож на Overleaf користуються zip з релізу.
