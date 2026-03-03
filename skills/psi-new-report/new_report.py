#!/usr/bin/env python3
"""Create a new report: next-id, mkdir, frontmatter, index append, calc links."""

from __future__ import annotations

import argparse
import fcntl
import json
import re
import sys
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any, Generator

import yaml


# --- Inline: filelock ---

@contextmanager
def locked_write(path: str | Path, timeout: float = 30.0) -> Generator[Path, None, None]:
    p = Path(path)
    lock_path = p.with_suffix(p.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = open(lock_path, "w")
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except (OSError, BlockingIOError):
            if time.monotonic() >= deadline:
                lock_fd.close()
                raise TimeoutError(f"Could not acquire lock on {lock_path} within {timeout}s")
            time.sleep(0.05)
    try:
        yield p
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


# --- Inline: frontmatter ---

_FM_PATTERN = re.compile(r"\A---\n(.*?)---\n?(.*)", re.DOTALL)

REPORT_KEY_ORDER = ["id", "title", "date", "status", "calcs", "tags", "notes"]


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = _FM_PATTERN.match(text)
    if not m:
        raise ValueError("No valid YAML front matter found")
    raw_yaml, body = m.group(1), m.group(2)
    metadata = yaml.safe_load(raw_yaml) or {}
    return metadata, body


def read_frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    return parse_frontmatter(text)


class _PsiDumper(yaml.SafeDumper):
    pass


def _str_representer(dumper: yaml.Dumper, data: str) -> yaml.Node:
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_PsiDumper.add_representer(str, _str_representer)


def _is_short_list(lst: list) -> bool:
    return all(isinstance(v, (str, int, float)) for v in lst) and len(lst) <= 10


def _is_leaf_dict(d: dict) -> bool:
    return all(isinstance(v, (str, int, float, bool, type(None))) for v in d.values()) and len(d) <= 8


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        if any(c in value for c in ",:{}[]#&*!|>'\"%@`"):
            return f'"{value}"'
        return value
    if value is None:
        return "null"
    return str(value)


def _ordered_metadata(metadata: dict) -> list[tuple[str, Any]]:
    ordered = []
    for k in REPORT_KEY_ORDER:
        if k in metadata:
            ordered.append((k, metadata[k]))
    for k in metadata:
        if k not in REPORT_KEY_ORDER:
            ordered.append((k, metadata[k]))
    return ordered


def render_frontmatter(metadata: dict, body: str) -> str:
    lines = ["---"]
    ordered = _ordered_metadata(metadata)
    for key, value in ordered:
        if value is None:
            lines.append(f"{key}:")
        elif isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            elif _is_short_list(value):
                items = ", ".join(_yaml_scalar(v) for v in value)
                lines.append(f"{key}: [{items}]")
            else:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {_yaml_scalar(item)}")
        elif isinstance(value, dict):
            if not value:
                lines.append(f"{key}: {{}}")
            elif _is_leaf_dict(value):
                items = ", ".join(f"{k}: {_yaml_scalar(v)}" for k, v in value.items())
                lines.append(f"{key}: {{{items}}}")
            else:
                dumped = yaml.dump(value, Dumper=_PsiDumper, default_flow_style=False, sort_keys=False).rstrip()
                lines.append(f"{key}:")
                for line in dumped.split("\n"):
                    lines.append(f"  {line}")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, str):
            if "\n" in value or ":" in value or "#" in value or value.startswith(("{", "[", "'", '"')):
                quoted = yaml.dump(value, Dumper=_PsiDumper, default_flow_style=True).strip()
                lines.append(f"{key}: {quoted}")
            else:
                lines.append(f"{key}: {value}" if value else f'{key}: ""')
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    result = "\n".join(lines) + "\n"
    if body:
        result += body
    return result


def write_frontmatter(path: Path, metadata: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_frontmatter(metadata, body), encoding="utf-8")


# --- Inline: markdown_table ---

def _parse_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def _is_separator_cell(cell: str) -> bool:
    return all(c in "-: " for c in cell) and len(cell.strip()) > 0


def parse_table(text: str) -> tuple[list[str], list[list[str]]]:
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    table_lines = [l for l in lines if l.startswith("|")]
    if not table_lines:
        return [], []
    headers = _parse_row(table_lines[0])
    rows = []
    for line in table_lines[1:]:
        cells = _parse_row(line)
        if all(_is_separator_cell(c) for c in cells):
            continue
        rows.append(cells)
    return headers, rows


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    if not headers:
        return ""
    ncols = len(headers)
    norm_rows = []
    for row in rows:
        if len(row) < ncols:
            row = row + [""] * (ncols - len(row))
        elif len(row) > ncols:
            row = row[:ncols]
        norm_rows.append(row)
    widths = [len(h) for h in headers]
    for row in norm_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    widths = [max(w, 4) for w in widths]

    def fmt_row(cells: list[str]) -> str:
        parts = [f" {cell:<{widths[i]}} " for i, cell in enumerate(cells)]
        return "|" + "|".join(parts) + "|"

    lines = [fmt_row(headers)]
    lines.append("|" + "|".join(f" {'-' * widths[i]} " for i in range(ncols)) + "|")
    for row in norm_rows:
        lines.append(fmt_row(row))
    return "\n".join(lines) + "\n"


def read_index(path: Path) -> tuple[str, list[str], list[list[str]]]:
    if not path.exists():
        return "", [], []
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
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


def write_index(path: Path, preamble: str, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = preamble + render_table(headers, rows)
    path.write_text(content, encoding="utf-8")


# --- Inline: templates ---

REPORT_FIELDS: dict[str, Any] = {
    "id": "", "title": "", "date": "", "status": "draft",
    "calcs": [], "tags": [], "notes": "",
}

REPORT_BODY = """\

# {id}: {title}

## Purpose

{{What question this report answers}}

## Analysis

{{Methods, comparisons, discussion}}

## Conclusions

{{Key findings, next steps}}
"""

REPORT_HEADERS = ["id", "title", "date", "status", "calcs", "tags"]
REPORT_PREAMBLE = "# Report Index\n\n"


def _fmt_cell(value, header: str) -> str:
    if value is None or value == "" or value == []:
        return "-"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items())
    return str(value)


# --- Directory helpers ---

def _slugify(tags: list[str]) -> str:
    if not tags:
        return ""
    slug = "_".join(tags)
    slug = re.sub(r'[^\w]', '_', slug)
    slug = re.sub(r'_+', '_', slug)
    return slug.strip('_').lower()


def _resolve_dir(base: Path, entry_id: str) -> Path:
    exact = base / entry_id
    if exact.is_dir():
        return exact
    matches = sorted(p for p in base.glob(f"{entry_id}_*") if p.is_dir())
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        print(f"Error: Multiple dirs match {entry_id}: {[p.name for p in matches]}", file=sys.stderr)
        sys.exit(1)
    print(f"Error: Directory not found for {entry_id} in {base}", file=sys.stderr)
    sys.exit(1)


# --- Next ID ---

def _next_id(dir_path: Path) -> str:
    prefix = "r"
    nums: list[int] = []
    index_path = dir_path / "index.md"
    if index_path.exists():
        _, _, rows = read_index(index_path)
        for row in rows:
            if row:
                m = re.match(rf"{prefix}(\d+)", row[0])
                if m:
                    nums.append(int(m.group(1)))
    for p in dir_path.glob(f"{prefix}[0-9]*"):
        if p.is_dir():
            m = re.match(rf"{prefix}(\d+)", p.name)
            if m:
                nums.append(int(m.group(1)))
    next_num = max(nums, default=0) + 1
    return f"{prefix}{next_num:03d}"


# --- Link operations ---

def _add_report_link(calc_id: str, report_id: str) -> None:
    calc_dir = _resolve_dir(Path("calc_db"), calc_id)
    calc_path = calc_dir / "README.md"
    if not calc_path.exists():
        print(f"Warning: Calc not found: {calc_path}", file=sys.stderr)
        return
    with locked_write(calc_path):
        metadata, body = read_frontmatter(calc_path)
        reports = metadata.get("reports", [])
        if not isinstance(reports, list):
            reports = [reports] if reports else []
        if report_id not in reports:
            reports.append(report_id)
            metadata["reports"] = reports
            write_frontmatter(calc_path, metadata, body)
            print(f"Added {report_id} to {calc_id}.reports")
        else:
            print(f"{report_id} already in {calc_id}.reports")


# --- Main ---

def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new report")
    parser.add_argument("json_data", help="JSON with report fields (title, calcs, tags)")
    args = parser.parse_args()

    try:
        data = json.loads(args.json_data)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    reports_dir = Path("reports")
    if not reports_dir.exists():
        print("Error: reports/ not found. Run psi:init first.", file=sys.stderr)
        sys.exit(1)

    # Get next ID
    next_id = _next_id(reports_dir)

    # Build metadata
    metadata = dict(REPORT_FIELDS)
    metadata["id"] = next_id
    metadata["title"] = data.get("title", "")
    metadata["date"] = data.get("date", str(date.today()))
    metadata["calcs"] = data.get("calcs", [])
    metadata["tags"] = data.get("tags", [])

    for k, v in data.items():
        if k not in ("title", "date", "calcs", "tags"):
            metadata[k] = v

    body = REPORT_BODY.format(id=next_id, title=metadata["title"])

    # Create report directory and README
    slug = _slugify(metadata.get("tags", []))
    dir_name = f"{next_id}_{slug}" if slug else next_id
    report_path = reports_dir / dir_name
    report_path.mkdir(parents=True, exist_ok=True)
    readme = report_path / "README.md"
    write_frontmatter(readme, metadata, body)

    # Append to index
    index_path = reports_dir / "index.md"
    with locked_write(index_path):
        preamble, headers, rows = read_index(index_path)
        if not headers:
            headers = REPORT_HEADERS
            preamble = preamble or REPORT_PREAMBLE
        row = [_fmt_cell(metadata.get(h, "-"), h) for h in headers]
        rows.append(row)
        write_index(index_path, preamble, headers, rows)

    # Update calc links
    for calc_id in metadata.get("calcs", []):
        _add_report_link(calc_id, next_id)

    print(f"Created {next_id}: {metadata['title']}")


if __name__ == "__main__":
    main()
