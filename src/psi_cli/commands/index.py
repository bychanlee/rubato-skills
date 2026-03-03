"""Index operations: next-id, append, update, rebuild."""

from __future__ import annotations

import json
import re
from pathlib import Path

from psi_cli.filelock import locked_write
from psi_cli.frontmatter import read_frontmatter
from psi_cli.main import die
from psi_cli.markdown_table import read_index, render_table, write_index

# Headers for each index type
CALC_HEADERS = ["id", "title", "date", "status", "code", "computer", "parents", "tags"]
REPORT_HEADERS = ["id", "title", "date", "status", "calcs", "tags"]

CALC_PREAMBLE = "# Calculation Index\n\n"
REPORT_PREAMBLE = "# Report Index\n\n"


def _detect_prefix(dir_name: str) -> str:
    """Detect ID prefix from directory name."""
    if "calc" in dir_name.lower():
        return "c"
    if "report" in dir_name.lower():
        return "r"
    return "c"


def _extract_ids_from_dir(dir_path: Path, prefix: str) -> list[int]:
    """Glob directories to extract numeric IDs."""
    nums = []
    pattern = f"{prefix}[0-9]*"
    for p in dir_path.glob(pattern):
        if p.is_dir():
            m = re.match(rf"{re.escape(prefix)}(\d+)", p.name)
            if m:
                nums.append(int(m.group(1)))
    return nums


def _extract_ids_from_rows(rows: list[list[str]], prefix: str) -> list[int]:
    """Extract numeric IDs from index table rows."""
    nums = []
    for row in rows:
        if row:
            m = re.match(rf"{re.escape(prefix)}(\d+)", row[0])
            if m:
                nums.append(int(m.group(1)))
    return nums


def run_index(args) -> None:
    if args.index_command == "next-id":
        _next_id(args.dir)
    elif args.index_command == "append":
        _append(args.index_path, args.json_data)
    elif args.index_command == "update":
        _update(args.index_path, args.id, args.json_data)
    elif args.index_command == "rebuild":
        _rebuild(args.dir)
    else:
        die("Usage: psi-cli index {next-id|append|update|rebuild}")


def _next_id(dir_path: str) -> None:
    """Print the next sequential ID."""
    d = Path(dir_path)
    dir_name = d.name
    prefix = _detect_prefix(dir_name)

    # Try index first
    index_path = d / "index.md"
    nums: list[int] = []
    if index_path.exists():
        _, _, rows = read_index(index_path)
        nums = _extract_ids_from_rows(rows, prefix)

    # Fallback: glob directories
    dir_nums = _extract_ids_from_dir(d, prefix)
    nums.extend(dir_nums)

    next_num = max(nums, default=0) + 1
    print(f"{prefix}{next_num:03d}")


def _append(index_path: str, json_data: str) -> None:
    """Append a row to the index (with file locking for concurrency safety)."""
    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        die(f"Invalid JSON: {e}")

    p = Path(index_path)
    with locked_write(p):
        preamble, headers, rows = read_index(p)

        if not headers:
            # Detect headers from path
            if "calc" in p.name or "calc" in str(p.parent):
                headers = CALC_HEADERS
                preamble = preamble or CALC_PREAMBLE
            else:
                headers = REPORT_HEADERS
                preamble = preamble or REPORT_PREAMBLE

        row = [_fmt_cell(data.get(h, "-"), h) for h in headers]
        rows.append(row)
        write_index(p, preamble, headers, rows)
    print(f"Appended to {p}")


def _update(index_path: str, row_id: str, json_data: str) -> None:
    """Update a row by its id (with file locking for concurrency safety)."""
    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        die(f"Invalid JSON: {e}")

    p = Path(index_path)
    if not p.exists():
        die(f"Index not found: {index_path}")

    with locked_write(p):
        preamble, headers, rows = read_index(p)
        if not headers:
            die(f"No table found in {index_path}")

        id_col = 0  # id is always first column
        found = False
        for i, row in enumerate(rows):
            if row[id_col].strip() == row_id:
                for h_idx, h in enumerate(headers):
                    if h in data:
                        rows[i][h_idx] = _fmt_cell(data[h], h)
                found = True
                break

        if not found:
            die(f"ID {row_id} not found in {index_path}")

        write_index(p, preamble, headers, rows)
    print(f"Updated {row_id} in {p}")


def _rebuild(dir_path: str) -> None:
    """Rebuild index from front matter of all README.md files."""
    d = Path(dir_path)
    prefix = _detect_prefix(d.name)

    if prefix == "c":
        headers = CALC_HEADERS
        preamble = CALC_PREAMBLE
        glob_pattern = "c*/README.md"
    else:
        headers = REPORT_HEADERS
        preamble = REPORT_PREAMBLE
        glob_pattern = "r*/README.md"

    readmes = sorted(d.glob(glob_pattern))
    rows = []
    for readme in readmes:
        try:
            metadata, _ = read_frontmatter(readme)
            row = [_fmt_cell(metadata.get(h, "-"), h) for h in headers]
            rows.append(row)
        except (ValueError, Exception) as e:
            print(f"Warning: skipping {readme}: {e}", file=__import__("sys").stderr)

    # Sort by id
    rows.sort(key=lambda r: r[0])

    index_path = d / "index.md"
    write_index(index_path, preamble, headers, rows)
    print(f"Rebuilt {index_path}: {len(rows)} entries")


def _fmt_cell(value, header: str) -> str:
    """Format a value for a table cell."""
    if value is None or value == "" or value == []:
        return "-"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items())
    return str(value)
