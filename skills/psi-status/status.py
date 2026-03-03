#!/usr/bin/env python3
"""Project status summary — outputs JSON."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml


# --- Inline: frontmatter (read only) ---

_FM_PATTERN = re.compile(r"\A---\n(.*?)---\n?(.*)", re.DOTALL)


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


# --- Main ---

def main() -> None:
    result = {}

    # Calculations
    calc_dir = Path("calc_db")
    calcs = []
    if calc_dir.exists():
        for readme in sorted(calc_dir.glob("c*/README.md")):
            try:
                metadata, _ = read_frontmatter(readme)
                calcs.append(metadata)
            except (ValueError, Exception):
                pass

    status_counts = Counter(c.get("status", "unknown") for c in calcs)
    result["calc_counts"] = dict(status_counts)
    result["total_calcs"] = len(calcs)

    sorted_calcs = sorted(calcs, key=lambda c: c.get("date", ""), reverse=True)
    result["recent_calcs"] = [
        {"id": c.get("id"), "title": c.get("title"), "date": c.get("date"), "status": c.get("status")}
        for c in sorted_calcs[:5]
    ]

    orphans = [
        c.get("id") for c in calcs
        if c.get("status") == "completed" and not c.get("reports")
    ]
    result["orphan_calcs"] = orphans

    # Reports
    report_dir = Path("reports")
    reports = []
    if report_dir.exists():
        for readme in sorted(report_dir.glob("r*/README.md")):
            try:
                metadata, _ = read_frontmatter(readme)
                reports.append(metadata)
            except (ValueError, Exception):
                pass

    result["total_reports"] = len(reports)
    draft_reports = [r.get("id") for r in reports if r.get("status") == "draft"]
    result["draft_reports"] = draft_reports

    json.dump(result, sys.stdout, ensure_ascii=False, default=str, indent=2)
    print()


if __name__ == "__main__":
    main()
