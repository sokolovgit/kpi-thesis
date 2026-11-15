% kpi-thesis.cls — diploma / coursework documents for KPI FICE (ІПІ department).
% Based on a 2026 diploma format that passed normcontrol; rules: ДСТУ 3008:2015 and
% the department guide «Дипломний проєкт: ... вимоги до структури, змісту та оформлення» (2024).
% Compile with XeLaTeX.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{kpi-thesis}[2026/11/15 v1.3 KPI FICE thesis documents]

\newif\ifkpi@coursework
\DeclareOption{diploma}{\kpi@courseworkfalse}
\DeclareOption{coursework}{\kpi@courseworktrue}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{extarticle}}
\ProcessOptions\relax

\LoadClass[14pt,a4paper]{extarticle}

\sloppy

% 14 pt with a 17 pt base, then \onehalfspacing — ~29 lines per page, like Word's 1.5.
\renewcommand\normalsize{%
  \@setfontsize\normalsize{14pt}{17pt}%
  \abovedisplayskip 14\p@ \@plus3\p@ \@minus7\p@
  \abovedisplayshortskip \z@ \@plus4\p@
  \belowdisplayshortskip 7\p@ \@plus4\p@ \@minus3\p@
  \belowdisplayskip \abovedisplayskip
  \let\@listi\@listI
}

% --- Fonts, language ---
\RequirePackage{fontspec}
\setmainfont{Times New Roman}
\setmonofont{Courier New}
\RequirePackage[english,ukrainian,shorthands=off]{babel}

% --- Page ---
\RequirePackage[left=30mm,right=20mm,top=20mm,bottom=20mm]{geometry}
\RequirePackage{setspace}
\normalsize
\onehalfspacing
\RequirePackage{indentfirst}
\setlength{\parindent}{1.25cm}
\RequirePackage{ragged2e}
\justifying

% --- Packages used across documents ---
\RequirePackage{ulem}
\setlength{\ULdepth}{2pt}
\RequirePackage{xparse}
\RequirePackage{etoolbox}
\RequirePackage{array}
\RequirePackage{tabularx}
\RequirePackage{longtable}
\RequirePackage{makecell}
\RequirePackage{multirow}
\RequirePackage{float}
\RequirePackage{amsmath}
\RequirePackage{graphicx}
\RequirePackage{caption}
\RequirePackage{enumitem}
\RequirePackage{pdfpages}
\RequirePackage{listings}
\RequirePackage{fvextra}
\RequirePackage{needspace}
\RequirePackage{xcolor}
\RequirePackage{cite}
\RequirePackage{pdftexcmds}
% URLs break after / . - _ and the like, never mid-word; \kpisetup{url-breaks=anywhere} for xurl.
\RequirePackage[hyphens]{url}
\urlstyle{same}

\setlength{\tabcolsep}{4pt}
\newcolumntype{Y}{>{\RaggedRight\arraybackslash}X}
% Flush-left cell that never breaks a word: \begin{kpitable}{|L{4cm}|L{10cm}|}...
% Defined at \begin{document}, so a work that has its own L (from v1.1) keeps it without a warning.
\AtBeginDocument{\@ifundefined{NC@find@L}%
  {\newcolumntype{L}[1]{>{\RaggedRight\arraybackslash\hyphenpenalty=10000\exhyphenpenalty=10000}p{#1}}}{}}
% media/ first: with latexmk -outdir=build, ../media/ also resolves against build/ and breaks loading.
\graphicspath{{media/}{../media/}{./}}
\floatplacement{figure}{H}
\floatplacement{table}{H}

% --- Headings ---
\RequirePackage{titlesec}
\RequirePackage{titletoc}

\titleformat{\section}
  {\centering\bfseries\MakeUppercase}
  {\thesection}{1em}{}
\titleformat{\subsection}
  {\bfseries}
  {\thesubsection}{1em}{}
\titlespacing*{\subsection}
  {\parindent}{3.25ex plus 1ex minus .2ex}{1.5ex plus .2ex}
\titleformat{\subsubsection}
  {\bfseries}
  {\thesubsubsection}{1em}{}
\titlespacing*{\subsubsection}
  {\parindent}{3.25ex plus 1ex minus .2ex}{1.5ex plus .2ex}
\setcounter{secnumdepth}{3}

\pretocmd{\section}{\clearpage}{}{}

\titlecontents{section}[0em]{\raggedright}{\thecontentslabel\hspace{0.5em}}{}{\titlerule*[1pc]{.}\contentspage}
\titlecontents{subsection}[1em]{\raggedright}{\thecontentslabel\hspace{0.5em}}{}{\titlerule*[1pc]{.}\contentspage}
\titlecontents{subsubsection}[2.75em]{\raggedright}{\thecontentslabel\hspace{0.5em}}{}{\titlerule*[1pc]{.}\contentspage}

\renewcommand\tableofcontents{%
  \section*{\centering ЗМІСТ}%
  \@starttoc{toc}%
}

% Unnumbered structural element (ВСТУП, ВИСНОВКИ, ...) listed in the ToC.
\NewDocumentCommand\structural{m}{%
  \section*{\centering #1}%
  \addcontentsline{toc}{section}{#1}%
}

% --- Page numbers: top right, none until \mainmatter ---
\RequirePackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[R]{\thepage}
\renewcommand{\headrulewidth}{0pt}
\setlength{\headheight}{17pt}
% Follow margins changed in the preamble (\kpisetup{left-margin=...}, \geometry).
\AtBeginDocument{\setlength{\headwidth}{\textwidth}}
\pagenumbering{gobble}

% Page 1 is the document's title page; numbering is visible from the page after it.
\NewDocumentCommand\mainmatter{}{%
  \clearpage
  \pagenumbering{arabic}%
  \setcounter{page}{2}%
}

% --- Captions: «Рисунок 1.2 – Назва», «Таблиця 1.2 – Назва» ---
\numberwithin{figure}{section}
\numberwithin{table}{section}
\numberwithin{equation}{section}

\DeclareCaptionLabelSeparator{kpidash}{ -- }
% «з абзацного відступу» (ДСТУ 3008 7.6.8); margin= is ignored by longtable captions.
\DeclareCaptionFormat{kpiindent}{\hspace*{1.25cm}#1#2#3\par}
\captionsetup*[figure]{
  name=Рисунок,
  labelsep=kpidash,
  justification=centering,
}
\captionsetup*[table]{
  name=Таблиця,
  labelsep=kpidash,
  format=kpiindent,
  justification=raggedright,
  singlelinecheck=false,
}
\setlength{\LTcapwidth}{\textwidth}

% Long table with the ДСТУ continuation line and repeated header. The \label goes inside
% the caption so editors (texlab) see it:
%   \begin{kpitable}{|p{4cm}|p{10cm}|}{Назва\label{tab:key}}{Поле & Опис}  rows  \end{kpitable}
% The caption and header never stay alone at the bottom of a page: the table starts on a new
% page unless the header plus [N] more lines fit (default 5: caption and ~3 rows; 0 = off).
% A longtable \hline is drawn twice around its break point, so a row rule at a page break
% reappeared at the top of the next page. Here the header already opens each page: one rule.
\ExplSyntaxOn
\def\kpi@LT@hline{%
  \noalign{\ifnum0=`}\fi\penalty\@M\futurelet\@let@token\kpi@LT@@hline}
\def\kpi@LT@@hline{%
  \ifx\@let@token\hline
    \gdef\LT@sep{\penalty\@M\vskip\doublerulesep}%
  \else
    \gdef\LT@sep{\penalty-\@lowpenalty}%
  \fi
  \ifnum0=`{\fi}%
  \multispan\LT@cols\unskip\leaders\hrule\@height\arrayrulewidth\hfill\cr
  \noalign{\cs_if_exist_use:N \tbl_gdecr_row_count: \LT@sep}}
\ExplSyntaxOff
\newsavebox\kpi@tablehead
\NewDocumentEnvironment{kpitable}{O{5} m m m}{%
  \let\LT@hline\kpi@LT@hline
  \ifnum#1>0
    \sbox\kpi@tablehead{\begin{tabular}{#2}\hline #4 \\ \hline\end{tabular}}%
    \Needspace{\dimexpr\ht\kpi@tablehead+\dp\kpi@tablehead+#1\baselineskip\relax}%
  \fi
  \begin{longtable}{#2}
  \caption{#3}\\
  \hline #4 \\ \hline
  \endfirsthead
  \caption*{Продовження таблиці \thetable}\\
  \hline #4 \\ \hline
  \endhead
}{%
  \end{longtable}%
}
\NewDocumentCommand\tablecontinued{}{\caption*{Продовження таблиці \thetable}}

% --- Formula symbol explanations: «де» without a colon, one symbol per line ---
%   \begin{where} M & маса авто; \\ F & сила контакту. \end{where}
% The dash follows each symbol at its own width: a column sized to the widest symbol
% leaves a gap after short ones (q_d next to [w > d]). Wrapped lines and later rows start
% under the first symbol, as in the ДСТУ 3008 example.
\newlength{\kpi@wherewidth}
\ExplSyntaxOn
\seq_new:N \l__kpi_where_rows_seq
\seq_new:N \l__kpi_where_cells_seq
\NewDocumentEnvironment{where}{+b}
  {
    \par
    \settowidth{\kpi@wherewidth}{де\ }
    \seq_set_split:Nnn \l__kpi_where_rows_seq { \\ } {#1}
    \seq_map_indexed_inline:Nn \l__kpi_where_rows_seq
      {
        \tl_if_blank:nF {##2}
          {
            \seq_set_split:Nnn \l__kpi_where_cells_seq { & } {##2}
            \noindent \hangindent=\kpi@wherewidth \hangafter=1
            \int_compare:nNnTF {##1} = { 1 } { де\ } { \hspace*{\kpi@wherewidth} }
            $ \seq_item:Nn \l__kpi_where_cells_seq { 1 } $ \ --\ \seq_item:Nn \l__kpi_where_cells_seq { 2 }
            \par
          }
      }
  }
  {}
\ExplSyntaxOff

% --- Lists: «–» for plain lists; «а)» then «1)» for referenced lists ---
\def\kpi@ukralph#1{\ifcase#1\or а\or б\or в\or г\or д\or е\or ж\or и\or к\or л\or м\or н\or п\or р\or с\or т\or у\or ф\or х\or ц\or ш\or щ\or ю\or я\else\@ctrerr\fi}
\def\kpi@ukrAlph#1{\ifcase#1\or А\or Б\or В\or Г\or Д\or Е\or Ж\or И\or К\or Л\or М\or Н\or П\or Р\or С\or Т\or У\or Ф\or Х\or Ц\or Ш\or Щ\or Ю\or Я\else\@ctrerr\fi}
\def\ukralph#1{\expandafter\kpi@ukralph\csname c@#1\endcsname}
\def\ukrAlph#1{\expandafter\kpi@ukrAlph\csname c@#1\endcsname}
\AddEnumerateCounter{\ukralph}{\kpi@ukralph}{щ}

\setlist{itemsep=0pt,parsep=0pt,topsep=0pt,partopsep=0pt}
\setlist[itemize,1]{label=\textendash, labelindent=\parindent, leftmargin=0cm, itemindent=*}
\setlist[itemize,2]{label=\textendash, labelindent=2\parindent, leftmargin=0cm, itemindent=*}
\setlist[enumerate,1]{label=\ukralph*), labelindent=\parindent, leftmargin=0cm, itemindent=*}
\setlist[enumerate,2]{label=\arabic*), labelindent=2\parindent, leftmargin=0cm, itemindent=*}

% Underlined full-width item, used on the assignment form.
\newcommand{\underitem}[1]{%
  \item
  \uline{\arabic{enumi})\hspace{0.3cm}#1}%
  \leaders\hbox{\rule[-\ULdepth]{1pt}{\ULthickness}}\hfill\kern0pt%
}

% --- Bibliography: «1) Опис», department guide appendix Ж ---
\addto\captionsukrainian{\renewcommand{\refname}{СПИСОК ВИКОРИСТАНИХ ДЖЕРЕЛ}}
\renewcommand{\@biblabel}[1]{#1)}
\renewenvironment{thebibliography}[1]
  {\structural{\refname}%
   \list{\@biblabel{\@arabic\c@enumiv}}%
     {%
      \usecounter{enumiv}%
      \let\p@enumiv\@empty
      \renewcommand{\theenumiv}{\@arabic\c@enumiv}%
      \settowidth{\labelwidth}{\@biblabel{#1}}%
      \labelsep=0.5em
      \leftmargin=0cm
      \itemindent=\dimexpr\parindent+\labelwidth+\labelsep\relax
      \itemsep=0pt \parsep=0pt \topsep=0pt \partopsep=0pt
     }%
   \sloppy
   \clubpenalty4000
   \widowpenalty4000
   \sfcode`\.=\@m}
  {\def\@noitemerr{\@latex@warning{Empty `thebibliography' environment}}%
   \global\c@kpi@sources=\c@enumiv
   \endlist}

% --- Appendices: «Додаток А» on its own line, the title under it ---
\newif\ifkpi@inappendix
\NewDocumentCommand\appendices{}{%
  \clearpage
  \global\kpi@inappendixtrue
  \setcounter{section}{0}%
  \renewcommand\thesection{\ukrAlph{section}}%
  \renewcommand\thefigure{\thesection.\arabic{figure}}%
  \renewcommand\thetable{\thesection.\arabic{table}}%
  \renewcommand\theequation{\thesection.\arabic{equation}}%
}
\RenewDocumentCommand\appendix{o m}{%
  \clearpage
  \refstepcounter{section}%
  \global\advance\c@kpi@appendices\@ne
  \IfValueT{#1}{\label{#1}}%
  \ifkpi@appinline
    {\centering Додаток \thesection.\ \textbf{#2}\par}%
  \else
    {\centering Додаток \thesection\par\nopagebreak
     \vspace{0.5\baselineskip}\nopagebreak
     \textbf{#2}\par}%
  \fi
  \addcontentsline{toc}{section}{Додаток \thesection\ #2}%
  \vspace{\baselineskip}%
}
% A ready-made document (similarity report, ...) as an appendix: title sheet, then its pages.
\NewDocumentCommand\appendixpdf{o m m}{%
  \appendix[#1]{#2}%
  \includepdf[pages=-,pagecommand={\thispagestyle{fancy}}]{#3}%
}

% --- Program listings: monospace 8 pt, single spacing (guide §5.7) ---
% \setstretch goes first: it reselects the current font size and would undo \fontsize.
\lstdefinestyle{kpicode}{
  basicstyle=\setstretch{1}\ttfamily\fontsize{8}{9}\selectfont,
  keywordstyle=\bfseries,
  commentstyle=\itshape\color{gray},
  showstringspaces=false,
  columns=fullflexible,
  keepspaces=true,
  breaklines=true,
  tabsize=4,
  frame=none,
  numbers=none,
  extendedchars=true,
  aboveskip=0.5\baselineskip,
  belowskip=0.5\baselineskip,
}
\lstset{style=kpicode}
% listings under XeLaTeX moves punctuation next to Cyrillic in strings and comments, so files
% go through fvextra: \codeinput[firstline=10, lastline=40]{../../app/main.py}, or the Verbatim
% environment. Options are \VerbatimInput's; fontsize= overrides the 8 pt default.
\fvset{fontsize=\setstretch{1}\fontsize{8}{9}\selectfont, breaklines=true, breakanywhere=true}
\NewDocumentCommand\codeinput{O{} m}{\VerbatimInput[#1]{#2}}

% --- Totals for the annotation and the project sheet («Відомість») ---
% Each document writes <jobname>.kpistats into its output folder; titles read them back.
\newcounter{kpi@figures}
\newcounter{kpi@tables}
\newcounter{kpi@sources}
\newcounter{kpi@appendices}
% Every numbered caption adds a line to the list of figures/tables (\caption* doesn't).
% Appendices count too, like their pages do.
\AddToHook{begindocument/end}{%
  \let\kpi@addcontentsline\addcontentsline
  \def\addcontentsline#1{%
    \ifnum\pdf@strcmp{#1}{lof}=0 \stepcounter{kpi@figures}\fi
    \ifnum\pdf@strcmp{#1}{lot}=0 \stepcounter{kpi@tables}\fi
    \kpi@addcontentsline{#1}}%
}

\newcount\kpi@shipped
\AddToHook{shipout/after}{\global\advance\kpi@shipped\@ne}
\newwrite\kpi@stats
\AtEndDocument{%
  \clearpage
  \immediate\openout\kpi@stats=\jobname.kpistats\relax
  \immediate\write\kpi@stats{\string\kpistat{pages}{\the\kpi@shipped}}%
  \immediate\write\kpi@stats{\string\kpistat{figures}{\the\value{kpi@figures}}}%
  \immediate\write\kpi@stats{\string\kpistat{tables}{\the\value{kpi@tables}}}%
  \immediate\write\kpi@stats{\string\kpistat{sources}{\the\value{kpi@sources}}}%
  \immediate\write\kpi@stats{\string\kpistat{appendices}{\the\value{kpi@appendices}}}%
  \immediate\closeout\kpi@stats
}

% \kpiloadstats{main}{../explanatory-note/build/explanatory-note.kpistats} then \kpistatof{main}{pages}; «??» until built.
\NewDocumentCommand\kpiloadstats{m m}{%
  \begingroup
  \def\kpistat##1##2{\global\@namedef{kpi@stat@#1@##1}{##2}}%
  \InputIfFileExists{#2}{}{}%
  \endgroup
}
\NewDocumentCommand\kpistatof{m m}{%
  \@ifundefined{kpi@stat@#1@#2}{\textbf{??}}{\@nameuse{kpi@stat@#1@#2}}%
}

% Placeholder that stays visible in the PDF; `just check` lists every one left.
\NewDocumentCommand\todo{m}{\textcolor{red}{[#1]}}

% «Файл path» + «Реалізація функціональної задачі ...» headings in the program text.
\NewDocumentCommand\codefile{m m}{%
  \par\bigskip\noindent\textbf{Файл }\path{#1}\par
  \noindent Реалізація функціональної задачі #2.\par
}

% --- Where a coursework guide differs from the diploma one: \kpisetup{...} in the preamble ---
%   left-margin    = 20mm     % default 30 mm (diploma guide)
%   hyphenation    = false    % no word breaks (also hides the Underfull noise that follows)
%   enumerate      = arabic   % «1)», nested «а)»; default «а)», nested «1)»
%   table-caption  = left     % from the left edge; default from the paragraph indent
%   appendix-title = inline   % «Додаток А. Назва» on one line; default two lines
%   url-breaks     = anywhere % xurl: a URL may break at any character; default after / . - _
%   algorithms                % algorithm + algpseudocode, «Алгоритм 1.1 – Назва» like tables
\newif\ifkpi@appinline
\def\kpi@nohyphenation{%
  \hyphenpenalty=10000 \exhyphenpenalty=10000
  \emergencystretch=3em \hbadness=10000 }
\def\kpi@arabiclists{%
  \setlist[enumerate,1]{label=\arabic*)}%
  \setlist[enumerate,2]{label=\ukralph*)}}
\def\kpi@leftcaptions{%
  \captionsetup*[table]{format=plain, justification=justified, singlelinecheck=false}}
\def\kpi@algorithms{%
  \RequirePackage{algorithm}%
  \RequirePackage[noend]{algpseudocode}%
  \floatname{algorithm}{Алгоритм}%
  \floatplacement{algorithm}{H}%
  \numberwithin{algorithm}{section}%
  \captionsetup*[algorithm]{labelsep=kpidash, justification=raggedright, singlelinecheck=false}}
\ExplSyntaxOn
\keys_define:nn { kpi / setup }
  {
    left-margin    .code:n = { \geometry { left = #1 } },
    hyphenation    .choices:nn = { true, false }
      { \int_compare:nNnT { \l_keys_choice_int } = { 2 } { \kpi@nohyphenation } },
    enumerate      .choices:nn = { alph, arabic }
      { \int_compare:nNnT { \l_keys_choice_int } = { 2 } { \kpi@arabiclists } },
    table-caption  .choices:nn = { indent, left }
      { \int_compare:nNnT { \l_keys_choice_int } = { 2 } { \kpi@leftcaptions } },
    appendix-title .choices:nn = { separate, inline }
      { \int_compare:nNnT { \l_keys_choice_int } = { 2 } { \kpi@appinlinetrue } },
    url-breaks     .choices:nn = { symbols, anywhere }
      { \int_compare:nNnT { \l_keys_choice_int } = { 2 } { \RequirePackage{xurl} } },
    algorithms     .code:n = { \kpi@algorithms },
    algorithms     .value_forbidden:n = true,
  }
\NewDocumentCommand \kpisetup { m } { \keys_set:nn { kpi / setup } { #1 } }
\ExplSyntaxOff
\@onlypreamble\kpisetup

\RequirePackage[hidelinks]{hyperref}

\endinput
