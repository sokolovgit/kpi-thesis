# LuaLaTeX (latexmk's pdf_mode 4).
$pdf_mode = 4;
$lualatex = 'lualatex -interaction=nonstopmode -file-line-error -synctex=1 %O %S';
# Each document builds into its own build/ (latexmk -cd), the folders keep only sources.
$out_dir = 'build';
