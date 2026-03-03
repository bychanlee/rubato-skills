"""Markdown table parse/render operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def parse_table(text: str) -> tuple[list[str], list[list[str]]]:
    """Parse a markdown table into (headers, rows).

    Expects | delimited lines. Skips the separator row (contains only -, |, :, spaces).
    """
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    table_lines = [l for l in lines if l.startswith("|")]
    if not table_lines:
        return [], []

    headers = _parse_row(table_lines[0])
    rows = []
    for line in table_lines[1:]:
        cells = _parse_row(line)
        # Skip separator rows
        if all(_is_separator_cell(c) for c in cells):
            continue
        rows.append(cells)
    return headers, rows


def _parse_row(line: str) -> list[str]:
    """Parse a single | delimited row into cells."""
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def _is_separator_cell(cell: str) -> bool:
    """Check if a cell is a separator (only contains -, :, spaces)."""
    return all(c in "-: " for c in cell) and len(cell.strip()) > 0


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render headers and rows into an aligned markdown table."""
    if not headers:
        return ""

    ncols = len(headers)
    # Normalize rows to have the right number of columns
    norm_rows = []
    for row in rows:
        if len(row) < ncols:
            row = row + [""] * (ncols - len(row))
        elif len(row) > ncols:
            row = row[:ncols]
        norm_rows.append(row)

    # Compute column widths
    widths = [len(h) for h in headers]
    for row in norm_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    # Minimum width of 4 for separator aesthetics
    widths = [max(w, 4) for w in widths]

    def fmt_row(cells: list[str]) -> str:
        parts = []
        for i, cell in enumerate(cells):
            parts.append(f" {cell:<{widths[i]}} ")
        return "|" + "|".join(parts) + "|"

    lines = [fmt_row(headers)]
    lines.append("|" + "|".join(f" {'-' * widths[i]} " for i in range(ncols)) + "|")
    for row in norm_rows:
        lines.append(fmt_row(row))
    return "\n".join(lines) + "\n"


def read_index(path: str | Path) -> tuple[str, list[str], list[list[str]]]:
    """Read an index file, returning (preamble, headers, rows).

    Preamble is the text before the table (e.g., '# Calculation Index\\n\\n').
    """
    p = Path(path)
    if not p.exists():
        return "", [], []

    text = p.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Find first table line
    table_start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("|"):
            table_start = i
            break

    if table_start is None:
        return text, [], []

    preamble = "\n".join(lines[:table_start])
    if preamble and not preamble.endswith("\n"):
        preamble += "\n"

    table_text = "\n".join(lines[table_start:])
    headers, rows = parse_table(table_text)
    return preamble, headers, rows


def write_index(path: str | Path, preamble: str, headers: list[str], rows: list[list[str]]) -> None:
    """Write preamble + table to an index file.

    Note: For atomic read-modify-write, callers should wrap both read_index
    and write_index inside a locked_write() context manager.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    content = preamble + render_table(headers, rows)
    p.write_text(content, encoding="utf-8")
