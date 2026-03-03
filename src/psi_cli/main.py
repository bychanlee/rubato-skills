"""Argparse entry point for psi-cli."""

from __future__ import annotations

import argparse
import sys


def die(msg: str, code: int = 1) -> None:
    """Print error to stderr and exit."""
    print(msg, file=sys.stderr)
    sys.exit(code)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="psi-cli", description="CLI tool for psi-agent provenance tracking")
    sub = parser.add_subparsers(dest="command")

    # init
    sub.add_parser("init", help="Initialize psi project (create calc_db/ and reports/ with index files)")

    # fm
    fm_parser = sub.add_parser("fm", help="Front matter operations")
    fm_sub = fm_parser.add_subparsers(dest="fm_command")

    fm_read = fm_sub.add_parser("read", help="Read front matter as JSON")
    fm_read.add_argument("path", help="Path to markdown file")

    fm_write = fm_sub.add_parser("write", help="Write/merge front matter from JSON stdin")
    fm_write.add_argument("path", help="Path to markdown file")
    fm_write.add_argument("--template", choices=["calc", "report"], help="Template to use if file doesn't exist")

    # index
    idx_parser = sub.add_parser("index", help="Index operations")
    idx_sub = idx_parser.add_subparsers(dest="index_command")

    idx_next = idx_sub.add_parser("next-id", help="Print next sequential ID")
    idx_next.add_argument("dir", help="Directory (calc_db or reports)")

    idx_append = idx_sub.add_parser("append", help="Append row to index")
    idx_append.add_argument("index_path", help="Path to index.md")
    idx_append.add_argument("json_data", help="JSON object with row data")

    idx_update = idx_sub.add_parser("update", help="Update row in index by id")
    idx_update.add_argument("index_path", help="Path to index.md")
    idx_update.add_argument("id", help="ID of row to update")
    idx_update.add_argument("json_data", help="JSON object with fields to update")

    idx_rebuild = idx_sub.add_parser("rebuild", help="Rebuild index from front matter")
    idx_rebuild.add_argument("dir", help="Directory (calc_db or reports)")

    # link
    link_parser = sub.add_parser("link", help="Bidirectional link operations")
    link_sub = link_parser.add_subparsers(dest="link_command")

    link_ac = link_sub.add_parser("add-child", help="Add child to parent's children list")
    link_ac.add_argument("parent_id", help="Parent calc ID")
    link_ac.add_argument("child_id", help="Child calc ID")

    link_rc = link_sub.add_parser("remove-child", help="Remove child from parent's children list")
    link_rc.add_argument("parent_id", help="Parent calc ID")
    link_rc.add_argument("child_id", help="Child calc ID")

    link_ar = link_sub.add_parser("add-report", help="Add report to calc's reports list")
    link_ar.add_argument("calc_id", help="Calc ID")
    link_ar.add_argument("report_id", help="Report ID")

    link_rr = link_sub.add_parser("remove-report", help="Remove report from calc's reports list")
    link_rr.add_argument("calc_id", help="Calc ID")
    link_rr.add_argument("report_id", help="Report ID")

    # computer
    comp_parser = sub.add_parser("computer", help="Computer registry operations")
    comp_sub = comp_parser.add_subparsers(dest="computer_command")

    comp_list = comp_sub.add_parser("list", help="List registered computers")
    comp_list.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")

    comp_add = comp_sub.add_parser("add", help="Add a computer")
    comp_add.add_argument("name", help="Computer name")
    comp_add.add_argument("json_data", nargs="?", help="JSON object with computer config")

    comp_rm = comp_sub.add_parser("remove", help="Remove a computer")
    comp_rm.add_argument("name", help="Computer name")

    comp_ssh = comp_sub.add_parser("ssh-check", help="Check SSH ControlMaster connectivity")
    comp_ssh.add_argument("name", help="Computer name")

    # sync
    sync_parser = sub.add_parser("sync", help="File sync operations")
    sync_sub = sync_parser.add_subparsers(dest="sync_command")

    sync_push = sync_sub.add_parser("push", help="Push calc files to remote")
    sync_push.add_argument("calc_id", help="Calc ID")
    sync_push.add_argument("--all", action="store_true", dest="sync_all", help="Sync all files")

    sync_pull = sync_sub.add_parser("pull", help="Pull calc files from remote")
    sync_pull.add_argument("calc_id", help="Calc ID")
    sync_pull.add_argument("--all", action="store_true", dest="sync_all", help="Sync all files")

    # status
    sub.add_parser("status", help="Show project status summary")

    # graph
    graph_parser = sub.add_parser("graph", help="Show provenance DAG")
    graph_parser.add_argument("id", nargs="?", help="Calc ID to center on")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "init":
        from psi_cli.commands.init import run_init
        run_init(args)
    elif args.command == "fm":
        from psi_cli.commands.fm import run_fm
        run_fm(args)
    elif args.command == "index":
        from psi_cli.commands.index import run_index
        run_index(args)
    elif args.command == "link":
        from psi_cli.commands.link import run_link
        run_link(args)
    elif args.command == "computer":
        from psi_cli.commands.computer import run_computer
        run_computer(args)
    elif args.command == "sync":
        from psi_cli.commands.sync import run_sync
        run_sync(args)
    elif args.command == "status":
        from psi_cli.commands.status import run_status
        run_status(args)
    elif args.command == "graph":
        from psi_cli.commands.graph import run_graph
        run_graph(args)


if __name__ == "__main__":
    main()
