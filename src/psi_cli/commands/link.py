"""Bidirectional link operations: add/remove child, add/remove report."""

from __future__ import annotations

from pathlib import Path

from psi_cli.filelock import locked_write
from psi_cli.frontmatter import read_frontmatter, write_frontmatter
from psi_cli.main import die


def _resolve_path(id_str: str) -> Path:
    """Resolve a short ID to its README.md path.

    c002 → calc_db/c002/README.md
    r001 → reports/r001/README.md
    """
    if id_str.startswith("c"):
        return Path("calc_db") / id_str / "README.md"
    elif id_str.startswith("r"):
        return Path("reports") / id_str / "README.md"
    else:
        die(f"Cannot resolve ID: {id_str} (must start with 'c' or 'r')")
        return Path()  # unreachable


def _add_to_list(metadata: dict, key: str, value: str) -> bool:
    """Add value to a list field if not already present. Returns True if changed."""
    lst = metadata.get(key, [])
    if not isinstance(lst, list):
        lst = [lst] if lst else []
    if value not in lst:
        lst.append(value)
        metadata[key] = lst
        return True
    return False


def _remove_from_list(metadata: dict, key: str, value: str) -> bool:
    """Remove value from a list field. Returns True if changed."""
    lst = metadata.get(key, [])
    if not isinstance(lst, list):
        lst = [lst] if lst else []
    if value in lst:
        lst.remove(value)
        metadata[key] = lst
        return True
    return False


def run_link(args) -> None:
    if args.link_command == "add-child":
        _add_child(args.parent_id, args.child_id)
    elif args.link_command == "remove-child":
        _remove_child(args.parent_id, args.child_id)
    elif args.link_command == "add-report":
        _add_report(args.calc_id, args.report_id)
    elif args.link_command == "remove-report":
        _remove_report(args.calc_id, args.report_id)
    else:
        die("Usage: psi-cli link {add-child|remove-child|add-report|remove-report}")


def _add_child(parent_id: str, child_id: str) -> None:
    """Add child_id to parent's children list (with file locking)."""
    parent_path = _resolve_path(parent_id)
    if not parent_path.exists():
        die(f"Parent not found: {parent_path}")

    with locked_write(parent_path):
        metadata, body = read_frontmatter(parent_path)
        if _add_to_list(metadata, "children", child_id):
            write_frontmatter(parent_path, metadata, body)
            print(f"Added {child_id} to {parent_id}.children")
        else:
            print(f"{child_id} already in {parent_id}.children")


def _remove_child(parent_id: str, child_id: str) -> None:
    """Remove child_id from parent's children list (with file locking)."""
    parent_path = _resolve_path(parent_id)
    if not parent_path.exists():
        die(f"Parent not found: {parent_path}")

    with locked_write(parent_path):
        metadata, body = read_frontmatter(parent_path)
        if _remove_from_list(metadata, "children", child_id):
            write_frontmatter(parent_path, metadata, body)
            print(f"Removed {child_id} from {parent_id}.children")
        else:
            print(f"{child_id} not in {parent_id}.children")


def _add_report(calc_id: str, report_id: str) -> None:
    """Add report_id to calc's reports list (with file locking)."""
    calc_path = _resolve_path(calc_id)
    if not calc_path.exists():
        die(f"Calc not found: {calc_path}")

    with locked_write(calc_path):
        metadata, body = read_frontmatter(calc_path)
        if _add_to_list(metadata, "reports", report_id):
            write_frontmatter(calc_path, metadata, body)
            print(f"Added {report_id} to {calc_id}.reports")
        else:
            print(f"{report_id} already in {calc_id}.reports")


def _remove_report(calc_id: str, report_id: str) -> None:
    """Remove report_id from calc's reports list (with file locking)."""
    calc_path = _resolve_path(calc_id)
    if not calc_path.exists():
        die(f"Calc not found: {calc_path}")

    with locked_write(calc_path):
        metadata, body = read_frontmatter(calc_path)
        if _remove_from_list(metadata, "reports", report_id):
            write_frontmatter(calc_path, metadata, body)
            print(f"Removed {report_id} from {calc_id}.reports")
        else:
            print(f"{report_id} not in {calc_id}.reports")
