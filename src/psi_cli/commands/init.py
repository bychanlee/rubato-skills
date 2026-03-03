"""Project initialization: create calc_db/ and reports/ with correct index files."""

from __future__ import annotations

from pathlib import Path

from psi_cli.commands.index import CALC_HEADERS, CALC_PREAMBLE, REPORT_HEADERS, REPORT_PREAMBLE
from psi_cli.markdown_table import render_table, write_index


def run_init(args) -> None:
    _init_project()


def _init_project() -> None:
    """Create calc_db/ and reports/ directories with properly-formatted index files."""
    calc_dir = Path("calc_db")
    reports_dir = Path("reports")

    calc_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    calc_index = calc_dir / "index.md"
    if not calc_index.exists():
        write_index(calc_index, CALC_PREAMBLE, CALC_HEADERS, [])
        print(f"Created {calc_index}")
    else:
        print(f"Already exists: {calc_index}")

    reports_index = reports_dir / "index.md"
    if not reports_index.exists():
        write_index(reports_index, REPORT_PREAMBLE, REPORT_HEADERS, [])
        print(f"Created {reports_index}")
    else:
        print(f"Already exists: {reports_index}")

    print("Initialization complete.")
