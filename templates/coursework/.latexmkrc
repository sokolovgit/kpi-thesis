# LuaLaTeX (latexmk's pdf_mode 4).
$pdf_mode = 4;
$lualatex = 'lualatex -interaction=nonstopmode -file-line-error -synctex=1 %O %S';
# Intermediate files and the PDF go to build/, the folder itself keeps only sources.
$out_dir = 'build';
