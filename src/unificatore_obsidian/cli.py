from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

from .builder import (
    BuildError,
    InstallPlan,
    ToolingStatus,
    build_linux_install_plan,
    build_pdf,
    describe_missing_tools,
    inspect_tooling,
)


class ProgressReporter:
    def __init__(self) -> None:
        self._bar_width = 32
        self._last_stage: str | None = None
        self._last_line_was_bar = False

    def __call__(self, event: BuildProgress) -> None:
        if event.stage == "preparing" and event.current is not None and event.total:
            bar = self._render_bar(event.current, event.total)
            line = f"\rPreparazione note {bar} {event.current}/{event.total}"
            print(line, end="", file=sys.stderr, flush=True)
            self._last_line_was_bar = True
            self._last_stage = event.stage
            return

        if self._last_line_was_bar:
            print(file=sys.stderr)
            self._last_line_was_bar = False

        if event.stage != self._last_stage or event.stage in {"collecting", "collected", "rendering", "completed"}:
            print(event.message, file=sys.stderr, flush=True)
        self._last_stage = event.stage

    def finish(self) -> None:
        if self._last_line_was_bar:
            print(file=sys.stderr)
            self._last_line_was_bar = False

    def _render_bar(self, current: int, total: int) -> str:
        filled = int(self._bar_width * current / total)
        empty = self._bar_width - filled
        return f"[{'#' * filled}{'.' * empty}]"



def offer_linux_install(tooling: ToolingStatus) -> bool:
    plan = build_linux_install_plan(tooling)
    if plan is None:
        return False

    print_install_plan(plan)
    if not sys.stdin.isatty():
        print(
            "Ambiente non interattivo: installa i pacchetti indicati e rilancia lo stesso comando.",
            file=sys.stderr,
        )
        return False

    answer = input("Vuoi procedere con l'installazione? [s/N] ").strip().lower()
    if answer not in {"s", "si", "y", "yes"}:
        return False

    for command in plan.commands:
        print(f"Eseguo: {format_command(command)}", file=sys.stderr)
        completed = subprocess.run(command, check=False)
        if completed.returncode != 0:
            print(
                f"Installazione interrotta: il comando ha restituito codice {completed.returncode}.",
                file=sys.stderr,
            )
            return False
    return True


def print_install_plan(plan: InstallPlan) -> None:
    print("Strumenti mancanti:", file=sys.stderr)
    for tool in plan.missing_tools:
        print(f"- {tool}", file=sys.stderr)
    print("", file=sys.stderr)
    print(f"Gestore pacchetti rilevato: {plan.package_manager}", file=sys.stderr)
    print("Pacchetti che verranno installati:", file=sys.stderr)
    for package in plan.packages:
        print(f"- {package}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Comandi previsti:", file=sys.stderr)
    for command in plan.commands:
        print(f"- {format_command(command)}", file=sys.stderr)
    if plan.notes:
        print("", file=sys.stderr)
        print("Riepilogo:", file=sys.stderr)
        for note in plan.notes:
            print(f"- {note}", file=sys.stderr)
    print("", file=sys.stderr)


def print_missing_tooling(tooling: ToolingStatus) -> None:
    missing = describe_missing_tools(tooling)
    print("Impossibile generare il PDF: mancano strumenti esterni.", file=sys.stderr)
    for tool in missing:
        print(f"- {tool}", file=sys.stderr)
    print(
        "Puoi installarli nel sistema, indicarli con --pandoc-path/--pdf-engine-path, "
        "oppure metterli in external/, tools/ o .portable-tools/.",
        file=sys.stderr,
    )


def format_command(command: tuple[str, ...]) -> str:
    return " ".join(shell_quote(part) for part in command)


def shell_quote(value: str) -> str:
    if value and all(char.isalnum() or char in "@%_+=:,./-" for char in value):
        return value
    return "'" + value.replace("'", "'\\''") + "'"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera un PDF unificato partendo da un indice Markdown di Obsidian."
    )
    parser.add_argument("index_file", nargs="?", type=Path, help="Percorso del file indice `.md`.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Percorso del PDF finale. Di default usa il nome dell'indice.",
    )
    parser.add_argument(
        "--vault-root",
        type=Path,
        help="Root del vault Obsidian. Se omesso viene rilevato automaticamente.",
    )
    parser.add_argument(
        "--pdf-engine",
        help="Motore PDF da passare a pandoc, ad esempio `xelatex`.",
    )
    parser.add_argument(
        "--pandoc-path",
        type=Path,
        help="Percorso esplicito del binario pandoc, utile per setup portabili.",
    )
    parser.add_argument(
        "--pdf-engine-path",
        type=Path,
        help="Percorso esplicito del binario del motore PDF, utile per setup portabili.",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Conserva i file temporanei accanto al PDF con estensione `.temp`.",
    )
    parser.add_argument(
        "--pandoc-arg",
        action="append",
        default=[],
        help="Argomento extra da inoltrare a pandoc. Opzione ripetibile.",
    )
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Mostra quali binari verrebbero usati per pandoc e il motore PDF.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    progress = ProgressReporter()

    if args.diagnose:
        try:
            tooling = inspect_tooling(
                index_file=args.index_file,
                pdf_engine=args.pdf_engine,
                pandoc_path=args.pandoc_path,
                pdf_engine_path=args.pdf_engine_path,
            )
        except BuildError as exc:
            print(f"Errore: {exc}", file=sys.stderr)
            return 1

        print(f"Pandoc: {tooling.pandoc_command or 'non trovato'}")
        print(f"Motore PDF richiesto: {tooling.requested_pdf_engine or 'auto'}")
        print(f"Motore PDF risolto: {tooling.pdf_engine_command or 'non trovato'}")
        print("Cartelle controllate:")
        for root in tooling.search_roots:
            print(f"- {root}")
        if describe_missing_tools(tooling):
            plan = build_linux_install_plan(tooling)
            if plan is not None:
                print("", file=sys.stderr)
                print_install_plan(plan)
        return 0

    if args.index_file is None:
        parser.error("il file indice e obbligatorio, a meno che non usi --diagnose")

    try:
        tooling = inspect_tooling(
            index_file=args.index_file,
            pdf_engine=args.pdf_engine,
            pandoc_path=args.pandoc_path,
            pdf_engine_path=args.pdf_engine_path,
        )
    except BuildError as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return 1

    if describe_missing_tools(tooling):
        if not offer_linux_install(tooling):
            print_missing_tooling(tooling)
            return 1
        try:
            tooling = inspect_tooling(
                index_file=args.index_file,
                pdf_engine=args.pdf_engine,
                pandoc_path=args.pandoc_path,
                pdf_engine_path=args.pdf_engine_path,
            )
        except BuildError as exc:
            print(f"Errore: {exc}", file=sys.stderr)
            return 1
        if describe_missing_tools(tooling):
            print_missing_tooling(tooling)
            return 1

    try:
        result = build_pdf(
            index_file=args.index_file,
            output_pdf=args.output,
            vault_root=args.vault_root,
            pdf_engine=args.pdf_engine,
            pandoc_path=args.pandoc_path,
            pdf_engine_path=args.pdf_engine_path,
            keep_temp=args.keep_temp,
            extra_pandoc_args=args.pandoc_arg,
            progress_callback=progress,
        )
    except BuildError as exc:
        progress.finish()
        print(f"Errore: {exc}", file=sys.stderr)
        return 1

    progress.finish()
    print(f"File processati: {len(result.included_notes)}")
    print(f"PDF salvato in: {result.output_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
