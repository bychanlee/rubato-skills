#!/usr/bin/env python3
"""Remove a computer from the project-local registry."""

from __future__ import annotations

import argparse
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


def _write_registry(data: dict) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


# --- Main ---

def main() -> None:
    parser = argparse.ArgumentParser(description="Remove a computer from the registry")
    parser.add_argument("name", help="Computer name to remove")
    args = parser.parse_args()

    data = _read_registry()
    if args.name not in data["computers"]:
        print(f"Error: Computer not found: {args.name}", file=sys.stderr)
        sys.exit(1)

    del data["computers"][args.name]
    _write_registry(data)
    print(f"Removed computer: {args.name}")


if __name__ == "__main__":
    main()
