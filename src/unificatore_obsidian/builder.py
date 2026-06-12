from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import os
import re
import shutil
import subprocess
import tempfile


WIKILINK_RE = re.compile(r"(!)?\[\[([^\]]+)\]\]")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"}
DEFAULT_LATEX_LIST_DEPTH = 9
PREFERRED_PDF_ENGINES = ("xelatex", "lualatex", "pdflatex")
DEFAULT_PAPER_SIZE = "a4"
DEFAULT_FONT_SIZE = "10pt"
DEFAULT_PAGE_MARGIN = "18mm"
DEFAULT_LINE_STRETCH = "1.05"


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
    keep_temp: bool = False,
    extra_pandoc_args: list[str] | None = None,
    progress_callback: Callable[[BuildProgress], None] | None = None,
) -> BuildResult:
    index_file = index_file.resolve()
    if not index_file.is_file():
        raise BuildError(f"Il file indice non esiste: {index_file}")
    if index_file.suffix.lower() != ".md":
        raise BuildError("Il file indice deve essere un Markdown `.md`.")

    if shutil.which("pandoc") is None:
        raise BuildError(
            "Pandoc non e disponibile nel PATH. Installalo e riprova."
        )

    selected_pdf_engine = pdf_engine or detect_pdf_engine()
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
        if is_latex_pdf_engine(selected_pdf_engine):
            latex_header_path = write_latex_header(temp_dir)
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
            prepared_notes=prepared_notes,
            output_pdf=output_pdf,
            vault_root=vault_root,
            pdf_engine=selected_pdf_engine,
            extra_pandoc_args=extra_pandoc_args,
            latex_header_path=latex_header_path,
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
    prepared_notes: list[Path],
    output_pdf: Path,
    vault_root: Path,
    pdf_engine: str | None,
    extra_pandoc_args: list[str],
    latex_header_path: Path | None = None,
) -> list[str]:
    resource_parts = [str(vault_root)]
    command = [
        "pandoc",
        "--standalone",
        "--from",
        "gfm+yaml_metadata_block+bracketed_spans",
        "--variable",
        f"papersize:{DEFAULT_PAPER_SIZE}",
        "--variable",
        f"fontsize:{DEFAULT_FONT_SIZE}",
        "--variable",
        f"geometry:margin={DEFAULT_PAGE_MARGIN}",
        "--variable",
        f"linestretch:{DEFAULT_LINE_STRETCH}",
        "--resource-path",
        os.pathsep.join(resource_parts),
        "-o",
        str(output_pdf),
    ]
    if pdf_engine:
        command.extend(["--pdf-engine", pdf_engine])
    if latex_header_path is not None:
        command.extend(["--include-in-header", str(latex_header_path)])
    command.extend(extra_pandoc_args)
    command.extend(str(path) for path in prepared_notes)
    return command


def detect_pdf_engine() -> str | None:
    for engine in PREFERRED_PDF_ENGINES:
        if shutil.which(engine):
            return engine
    return None


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
    return pdf_engine.lower() in {"pdflatex", "xelatex", "lualatex", "latexmk", "tectonic"}


def write_latex_header(temp_dir: Path, list_depth: int = DEFAULT_LATEX_LIST_DEPTH) -> Path:
    header_path = temp_dir / "pandoc-header.tex"
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
        r"\usepackage{enumitem}",
        r"\usepackage{etoolbox}",
        r"\usepackage{longtable,booktabs,array,tabularx,ltablex,graphicx}",
        r"\keepXColumns",
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
        rf"\setlistdepth{{{list_depth}}}",
        rf"\renewlist{{itemize}}{{itemize}}{{{list_depth}}}",
        rf"\renewlist{{enumerate}}{{enumerate}}{{{list_depth}}}",
    ]
    for index in range(1, list_depth + 1):
        item_label = itemize_labels[(index - 1) % len(itemize_labels)]
        enum_label = enumerate_labels[(index - 1) % len(enumerate_labels)]
        lines.append(rf"\setlist[itemize,{index}]{{label={item_label}}}")
        lines.append(rf"\setlist[enumerate,{index}]{{label={enum_label}}}")
    header_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return header_path


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
