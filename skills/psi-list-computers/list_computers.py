#!/usr/bin/env python3
"""List registered computers from the project-local registry."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml


# --- Inline: computer registry ---

REGISTRY_PATH = Path("calc_db") / "computers.yaml"


def _read_registry() -> dict:
    if not REGISTRY_PATH.exists():
        return {"computers": {}}
    text = REGISTRY_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    if "computers" not in data:
        data["computers"] = {}
    # Handle list format: convert [{id: name, ...}, ...] to {name: {...}, ...}
    if isinstance(data["computers"], list):
        by_name = {}
        for entry in data["computers"]:
            name = entry.get("id") or entry.get("label") or entry.get("name", "unknown")
            by_name[name] = {k: v for k, v in entry.items() if k not in ("id", "label")}
        data["computers"] = by_name
    return data


def _ssh_check(hostname: str) -> bool:
    try:
        result = subprocess.run(
            ["ssh", "-O", "check", hostname],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# --- Inline: markdown_table (render only) ---

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


# --- Main ---

def main() -> None:
    parser = argparse.ArgumentParser(description="List registered computers")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    data = _read_registry()
    computers = data.get("computers", {})

    if args.json:
        json.dump(computers, sys.stdout, ensure_ascii=False, default=str)
        print()
        return

    if not computers:
        print("No computers registered.")
        return

    headers = ["name", "type", "hostname", "scheduler", "work_dir"]
    rows = []
    for name, config in computers.items():
        rows.append([
            name,
            config.get("type", "-"),
            config.get("hostname", "-"),
            config.get("scheduler", "-"),
            config.get("work_dir", "-"),
        ])

    print(render_table(headers, rows), end="")

    for name, config in computers.items():
        if config.get("type") == "hpc":
            hostname = config.get("hostname", "")
            if hostname:
                connected = _ssh_check(hostname)
                status = "connected" if connected else "disconnected"
                print(f"  {name}: SSH {status}")


if __name__ == "__main__":
    main()
