#!/usr/bin/env python3
"""Update a computer's configuration in the global registry."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml


# --- Inline: computer registry ---

REGISTRY_PATH = Path.home() / ".claude" / "agent-memory" / "psi" / "computers.yaml"


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


def _ssh_check(hostname: str) -> bool:
    try:
        result = subprocess.run(
            ["ssh", "-O", "check", hostname],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# --- Main ---

def main() -> None:
    parser = argparse.ArgumentParser(description="Update a computer in the registry")
    parser.add_argument("name", help="Computer name to update")
    parser.add_argument("json_data", help="JSON with fields to update")
    args = parser.parse_args()

    try:
        updates = json.loads(args.json_data)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    data = _read_registry()
    if args.name not in data["computers"]:
        print(f"Error: Computer not found: {args.name}", file=sys.stderr)
        sys.exit(1)

    # Deep merge updates into existing config
    data["computers"][args.name] = deep_merge(data["computers"][args.name], updates)
    _write_registry(data)
    print(f"Updated computer: {args.name}")

    # SSH check for HPC
    config = data["computers"][args.name]
    if config.get("type") == "hpc":
        hostname = config.get("hostname", "")
        if hostname:
            if _ssh_check(hostname):
                print(f"SSH connected: {args.name} ({hostname})")
            else:
                print(f"SSH disconnected: {args.name} ({hostname})", file=sys.stderr)
                sys.exit(2)


if __name__ == "__main__":
    main()
