from datetime import date
from pathlib import Path
import tempfile
import unittest

from unificatore_obsidian.builder import (
    BuildProgress,
    ToolingStatus,
    PANDOC_ENV_VAR,
    PDF_ENGINE_ENV_VAR,
    build_note_anchor_map,
    build_revision_table_markdown,
    build_pandoc_command,
    build_tool_search_roots,
    build_linux_install_plan,
    collect_note_graph,
    decode_process_output,
    detect_vault_root,
    detect_pdf_engine,
    describe_missing_tools,
    extract_document_version,
    extract_obsidian_links,
    inspect_tooling,
    insert_note_anchor,
    is_latex_pdf_engine,
    normalize_markdown_lists,
    notify_progress,
    prepare_note_copies,
    resolve_command,
    rewrite_obsidian_syntax,
    write_latex_header,
)
from unittest.mock import patch


class BuilderTests(unittest.TestCase):
    def test_extract_obsidian_links(self) -> None:
        links = extract_obsidian_links("Vai a [[Note/Capitolo 1|Capitolo]] e ![[img/test.png]]")
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0].target, "Note/Capitolo 1")
        self.assertEqual(links[0].label, "Capitolo")
        self.assertFalse(links[0].is_embed)
        self.assertTrue(links[1].is_embed)

    def test_detect_vault_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".obsidian").mkdir()
            docs = root / "docs"
            docs.mkdir()
            index = docs / "indice.md"
            index.write_text("# Indice\n", encoding="utf-8")
            self.assertEqual(detect_vault_root(index), root)

    def test_collect_note_graph_depth_first_without_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".obsidian").mkdir()
            (root / "indice.md").write_text("[[A]]\n[[B]]\n", encoding="utf-8")
            (root / "A.md").write_text("[[B]]\n[[C]]\n", encoding="utf-8")
            (root / "B.md").write_text("# B\n", encoding="utf-8")
            (root / "C.md").write_text("# C\n", encoding="utf-8")

            ordered = collect_note_graph(root / "indice.md", root)
            self.assertEqual([note.name for note in ordered], ["indice.md", "A.md", "B.md", "C.md"])

    def test_collect_note_graph_avoids_circular_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".obsidian").mkdir()
            (root / "indice.md").write_text("[[A]]\n", encoding="utf-8")
            (root / "A.md").write_text("[[B]]\n", encoding="utf-8")
            (root / "B.md").write_text("[[A]]\n[[C]]\n", encoding="utf-8")
            (root / "C.md").write_text("# C\n", encoding="utf-8")

            ordered = collect_note_graph(root / "indice.md", root)
            self.assertEqual([note.name for note in ordered], ["indice.md", "A.md", "B.md", "C.md"])

    def test_rewrite_obsidian_syntax_converts_embeds_and_note_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / "docs"
            current.mkdir()
            image = root / "img test.png"
            image.write_bytes(b"fake")
            note = root / "Capitolo.md"
            note.write_text("# Capitolo\n", encoding="utf-8")
            note_anchor_map = {note.resolve(): "note-capitolo"}

            text = "Apri [[Capitolo|questo capitolo]] e ![[img test.png|Figura]].\n"
            rewritten = rewrite_obsidian_syntax(text, current, root, note_anchor_map)

            self.assertIn("[questo capitolo](#note-capitolo)", rewritten)
            self.assertIn("![Figura]", rewritten)
            self.assertIn("img test.png", rewritten)

    def test_rewrite_obsidian_syntax_converts_markdown_images(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / "docs"
            current.mkdir()
            image = root / "assets" / "diagram.png"
            image.parent.mkdir()
            image.write_bytes(b"fake")

            text = "![Schema](../assets/diagram.png)\n"
            rewritten = rewrite_obsidian_syntax(text, current, root, {})

            self.assertIn("![Schema]", rewritten)
            self.assertIn("diagram.png", rewritten)

    def test_rewrite_obsidian_syntax_converts_markdown_note_links_to_internal_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / "docs"
            current.mkdir()
            note = root / "Capitolo.md"
            note.write_text("# Capitolo\n", encoding="utf-8")
            note_anchor_map = {note.resolve(): "note-capitolo"}

            text = "[Vai al capitolo](../Capitolo.md)\n"
            rewritten = rewrite_obsidian_syntax(text, current, root, note_anchor_map)

            self.assertIn("[Vai al capitolo](#note-capitolo)", rewritten)

    def test_build_revision_table_markdown_uses_index_version(self) -> None:
        content = build_revision_table_markdown(
            Path("Indice Documentale Babel v1.2.3.md"),
            revision_date=date(2026, 6, 18),
        )

        self.assertIn("# Tabella revisioni", content)
        self.assertIn("| Versione | Data | Descrizione | Autore |", content)
        self.assertIn("| 1.2.3 | 18/06/2026 | Prima emissione del manuale unificato | Assistenza Tecnica |", content)
        self.assertTrue(content.endswith("\\newpage\n"))

    def test_extract_document_version_defaults_when_missing(self) -> None:
        self.assertEqual(extract_document_version(Path("Indice.md")), "1.0")

    def test_normalize_markdown_lists_converts_nested_parenthesis_markers(self) -> None:
        text = "1) [[Accesso babel]]\n\t1) [[Requisiti Tecnici del Browser]]\n"

        normalized = normalize_markdown_lists(text)

        self.assertEqual(
            normalized,
            "1. [[Accesso babel]]\n    1. [[Requisiti Tecnici del Browser]]\n",
        )

    def test_prepare_note_copies_prepends_revision_table_and_normalizes_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = root / "Indice Documentale Babel v1.0.0.md"
            note = root / "Capitolo.md"
            index.write_text("1) [[Capitolo]]\n\t1) [[Capitolo]]\n", encoding="utf-8")
            note.write_text("# Capitolo\n", encoding="utf-8")
            note_anchor_map = build_note_anchor_map([index, note], root)

            prepared = prepare_note_copies([index, note], root, root / "tmp", note_anchor_map)

            self.assertEqual(prepared[0].name, "00-tabella-revisioni.md")
            self.assertIn("| 1.0.0 |", prepared[0].read_text(encoding="utf-8"))
            index_copy = prepared[1].read_text(encoding="utf-8")
            self.assertIn("1. [Capitolo](#note-capitolo)", index_copy)
            self.assertIn("    1. [Capitolo](#note-capitolo)", index_copy)

    def test_build_note_anchor_map_generates_unique_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            note_a = root / "A.md"
            note_b = root / "sub" / "A.md"
            note_b.parent.mkdir()
            note_a.write_text("", encoding="utf-8")
            note_b.write_text("", encoding="utf-8")

            mapping = build_note_anchor_map([note_a, note_b], root)

            self.assertEqual(len(mapping), 2)
            self.assertNotEqual(mapping[note_a.resolve()], mapping[note_b.resolve()])

    def test_insert_note_anchor_preserves_frontmatter(self) -> None:
        text = "---\ntitle: Demo\n---\n# Titolo\n"
        anchored = insert_note_anchor(text, "note-demo")

        self.assertIn("[]{#note-demo}", anchored)
        self.assertTrue(anchored.startswith("---\ntitle: Demo\n---\n"))

    def test_write_latex_header_contains_extended_list_setup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            header = write_latex_header(Path(tmp), list_depth=6)
            content = header.read_text(encoding="utf-8")

            self.assertIn(r"\usepackage{fancyhdr}", content)
            self.assertIn(r"\usepackage{lastpage}", content)
            self.assertIn(r"\usepackage{enumitem}", content)
            self.assertIn(r"\usepackage{longtable,booktabs,array,tabularx,ltablex,graphicx}", content)
            self.assertIn(r"\fancyfoot[R]{\fontsize{8}{10}\selectfont Pagina \thepage\ di \pageref{LastPage}}", content)
            self.assertIn("babel-header-logo.jpg", content)
            self.assertIn(r"\setmainfont{Latin Modern Sans}", content)
            self.assertNotIn("Arial", content)
            self.assertIn(r"\AtBeginDocument{\ifdefined\hypersetup", content)
            self.assertIn(r"\setlength{\LTleft}{0pt}", content)
            self.assertIn(r"\setkeys{Gin}{width=\maxwidth,height=\maxheight,keepaspectratio}", content)
            self.assertIn(r"\setlistdepth{6}", content)
            self.assertIn(r"\renewlist{enumerate}{enumerate}{6}", content)
            self.assertIn(r"\setlist[enumerate,6]", content)

    def test_build_pandoc_command_includes_header_when_present(self) -> None:
        command = build_pandoc_command(
            pandoc_command="pandoc",
            prepared_notes=[Path("a.md"), Path("b.md")],
            output_pdf=Path("out.pdf"),
            vault_root=Path("vault"),
            pdf_engine_command="xelatex",
            extra_pandoc_args=[],
            latex_header_path=Path("header.tex"),
        )

        self.assertIn("--pdf-engine", command)
        self.assertIn("xelatex", command)
        self.assertIn("markdown+yaml_metadata_block+bracketed_spans+pipe_tables+raw_tex", command)
        self.assertIn("--toc", command)
        self.assertIn("--toc-depth", command)
        self.assertIn("toc-title=Sommario", command)
        self.assertIn("papersize:a4", command)
        self.assertIn("fontsize:10pt", command)
        self.assertIn("mainfont:Latin Modern Sans", command)
        self.assertIn("sansfont:Latin Modern Sans", command)
        self.assertIn("geometry:left=20mm", command)
        self.assertIn("geometry:top=38mm", command)
        self.assertIn("linestretch:1.05", command)
        self.assertIn("--include-in-header", command)
        self.assertIn("header.tex", command)

    def test_detect_pdf_engine_returns_none_or_known_engine(self) -> None:
        engine = detect_pdf_engine()
        self.assertIn(
            Path(engine).stem if engine is not None else None,
            {None, "tectonic", "xelatex", "lualatex", "pdflatex"},
        )

    def test_is_latex_pdf_engine(self) -> None:
        self.assertTrue(is_latex_pdf_engine(None))
        self.assertTrue(is_latex_pdf_engine("xelatex"))
        self.assertTrue(is_latex_pdf_engine(r"C:\tools\tectonic.exe"))
        self.assertFalse(is_latex_pdf_engine("wkhtmltopdf"))

    def test_notify_progress_invokes_callback(self) -> None:
        seen: list[BuildProgress] = []
        event = BuildProgress(stage="preparing", message="demo", current=1, total=3)

        notify_progress(seen.append, event)

        self.assertEqual(seen, [event])

    def test_decode_process_output_handles_non_utf8_bytes(self) -> None:
        self.assertEqual(decode_process_output(b"abc"), "abc")
        self.assertTrue(decode_process_output(b"\x8d").strip() != "")

    def test_resolve_command_finds_portable_tool_in_external_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            portable = root / "external" / "pandoc" / "pandoc.exe"
            portable.parent.mkdir(parents=True)
            portable.write_bytes(b"")

            resolved = resolve_command("pandoc", env_var=None, search_roots=[root])

            self.assertEqual(Path(resolved), portable.resolve())

    def test_inspect_tooling_prefers_explicit_and_environment_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pandoc = root / "pandoc.exe"
            engine = root / "tectonic.exe"
            pandoc.write_bytes(b"")
            engine.write_bytes(b"")

            with patch.dict("os.environ", {PANDOC_ENV_VAR: str(pandoc), PDF_ENGINE_ENV_VAR: str(engine)}):
                tooling = inspect_tooling(index_file=root / "indice.md")

            self.assertEqual(Path(tooling.pandoc_command), pandoc.resolve())
            self.assertEqual(Path(tooling.pdf_engine_command), engine.resolve())

    def test_inspect_tooling_reports_missing_requested_engine(self) -> None:
        with patch("unificatore_obsidian.builder.resolve_command", return_value=None):
            tooling = inspect_tooling(pdf_engine="xelatex")

        self.assertIsNone(tooling.pdf_engine_command)
        self.assertEqual(tooling.requested_pdf_engine, "xelatex")
        self.assertEqual(describe_missing_tools(tooling), ("pandoc", "xelatex"))

    def test_build_linux_install_plan_for_apt_missing_all_tools(self) -> None:
        tooling = ToolingStatus(
            pandoc_command=None,
            pdf_engine_command=None,
            requested_pdf_engine=None,
            search_roots=(),
        )

        with patch("sys.platform", "linux"), patch(
            "unificatore_obsidian.builder.detect_linux_package_manager", return_value="apt-get"
        ), patch("unificatore_obsidian.builder.is_running_as_root", return_value=True):
            plan = build_linux_install_plan(tooling)

        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(plan.package_manager, "apt-get")
        self.assertIn("pandoc", plan.packages)
        self.assertIn("tectonic", plan.packages)
        self.assertIn(("apt-get", "update"), plan.commands)
        self.assertIn(("apt-get", "install", "-y", *plan.packages), plan.commands)


    def test_build_linux_install_plan_for_dnf_uses_xelatex_packages(self) -> None:
        tooling = ToolingStatus(
            pandoc_command="/usr/bin/pandoc",
            pdf_engine_command=None,
            requested_pdf_engine=None,
            search_roots=(),
        )

        with patch("sys.platform", "linux"), patch(
            "unificatore_obsidian.builder.detect_linux_package_manager", return_value="dnf"
        ), patch("unificatore_obsidian.builder.is_running_as_root", return_value=True):
            plan = build_linux_install_plan(tooling)

        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertNotIn("tectonic", plan.packages)
        self.assertIn("texlive-xetex", plan.packages)
        self.assertIn("texlive-collection-latexextra", plan.packages)
        self.assertIn(("dnf", "install", "-y", *plan.packages), plan.commands)

    def test_build_tool_search_roots_includes_index_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = root / "vault" / "indice.md"
            index.parent.mkdir(parents=True)
            index.write_text("", encoding="utf-8")

            roots = build_tool_search_roots(index)

            self.assertIn(index.parent.resolve(), roots)


if __name__ == "__main__":
    unittest.main()
