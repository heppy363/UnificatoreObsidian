from __future__ import annotations

import base64
from datetime import date
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import os
import re
import shutil
import subprocess
import sys
import tempfile


WIKILINK_RE = re.compile(r"(!)?\[\[([^\]]+)\]\]")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"}
DEFAULT_LATEX_LIST_DEPTH = 9
PREFERRED_PDF_ENGINES = ("tectonic", "xelatex", "lualatex", "pdflatex")
DEFAULT_PAPER_SIZE = "a4"
DEFAULT_FONT_SIZE = "10pt"
DEFAULT_MAIN_FONT = "Latin Modern Sans"
DEFAULT_SANS_FONT = "Latin Modern Sans"
DEFAULT_LINE_STRETCH = "1.05"
DEFAULT_GEOMETRY_OPTIONS = (
    "left=20mm",
    "right=20mm",
    "top=38mm",
    "bottom=22mm",
    "headheight=46pt",
    "headsep=17pt",
    "footskip=18pt",
)
DEFAULT_TOC_DEPTH = "3"
DEFAULT_TOC_TITLE = "Sommario"
REVISION_TABLE_TITLE = "Tabella revisioni"
REVISION_TABLE_AUTHOR = "Assistenza Tecnica"
REVISION_TABLE_DESCRIPTION = "Prima emissione del manuale unificato"
PORTABLE_TOOL_DIR_NAMES = ("external", "tools", ".portable-tools")
BABEL_HEADER_TITLE = "Engineering Ingegneria Informatica S.p.A."
BABEL_HEADER_SUBTITLE = "DC Sanita e Pubblica Amministrazione"
BABEL_HEADER_NOTE = "Nota di lavoro"
BABEL_LOGO_FILENAME = "babel-header-logo.jpg"
BABEL_LOGO_BASE64 = (
    "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"
)
PANDOC_ENV_VAR = "UNIFICATORE_OBSIDIAN_PANDOC"
PDF_ENGINE_ENV_VAR = "UNIFICATORE_OBSIDIAN_PDF_ENGINE"
TOOLS_DIR_ENV_VAR = "UNIFICATORE_OBSIDIAN_TOOLS_DIR"


@dataclass(frozen=True)
class ObsidianLink:
    target: str
    label: str
    is_embed: bool


@dataclass(frozen=True)
class BuildResult:
    output_pdf: Path
    included_notes: list[Path]


@dataclass(frozen=True)
class BuildProgress:
    stage: str
    message: str
    current: int | None = None
    total: int | None = None
    path: Path | None = None


@dataclass(frozen=True)
class ToolingStatus:
    pandoc_command: str | None
    pdf_engine_command: str | None
    requested_pdf_engine: str | None
    search_roots: tuple[Path, ...]


@dataclass(frozen=True)
class InstallPlan:
    package_manager: str
    packages: tuple[str, ...]
    commands: tuple[tuple[str, ...], ...]
    missing_tools: tuple[str, ...]
    notes: tuple[str, ...] = ()


class BuildError(RuntimeError):
    """Errore applicativo per la generazione del PDF."""


def detect_vault_root(index_file: Path) -> Path:
    index_file = index_file.resolve()
    for candidate in (index_file.parent, *index_file.parents):
        if (candidate / ".obsidian").is_dir():
            return candidate
    return index_file.parent


def extract_obsidian_links(text: str) -> list[ObsidianLink]:
    links: list[ObsidianLink] = []
    for match in WIKILINK_RE.finditer(text):
        raw_target = match.group(2).strip()
        target, _, raw_label = raw_target.partition("|")
        target = target.strip()
        label = raw_label.strip() or _default_label(target)
        links.append(
            ObsidianLink(
                target=target,
                label=label,
                is_embed=bool(match.group(1)),
            )
        )
    return links


def collect_note_graph(index_file: Path, vault_root: Path) -> list[Path]:
    visited: set[Path] = set()
    ordered: list[Path] = []

    def visit(note_path: Path) -> None:
        resolved = note_path.resolve()
        if resolved in visited:
            return

        visited.add(resolved)
        ordered.append(resolved)

        text = resolved.read_text(encoding="utf-8")
        for link in extract_obsidian_links(text):
            linked_note = resolve_note_target(link.target, resolved.parent, vault_root)
            if linked_note is None:
                continue
            if linked_note.suffix.lower() != ".md":
                continue
            visit(linked_note)

        for _, href in extract_markdown_links(text):
            linked_note = resolve_standard_link(href, resolved.parent, vault_root)
            if linked_note is None:
                continue
            if linked_note.suffix.lower() != ".md":
                continue
            visit(linked_note)

    visit(index_file)
    return ordered


def build_pdf(
    index_file: Path,
    output_pdf: Path | None = None,
    vault_root: Path | None = None,
    pdf_engine: str | None = None,
    pandoc_path: Path | str | None = None,
    pdf_engine_path: Path | str | None = None,
    keep_temp: bool = False,
    extra_pandoc_args: list[str] | None = None,
    progress_callback: Callable[[BuildProgress], None] | None = None,
) -> BuildResult:
    index_file = index_file.resolve()
    if not index_file.is_file():
        raise BuildError(f"Il file indice non esiste: {index_file}")
    if index_file.suffix.lower() != ".md":
        raise BuildError("Il file indice deve essere un Markdown `.md`.")

    tooling = inspect_tooling(
        index_file=index_file,
        pdf_engine=pdf_engine,
        pandoc_path=pandoc_path,
        pdf_engine_path=pdf_engine_path,
    )
    if tooling.pandoc_command is None:
        raise BuildError(
            "Pandoc non e disponibile. Prova una di queste opzioni: "
            f"impostare `{PANDOC_ENV_VAR}`, usare `--pandoc-path`, oppure "
            "mettere il binario in `external/`, `tools/` o `.portable-tools/`."
        )

    if tooling.pdf_engine_command is None:
        missing = describe_missing_tools(tooling)
        raise BuildError(
            "Motore PDF non disponibile. "
            f"Mancano: {', '.join(missing)}. "
            "Installa un motore compatibile come `tectonic`, `xelatex`, `lualatex` o `pdflatex`, "
            f"usa `--pdf-engine-path`, `{PDF_ENGINE_ENV_VAR}` oppure una cartella locale "
            "`external/`, `tools/` o `.portable-tools/`"
        )

    selected_pdf_engine = tooling.pdf_engine_command
    notify_progress(
        progress_callback,
        BuildProgress(
            stage="collecting",
            message="Raccolta delle note collegate in corso...",
            path=index_file,
        ),
    )
    vault_root = (vault_root or detect_vault_root(index_file)).resolve()
    note_paths = collect_note_graph(index_file, vault_root)
    if not note_paths:
        raise BuildError("Nessuna nota trovata a partire dall'indice fornito.")
    notify_progress(
        progress_callback,
        BuildProgress(
            stage="collected",
            message=f"Raccolte {len(note_paths)} note da elaborare.",
            current=len(note_paths),
            total=len(note_paths),
        ),
    )

    output_pdf = (output_pdf or index_file.with_name(f"{index_file.stem}-unificato.pdf")).resolve()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    extra_pandoc_args = extra_pandoc_args or []

    temp_dir_ctx = tempfile.TemporaryDirectory(prefix="unificatore-obsidian-")
    temp_dir = Path(temp_dir_ctx.name)
    note_anchor_map = build_note_anchor_map(note_paths, vault_root)

    try:
        prepared_notes = prepare_note_copies(
            note_paths,
            vault_root,
            temp_dir,
            note_anchor_map=note_anchor_map,
            progress_callback=progress_callback,
        )
        latex_header_path = None
        revision_table_path = None
        if is_latex_pdf_engine(selected_pdf_engine):
            latex_header_path = write_latex_header(temp_dir)
            revision_table_path = write_latex_revision_table(temp_dir, index_file)
        notify_progress(
            progress_callback,
            BuildProgress(
                stage="rendering",
                message=f"Generazione PDF con {selected_pdf_engine or 'motore predefinito'}...",
                current=len(prepared_notes),
                total=len(prepared_notes),
                path=output_pdf,
            ),
        )
        command = build_pandoc_command(
            pandoc_command=tooling.pandoc_command,
            prepared_notes=prepared_notes,
            output_pdf=output_pdf,
            vault_root=vault_root,
            pdf_engine_command=selected_pdf_engine,
            extra_pandoc_args=extra_pandoc_args,
            latex_header_path=latex_header_path,
            revision_table_path=revision_table_path,
        )

        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            error_message = (
                decode_process_output(completed.stderr).strip()
                or decode_process_output(completed.stdout).strip()
            )
            raise BuildError(f"Pandoc ha restituito un errore:\n{error_message}")

        if keep_temp:
            preserved = output_pdf.with_suffix(".temp")
            if preserved.exists():
                shutil.rmtree(preserved)
            shutil.copytree(temp_dir, preserved)
    finally:
        temp_dir_ctx.cleanup()

    notify_progress(
        progress_callback,
        BuildProgress(
            stage="completed",
            message="PDF generato con successo.",
            current=len(note_paths),
            total=len(note_paths),
            path=output_pdf,
        ),
    )
    return BuildResult(output_pdf=output_pdf, included_notes=note_paths)


def prepare_note_copies(
    note_paths: list[Path],
    vault_root: Path,
    temp_dir: Path,
    note_anchor_map: dict[Path, str],
    progress_callback: Callable[[BuildProgress], None] | None = None,
) -> list[Path]:
    prepared: list[Path] = []
    notes_root = temp_dir / "notes"
    notes_root.mkdir(parents=True, exist_ok=True)
    total_notes = len(note_paths)

    for index, note_path in enumerate(note_paths):
        relative = safe_relative(note_path, vault_root)
        target_path = notes_root / relative
        target_path.parent.mkdir(parents=True, exist_ok=True)

        text = note_path.read_text(encoding="utf-8")
        if index > 0:
            text = strip_yaml_frontmatter(text)
        if index == 0:
            text = normalize_markdown_lists(text)
        text = rewrite_obsidian_syntax(
            text,
            note_path.parent,
            vault_root,
            note_anchor_map,
        )
        text = insert_note_anchor(text, note_anchor_map[note_path.resolve()])
        target_path.write_text(text, encoding="utf-8")
        prepared.append(target_path)
        notify_progress(
            progress_callback,
            BuildProgress(
                stage="preparing",
                message=f"Preparazione nota {index + 1} di {total_notes}",
                current=index + 1,
                total=total_notes,
                path=note_path,
            ),
        )

    return prepared


def build_pandoc_command(
    pandoc_command: str,
    prepared_notes: list[Path],
    output_pdf: Path,
    vault_root: Path,
    pdf_engine_command: str | None,
    extra_pandoc_args: list[str],
    latex_header_path: Path | None = None,
    revision_table_path: Path | None = None,
) -> list[str]:
    resource_parts = [str(vault_root)]
    command = [
        pandoc_command,
        "--standalone",
        "--toc",
        "--toc-depth",
        DEFAULT_TOC_DEPTH,
        "--metadata",
        f"toc-title={DEFAULT_TOC_TITLE}",
        "--from",
        "gfm+yaml_metadata_block+bracketed_spans",
        "--variable",
        f"papersize:{DEFAULT_PAPER_SIZE}",
        "--variable",
        f"fontsize:{DEFAULT_FONT_SIZE}",
        "--variable",
        f"mainfont:{DEFAULT_MAIN_FONT}",
        "--variable",
        f"sansfont:{DEFAULT_SANS_FONT}",
        "--variable",
        f"linestretch:{DEFAULT_LINE_STRETCH}",
        "--resource-path",
        os.pathsep.join(resource_parts),
        "-o",
        str(output_pdf),
    ]
    for geometry_option in DEFAULT_GEOMETRY_OPTIONS:
        command.extend(["--variable", f"geometry:{geometry_option}"])
    if pdf_engine_command:
        command.extend(["--pdf-engine", pdf_engine_command])
    if latex_header_path is not None:
        command.extend(["--include-in-header", str(latex_header_path)])
    if revision_table_path is not None:
        command.extend(["--include-before-body", str(revision_table_path)])
    command.extend(extra_pandoc_args)
    command.extend(str(path) for path in prepared_notes)
    return command


def detect_pdf_engine(search_roots: list[Path] | None = None) -> str | None:
    for engine in PREFERRED_PDF_ENGINES:
        resolved = resolve_command(
            engine,
            env_var=PDF_ENGINE_ENV_VAR,
            search_roots=search_roots,
        )
        if resolved is not None:
            return resolved
    return None


def inspect_tooling(
    index_file: Path | None = None,
    pdf_engine: str | None = None,
    pandoc_path: Path | str | None = None,
    pdf_engine_path: Path | str | None = None,
) -> ToolingStatus:
    search_roots = tuple(build_tool_search_roots(index_file))
    pandoc_command = resolve_command(
        "pandoc",
        env_var=PANDOC_ENV_VAR,
        search_roots=list(search_roots),
        explicit_path=pandoc_path,
    )
    if pdf_engine_path is not None:
        pdf_engine_command = resolve_explicit_command(pdf_engine_path)
    elif pdf_engine:
        pdf_engine_command = resolve_command(
            pdf_engine,
            env_var=PDF_ENGINE_ENV_VAR,
            search_roots=list(search_roots),
        )
    else:
        pdf_engine_command = detect_pdf_engine(list(search_roots))

    return ToolingStatus(
        pandoc_command=pandoc_command,
        pdf_engine_command=pdf_engine_command,
        requested_pdf_engine=pdf_engine,
        search_roots=search_roots,
    )


def describe_missing_tools(tooling: ToolingStatus) -> tuple[str, ...]:
    missing: list[str] = []
    if tooling.pandoc_command is None:
        missing.append("pandoc")
    if tooling.pdf_engine_command is None:
        if tooling.requested_pdf_engine:
            missing.append(tooling.requested_pdf_engine)
        else:
            missing.append("motore PDF LaTeX (tectonic/xelatex/lualatex/pdflatex)")
    return tuple(missing)


def build_linux_install_plan(tooling: ToolingStatus) -> InstallPlan | None:
    if not sys.platform.startswith("linux"):
        return None

    missing_tools = describe_missing_tools(tooling)
    if not missing_tools:
        return None

    package_manager = detect_linux_package_manager()
    if package_manager is None:
        return None

    packages = linux_packages_for_missing_tools(package_manager, tooling)
    if not packages:
        return None

    sudo = () if is_running_as_root() else ("sudo",)
    if package_manager == "apt-get":
        commands = (
            (*sudo, "apt-get", "update"),
            (*sudo, "apt-get", "install", "-y", *packages),
        )
    elif package_manager in {"dnf", "yum"}:
        commands = ((*sudo, package_manager, "install", "-y", *packages),)
    elif package_manager == "pacman":
        commands = ((*sudo, "pacman", "-Sy", "--needed", *packages),)
    elif package_manager == "zypper":
        commands = ((*sudo, "zypper", "install", "-y", *packages),)
    else:
        return None

    notes = (
        "Pandoc converte Markdown in PDF.",
        "Il motore LaTeX serve a renderizzare intestazione, footer, font, tabelle e immagini.",
    )
    return InstallPlan(
        package_manager=package_manager,
        packages=tuple(packages),
        commands=commands,
        missing_tools=missing_tools,
        notes=notes,
    )


def detect_linux_package_manager() -> str | None:
    for command in ("apt-get", "dnf", "yum", "pacman", "zypper"):
        if shutil.which(command):
            return command
    return None


def linux_packages_for_missing_tools(package_manager: str, tooling: ToolingStatus) -> tuple[str, ...]:
    packages: list[str] = []
    if tooling.pandoc_command is None:
        packages.append("pandoc")

    if tooling.pdf_engine_command is None:
        engine_packages = linux_pdf_engine_packages(package_manager, tooling.requested_pdf_engine)
        packages.extend(engine_packages)

    return tuple(dict.fromkeys(packages))


def linux_pdf_engine_packages(package_manager: str, requested_engine: str | None) -> tuple[str, ...]:
    default_engine = "xelatex" if package_manager in {"dnf", "yum"} else "tectonic"
    engine = tool_stem(requested_engine or default_engine)
    if package_manager == "apt-get":
        if engine == "tectonic":
            return ("tectonic",)
        if engine == "pdflatex":
            return ("texlive-latex-base", "texlive-latex-extra", "texlive-fonts-recommended")
        if engine == "lualatex":
            return ("texlive-luatex", "texlive-latex-extra", "texlive-fonts-recommended")
        return ("texlive-xetex", "texlive-latex-extra", "texlive-fonts-recommended")
    if package_manager in {"dnf", "yum"}:
        if engine == "pdflatex":
            return ("texlive-scheme-basic", "texlive-collection-latexextra", "texlive-collection-fontsrecommended")
        if engine == "lualatex":
            return ("texlive-luatex", "texlive-collection-latexextra", "texlive-collection-fontsrecommended")
        return ("texlive-xetex", "texlive-collection-latexextra", "texlive-collection-fontsrecommended")
    if package_manager == "pacman":
        if engine == "tectonic":
            return ("tectonic",)
        return ("texlive-bin", "texlive-latexextra", "texlive-fontsrecommended")
    if package_manager == "zypper":
        if engine == "tectonic":
            return ("tectonic",)
        return ("texlive-xetex", "texlive-latexextra", "texlive-fontsrecommended")
    return ()


def is_running_as_root() -> bool:
    geteuid = getattr(os, "geteuid", None)
    return bool(geteuid is not None and geteuid() == 0)


def build_note_anchor_map(note_paths: list[Path], vault_root: Path) -> dict[Path, str]:
    note_anchor_map: dict[Path, str] = {}
    used_anchors: set[str] = set()

    for note_path in note_paths:
        relative = safe_relative(note_path, vault_root).with_suffix("").as_posix()
        base_anchor = slugify_anchor(relative) or "nota"
        anchor = f"note-{base_anchor}"
        suffix = 2
        while anchor in used_anchors:
            anchor = f"note-{base_anchor}-{suffix}"
            suffix += 1
        resolved = note_path.resolve()
        note_anchor_map[resolved] = anchor
        used_anchors.add(anchor)

    return note_anchor_map


def is_latex_pdf_engine(pdf_engine: str | None) -> bool:
    if pdf_engine is None:
        return True
    return tool_stem(pdf_engine) in {"pdflatex", "xelatex", "lualatex", "latexmk", "tectonic"}


def write_latex_header(temp_dir: Path, list_depth: int = DEFAULT_LATEX_LIST_DEPTH) -> Path:
    header_path = temp_dir / "pandoc-header.tex"
    logo_path = temp_dir / BABEL_LOGO_FILENAME
    logo_path.write_bytes(base64.b64decode(BABEL_LOGO_BASE64))
    enumerate_labels = [
        r"\arabic*.",
        r"\alph*.",
        r"\roman*.",
        r"\Alph*.",
        r"\arabic*.",
        r"\alph*.",
        r"\roman*.",
        r"\Alph*.",
        r"\arabic*.",
    ]
    itemize_labels = [
        r"$\bullet$",
        r"--",
        r"*",
        r"$\cdot$",
        r"$\bullet$",
        r"--",
        r"*",
        r"$\cdot$",
        r"$\bullet$",
    ]
    lines = [
        r"\usepackage{iftex}",
        r"\ifPDFTeX",
        r"  \usepackage[scaled=0.98]{helvet}",
        r"  \renewcommand{\familydefault}{\sfdefault}",
        r"\else",
        r"  \usepackage{fontspec}",
        r"  \setmainfont{Latin Modern Sans}",
        r"  \setsansfont{Latin Modern Sans}",
        r"\fi",
        r"\usepackage{xcolor}",
        r"\usepackage{fancyhdr}",
        r"\usepackage{lastpage}",
        r"\usepackage{titlesec}",
        r"\usepackage{enumitem}",
        r"\usepackage{etoolbox}",
        r"\usepackage{longtable,booktabs,array,tabularx,ltablex,graphicx}",
        r"\keepXColumns",
        r"\definecolor{babelgray}{RGB}{128,128,128}",
        r"\AtBeginDocument{\ifdefined\hypersetup\hypersetup{colorlinks=false,pdfborder={0 0 0},linkcolor=black,urlcolor=black,citecolor=black}\fi}",
        r"\setlength{\parindent}{0pt}",
        r"\setlength{\parskip}{4pt plus 1pt minus 1pt}",
        r"\setlength{\LTleft}{0pt}",
        r"\setlength{\LTright}{0pt}",
        r"\setlength{\tabcolsep}{4pt}",
        r"\renewcommand{\arraystretch}{1.1}",
        r"\setlength{\emergencystretch}{3em}",
        r"\pretolerance=1000",
        r"\tolerance=2000",
        r"\hfuzz=2pt",
        r"\vfuzz=2pt",
        r"\AtBeginEnvironment{longtable}{\footnotesize}",
        r"\AtBeginEnvironment{tabular}{\footnotesize}",
        r"\AtBeginEnvironment{table}{\footnotesize}",
        r"\AtBeginEnvironment{figure}{\centering}",
        r"\makeatletter",
        r"\def\maxwidth{\ifdim\Gin@nat@width>\linewidth\linewidth\else\Gin@nat@width\fi}",
        r"\def\maxheight{\ifdim\Gin@nat@height>\textheight\textheight\else\Gin@nat@height\fi}",
        r"\makeatother",
        r"\setkeys{Gin}{width=\maxwidth,height=\maxheight,keepaspectratio}",
        r"\pagestyle{fancy}",
        r"\fancyhf{}",
        rf"\fancyhead[L]{{\includegraphics[width=36.5mm]{{{latex_path(logo_path)}}}}}",
        rf"\fancyhead[C]{{\begin{{minipage}}[b]{{66mm}}\centering\fontsize{{12}}{{13}}\selectfont\bfseries {latex_escape(BABEL_HEADER_TITLE)}\\[-1pt]{latex_escape(BABEL_HEADER_SUBTITLE)}\end{{minipage}}}}",
        rf"\fancyhead[R]{{\begin{{minipage}}[b]{{25mm}}\raggedleft\fontsize{{10}}{{12}}\selectfont\itshape {latex_escape(BABEL_HEADER_NOTE)}\end{{minipage}}}}",
        r"\fancyfoot[R]{\fontsize{8}{10}\selectfont Pagina \thepage\ di \pageref{LastPage}}",
        r"\renewcommand{\headrulewidth}{0.5pt}",
        r"\renewcommand{\footrulewidth}{0.5pt}",
        r"\fancypagestyle{plain}{%",
        r"  \fancyhf{}%",
        rf"  \fancyhead[L]{{\includegraphics[width=36.5mm]{{{latex_path(logo_path)}}}}}%",
        rf"  \fancyhead[C]{{\begin{{minipage}}[b]{{66mm}}\centering\fontsize{{12}}{{13}}\selectfont\bfseries {latex_escape(BABEL_HEADER_TITLE)}\\[-1pt]{latex_escape(BABEL_HEADER_SUBTITLE)}\end{{minipage}}}}%",
        rf"  \fancyhead[R]{{\begin{{minipage}}[b]{{25mm}}\raggedleft\fontsize{{10}}{{12}}\selectfont\itshape {latex_escape(BABEL_HEADER_NOTE)}\end{{minipage}}}}%",
        r"  \fancyfoot[R]{\fontsize{8}{10}\selectfont Pagina \thepage\ di \pageref{LastPage}}%",
        r"  \renewcommand{\headrulewidth}{0.5pt}%",
        r"  \renewcommand{\footrulewidth}{0.5pt}%",
        r"}",
        r"\AtBeginDocument{\pagestyle{fancy}\thispagestyle{fancy}}",
        r"\titleformat{\section}{\centering\bfseries\fontsize{20}{24}\selectfont}{\thesection}{1em}{}",
        r"\titleformat{\subsection}{\bfseries\fontsize{12}{14}\selectfont}{\thesubsection}{0.75em}{}",
        r"\titleformat{\subsubsection}{\bfseries\fontsize{11}{13}\selectfont}{\thesubsubsection}{0.75em}{}",
        r"\titlespacing*{\section}{0pt}{18pt}{12pt}",
        r"\titlespacing*{\subsection}{0pt}{14pt}{6pt}",
        r"\titlespacing*{\subsubsection}{0pt}{10pt}{4pt}",
        r"\makeatletter",
        r"\renewcommand{\maketitle}{%",
        r"  \thispagestyle{fancy}%",
        r"  \vspace*{118pt}%",
        r"  \begin{center}%",
        r"  \setlength{\fboxsep}{10pt}%",
        r"  \colorbox{babelgray}{%",
        r"    \begin{minipage}{\dimexpr\textwidth-20pt\relax}%",
        r"    \centering\color{white}\bfseries\fontsize{18}{24}\selectfont\@title%",
        r"    \end{minipage}%",
        r"  }%",
        r"  \end{center}%",
        r"  \vspace{18pt}%",
        r"}",
        r"\makeatother",
        rf"\setlistdepth{{{list_depth}}}",
        rf"\renewlist{{itemize}}{{itemize}}{{{list_depth}}}",
        rf"\renewlist{{enumerate}}{{enumerate}}{{{list_depth}}}",
    ]
    for index in range(1, list_depth + 1):
        item_label = itemize_labels[(index - 1) % len(itemize_labels)]
        enum_label = enumerate_labels[(index - 1) % len(enumerate_labels)]
        lines.append(rf"\setlist[itemize,{index}]{{label={item_label},leftmargin=*}}")
        lines.append(rf"\setlist[enumerate,{index}]{{label={enum_label},leftmargin=*}}")
    header_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return header_path


def latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)


def latex_path(path: Path) -> str:
    return path.as_posix().replace("\\", "/")


def write_latex_revision_table(temp_dir: Path, index_file: Path, revision_date: date | None = None) -> Path:
    revision_path = temp_dir / "pandoc-revision-table.tex"
    version = extract_document_version(index_file)
    formatted_date = (revision_date or date.today()).strftime("%d/%m/%Y")
    lines = [
        rf"\section*{{{latex_escape(REVISION_TABLE_TITLE)}}}",
        rf"\addcontentsline{{toc}}{{section}}{{{latex_escape(REVISION_TABLE_TITLE)}}}",
        r"\begin{longtable}{|p{24mm}|p{28mm}|p{78mm}|p{36mm}|}",
        r"\hline",
        r"\textbf{Versione} & \textbf{Data} & \textbf{Descrizione} & \textbf{Autore} \\ \hline",
        rf"{latex_escape(version)} & {latex_escape(formatted_date)} & {latex_escape(REVISION_TABLE_DESCRIPTION)} & {latex_escape(REVISION_TABLE_AUTHOR)} \\ \hline",
        r"\end{longtable}",
        r"\newpage",
    ]
    revision_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return revision_path


def extract_document_version(index_file: Path) -> str:
    match = re.search(r"(?:^|[.\s_-])v?(\d+(?:\.\d+)+)(?:$|[.\s_-])", index_file.stem, re.IGNORECASE)
    if match is None:
        return "1.0"
    return match.group(1)


def normalize_markdown_lists(text: str) -> str:
    lines = text.splitlines(keepends=True)
    normalized: list[str] = []
    inside_fence = False

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(chr(96) * 3) or stripped.startswith("~~~"):
            inside_fence = not inside_fence
            normalized.append(line)
            continue

        if inside_fence:
            normalized.append(line)
            continue

        normalized.append(normalize_ordered_list_marker(line))

    return "".join(normalized)


def normalize_ordered_list_marker(line: str) -> str:
    line_ending = ""
    body = line
    if body.endswith("\r\n"):
        body = body[:-2]
        line_ending = "\r\n"
    elif body.endswith("\n"):
        body = body[:-1]
        line_ending = "\n"

    match = re.match(r"^([ \t]*)(\d+)\)(\s+)(.*)$", body)
    if match is None:
        return line
    indent = match.group(1).replace("\t", "    ")
    return f"{indent}{match.group(2)}. {match.group(4)}{line_ending}"


def insert_note_anchor(text: str, anchor: str) -> str:
    anchor_markup = f"[]{{#{anchor}}}"
    lines = text.splitlines(keepends=True)
    if not lines:
        return f"{anchor_markup}\n"

    if lines[0].strip() != "---":
        return f"{anchor_markup}\n\n{text}"

    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            before = "".join(lines[: index + 1])
            after = "".join(lines[index + 1 :])
            separator = "" if after.startswith("\n") else "\n"
            return f"{before}{separator}{anchor_markup}\n\n{after}"

    return f"{anchor_markup}\n\n{text}"


def rewrite_obsidian_syntax(
    text: str,
    current_dir: Path,
    vault_root: Path,
    note_anchor_map: dict[Path, str],
) -> str:
    lines = text.splitlines(keepends=True)
    inside_fence = False
    rewritten: list[str] = []

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            inside_fence = not inside_fence
            rewritten.append(line)
            continue

        if inside_fence:
            rewritten.append(line)
            continue

        updated = WIKILINK_RE.sub(
            lambda match: _replace_wikilink(match, current_dir, vault_root, note_anchor_map),
            line,
        )
        updated = MARKDOWN_IMAGE_RE.sub(
            lambda match: _replace_markdown_image(match, current_dir, vault_root),
            updated,
        )
        updated = MARKDOWN_LINK_RE.sub(
            lambda match: _replace_markdown_link(match, current_dir, vault_root, note_anchor_map),
            updated,
        )
        rewritten.append(updated)

    return "".join(rewritten)


def extract_markdown_links(text: str) -> list[tuple[str, str]]:
    return [(match.group(1), match.group(2).strip()) for match in MARKDOWN_LINK_RE.finditer(text)]


def strip_yaml_frontmatter(text: str) -> str:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text

    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "".join(lines[index + 1 :])
    return text


def resolve_note_target(target: str, current_dir: Path, vault_root: Path) -> Path | None:
    cleaned = strip_target_fragment(target)
    candidates = candidate_paths(cleaned, current_dir, vault_root, markdown_only=True)
    return first_existing_path(candidates)


def resolve_asset_target(target: str, current_dir: Path, vault_root: Path) -> Path | None:
    cleaned = strip_target_fragment(target)
    candidates = candidate_paths(cleaned, current_dir, vault_root, markdown_only=False)
    return first_existing_path(candidates)


def resolve_standard_link(href: str, current_dir: Path, vault_root: Path) -> Path | None:
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", href):
        return None
    if href.startswith("#"):
        return None
    return resolve_asset_target(href, current_dir, vault_root)


def candidate_paths(
    target: str,
    current_dir: Path,
    vault_root: Path,
    markdown_only: bool,
) -> list[Path]:
    raw_path = Path(target)
    candidates: list[Path] = []

    def append_candidate(path: Path) -> None:
        resolved_candidate = path.resolve()
        if resolved_candidate not in candidates:
            candidates.append(resolved_candidate)

    if raw_path.suffix:
        append_candidate(current_dir / raw_path)
        append_candidate(vault_root / raw_path)
    else:
        append_candidate(current_dir / raw_path.with_suffix(".md"))
        append_candidate(vault_root / raw_path.with_suffix(".md"))
        if not markdown_only:
            append_candidate(current_dir / raw_path)
            append_candidate(vault_root / raw_path)

    base_name = raw_path.name
    if base_name:
        pattern = f"{base_name}.md" if markdown_only and not raw_path.suffix else base_name
        for candidate in vault_root.rglob(pattern):
            append_candidate(candidate)

    return candidates


def first_existing_path(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def safe_relative(path: Path, base: Path) -> Path:
    try:
        return path.resolve().relative_to(base.resolve())
    except ValueError:
        return Path(path.name)


def strip_target_fragment(target: str) -> str:
    without_heading = target.split("#", 1)[0]
    return without_heading.split("^", 1)[0].strip()


def _replace_wikilink(
    match: re.Match[str],
    current_dir: Path,
    vault_root: Path,
    note_anchor_map: dict[Path, str],
) -> str:
    is_embed = bool(match.group(1))
    raw_target = match.group(2).strip()
    target, _, raw_label = raw_target.partition("|")
    target = target.strip()
    label = raw_label.strip() or _default_label(target)

    resolved = resolve_asset_target(target, current_dir, vault_root)
    if resolved is None:
        return label

    if resolved.suffix.lower() == ".md":
        anchor = note_anchor_map.get(resolved.resolve())
        if anchor is None:
            return label
        return f"[{label}](#{anchor})"

    if is_embed and resolved.suffix.lower() in IMAGE_SUFFIXES:
        return f"![{label}](<{resolved.as_posix()}>)"

    return f"[{label}](<{resolved.as_posix()}>)"


def _replace_markdown_link(
    match: re.Match[str],
    current_dir: Path,
    vault_root: Path,
    note_anchor_map: dict[Path, str],
) -> str:
    label = match.group(1)
    href = match.group(2).strip()

    resolved = resolve_standard_link(href, current_dir, vault_root)
    if resolved is None:
        return match.group(0)

    if resolved.suffix.lower() == ".md":
        anchor = note_anchor_map.get(resolved.resolve())
        if anchor is None:
            return label
        return f"[{label}](#{anchor})"

    return f"[{label}](<{resolved.as_posix()}>)"


def _replace_markdown_image(match: re.Match[str], current_dir: Path, vault_root: Path) -> str:
    label = match.group(1)
    href = match.group(2).strip()

    resolved = resolve_standard_link(href, current_dir, vault_root)
    if resolved is None or resolved.suffix.lower() == ".md":
        return match.group(0)

    return f"![{label}](<{resolved.as_posix()}>)"


def _default_label(target: str) -> str:
    cleaned = strip_target_fragment(target)
    return Path(cleaned).stem or cleaned


def slugify_anchor(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return slug.strip("-")


def decode_process_output(output: bytes | str | None) -> str:
    if output is None:
        return ""
    if isinstance(output, str):
        return output
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return output.decode(encoding)
        except UnicodeDecodeError:
            continue
    return output.decode("utf-8", errors="replace")


def notify_progress(
    progress_callback: Callable[[BuildProgress], None] | None,
    event: BuildProgress,
) -> None:
    if progress_callback is not None:
        progress_callback(event)


def build_tool_search_roots(index_file: Path | None = None) -> list[Path]:
    roots: list[Path] = []
    configured_tools_dir = os.environ.get(TOOLS_DIR_ENV_VAR)
    package_dir = Path(__file__).resolve().parent
    package_root = package_dir.parents[1] if len(package_dir.parents) > 1 else package_dir
    script_dir = Path(sys.argv[0]).resolve().parent if sys.argv and sys.argv[0] else Path.cwd()

    for candidate in (
        Path.cwd(),
        script_dir,
        package_root,
        package_dir,
        Path(configured_tools_dir) if configured_tools_dir else None,
        index_file.resolve().parent if index_file is not None else None,
    ):
        if candidate is None:
            continue
        resolved = candidate.resolve()
        if resolved not in roots:
            roots.append(resolved)

    return roots


def resolve_command(
    command_name: str,
    env_var: str | None,
    search_roots: list[Path] | None = None,
    explicit_path: Path | str | None = None,
) -> str | None:
    if explicit_path is not None:
        return resolve_explicit_command(explicit_path)

    if env_var:
        configured = os.environ.get(env_var)
        if configured:
            resolved = resolve_explicit_command(configured)
            if resolved is not None:
                return resolved

    for root in search_roots or []:
        for candidate in bundled_executable_candidates(root, command_name):
            if candidate.is_file():
                return str(candidate.resolve())

    return shutil.which(command_name)


def resolve_explicit_command(value: Path | str) -> str | None:
    raw = str(value).strip()
    if not raw:
        return None

    direct_candidate = Path(raw)
    for candidate in (direct_candidate, *with_platform_suffix(direct_candidate)):
        if candidate.is_file():
            return str(candidate.resolve())

    return shutil.which(raw)


def bundled_executable_candidates(root: Path, command_name: str) -> list[Path]:
    candidates: list[Path] = []
    executable_names = executable_name_candidates(command_name)
    relative_dirs = (
        Path(),
        Path("bin"),
        Path(command_name),
        Path(command_name) / "bin",
    )
    base_dirs = [Path()] + [Path(name) for name in PORTABLE_TOOL_DIR_NAMES]

    for base_dir in base_dirs:
        for relative_dir in relative_dirs:
            for executable_name in executable_names:
                candidate = root / base_dir / relative_dir / executable_name
                if candidate not in candidates:
                    candidates.append(candidate)

    return candidates


def executable_name_candidates(command_name: str) -> list[str]:
    path = Path(command_name)
    if path.suffix:
        return [path.name]
    names = [path.name]
    exe_name = f"{path.name}.exe"
    if exe_name not in names:
        names.append(exe_name)
    return names


def with_platform_suffix(path: Path) -> list[Path]:
    if path.suffix or os.name != "nt":
        return []
    return [path.with_suffix(".exe")]


def tool_stem(command: str) -> str:
    normalized = command.replace("\\", "/")
    return Path(normalized).stem.lower()
