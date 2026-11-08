# XeLaTeX straight to PDF (the xdv route drops the A3 page size of the graphic sheets).
$pdf_mode = 1;
$pdflatex = 'xelatex -interaction=nonstopmode -file-line-error -synctex=1 %O %S';
# Intermediate files and the PDF go to build/, the folder itself keeps only sources.
$out_dir = 'build';
