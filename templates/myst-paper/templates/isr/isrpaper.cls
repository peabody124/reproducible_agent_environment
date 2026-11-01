% isrpaper.cls
% LaTeX class for ISR Lab papers
% Intelligence Sensing and Rehabilitation Laboratory
% Northwestern University & Shirley Ryan AbilityLab
%
% Usage: \documentclass{isrpaper}

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{isrpaper}[2026/02/03 ISR Lab Paper Class]

% --------------------------------------------------------------------------
% Class options
% --------------------------------------------------------------------------
\newif\if@bluecolor
\@bluecolorfalse

\DeclareOption{blue}{\@bluecolortrue}
\DeclareOption{orange}{\@bluecolorfalse}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}
\ProcessOptions\relax

\LoadClass[11pt,a4paper]{article}

% --------------------------------------------------------------------------
% Required packages
% --------------------------------------------------------------------------
\RequirePackage[utf8]{inputenc}
\RequirePackage[T1]{fontenc}
\RequirePackage[top=2.5cm, bottom=2.5cm, left=2.5cm, right=2.5cm]{geometry}
\RequirePackage[dvipsnames]{xcolor}
\RequirePackage[most]{tcolorbox}
\RequirePackage{graphicx}
\RequirePackage{amsmath,amssymb}
\RequirePackage{booktabs}
\RequirePackage{hyperref}
\RequirePackage{etoolbox}

% --------------------------------------------------------------------------
% Color definitions
% --------------------------------------------------------------------------
\if@bluecolor
    % Blue/Teal scheme
    \definecolor{isrprimary}{RGB}{30, 90, 150}
    \definecolor{israccent}{RGB}{0, 128, 128}
    \definecolor{isrlight}{RGB}{230, 242, 255}
    \definecolor{isrgray}{RGB}{100, 100, 100}
\else
    % Orange/Cream scheme (SRAlab-inspired)
    \definecolor{isrprimary}{RGB}{232, 93, 4}
    \definecolor{israccent}{RGB}{0, 128, 128}
    \definecolor{isrlight}{RGB}{255, 247, 237}
    \definecolor{isrgray}{RGB}{80, 80, 80}
\fi

% --------------------------------------------------------------------------
% Hyperref setup
% --------------------------------------------------------------------------
\hypersetup{
    colorlinks=true,
    linkcolor=isrprimary,
    citecolor=isrprimary,
    urlcolor=israccent
}

% --------------------------------------------------------------------------
% Metadata commands
% --------------------------------------------------------------------------
\newcommand{\@paperdate}{}
\newcommand{\@correspondence}{}
\newcommand{\@dataseturl}{}
\newcommand{\@datasetname}{}
\newcommand{\@projecturl}{}
\newcommand{\@projectname}{}
\newcommand{\@papernote}{}
\newcommand{\@paperabstract}{}
\newcommand{\@papertitle}{}
\newcommand{\@paperauthors}{}
\newcommand{\@paperaffiliations}{}

\newcommand{\paperdate}[1]{\renewcommand{\@paperdate}{#1}}
\newcommand{\correspondence}[1]{\renewcommand{\@correspondence}{#1}}
\newcommand{\dataset}[2]{\renewcommand{\@datasetname}{#1}\renewcommand{\@dataseturl}{#2}}
\newcommand{\project}[2]{\renewcommand{\@projectname}{#1}\renewcommand{\@projecturl}{#2}}
\newcommand{\papernote}[1]{\renewcommand{\@papernote}{#1}}
\newcommand{\paperabstract}[1]{\renewcommand{\@paperabstract}{#1}}
\renewcommand{\title}[1]{\renewcommand{\@papertitle}{#1}}
\renewcommand{\author}[1]{\renewcommand{\@paperauthors}{#1}}
\newcommand{\affiliations}[1]{\renewcommand{\@paperaffiliations}{#1}}

% --------------------------------------------------------------------------
% Logo command
% --------------------------------------------------------------------------
\newcommand{\ISRLogo}{\includegraphics[height=1.5cm]{isr-logo}}

% --------------------------------------------------------------------------
% Metadata field helpers
% --------------------------------------------------------------------------
\newcommand{\@metafield}[2]{%
    \ifx#2\empty\else\textbf{#1:} #2\\[2pt]\fi%
}
\newcommand{\@metalink}[3]{%
    \ifx#2\empty\else\textbf{#1:} \href{#3}{\textcolor{israccent}{#2}}\\[2pt]\fi%
}

% --------------------------------------------------------------------------
% Header box (maketitle replacement)
% --------------------------------------------------------------------------
\renewcommand{\maketitle}{%
    \begin{tcolorbox}[
        enhanced,
        colback=isrlight,
        colframe=isrlight,
        boxrule=0pt,
        arc=12pt,
        left=16pt, right=16pt, top=16pt, bottom=16pt,
        before skip=0pt,
        after skip=20pt,
    ]
    % Title and authors
    \begin{center}
        {\LARGE\bfseries \@papertitle\par}
        \vspace{0.7em}
        {\large \@paperauthors\par}
        \vspace{0.4em}
        {\small \@paperaffiliations\par}
    \end{center}
    \vspace{0.8em}

    % Abstract (full width)
    \noindent
    {\small \@paperabstract}

    \vspace{12pt}

    % Metadata and logo (side by side with minimum height for logo)
    \noindent
    \begin{minipage}[t]{0.62\textwidth}
        \vspace{0pt}% Align tops
        \small
        \ifdefempty{\@paperdate}{}{\textbf{Date:} \@paperdate\\[2pt]}%
        \ifdefempty{\@correspondence}{}{\textbf{Correspondence:} \@correspondence\\[2pt]}%
        \ifdefempty{\@datasetname}{}{\textbf{Dataset:} \href{\@dataseturl}{\textcolor{israccent}{\@datasetname}}\\[2pt]}%
        \ifdefempty{\@projectname}{}{\textbf{Project:} \href{\@projecturl}{\textcolor{israccent}{\@projectname}}\\[2pt]}%
        \ifdefempty{\@papernote}{}{\textbf{Note:} \@papernote\\[2pt]}%
        \vspace{0pt plus 1fill}% Add stretchable space to match logo height
    \end{minipage}%
    \hfill%
    \begin{minipage}[t]{0.35\textwidth}
        \vspace{0pt}% Align tops
        \raggedleft
        \ISRLogo
    \end{minipage}
    \end{tcolorbox}
}

% --------------------------------------------------------------------------
% Section formatting (optional customization)
% --------------------------------------------------------------------------
\renewcommand{\section}{\@startsection{section}{1}{0pt}%
    {-3.5ex plus -1ex minus -.2ex}%
    {2.3ex plus .2ex}%
    {\normalfont\Large\bfseries}}

\renewcommand{\subsection}{\@startsection{subsection}{2}{0pt}%
    {-3.25ex plus -1ex minus -.2ex}%
    {1.5ex plus .2ex}%
    {\normalfont\large\bfseries}}

% --------------------------------------------------------------------------
% Compact table formatting (\footnotesize)
% --------------------------------------------------------------------------
\AtBeginEnvironment{table}{\footnotesize\setlength{\tabcolsep}{4.5pt}}
\AtBeginEnvironment{tabular}{\footnotesize\setlength{\tabcolsep}{4.5pt}}
\AtBeginEnvironment{longtable}{\footnotesize\setlength{\tabcolsep}{4.5pt}}

\endinput
