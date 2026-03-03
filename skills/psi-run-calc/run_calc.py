#!/usr/bin/env python3
"""Run a calculation: preflight, push, submit, monitor, pull, update-status."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


# --- Inline: frontmatter ---

_FM_PATTERN = re.compile(r"\A---\n(.*?)---\n?(.*)", re.DOTALL)

CALC_KEY_ORDER = [
    "id", "title", "date", "status", "code", "computer", "tags",
    "parents", "children", "reports", "hpc_path", "job_id", "key_results", "notes",
]


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
    for k in CALC_KEY_ORDER:
        if k in metadata:
            ordered.append((k, metadata[k]))
    for k in metadata:
        if k not in CALC_KEY_ORDER:
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


CALC_HEADERS = ["id", "title", "date", "status", "code", "computer", "parents", "tags"]


def _fmt_cell(value: Any, header: str) -> str:
    if value is None or value == "" or value == []:
        return "-"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items())
    return str(value)


# --- Inline: computer registry ---

REGISTRY_PATH = Path.home() / ".claude" / "agent-memory" / "psi" / "computers.yaml"


def _read_registry() -> dict:
    if not REGISTRY_PATH.exists():
        return {"computers": {}}
    text = REGISTRY_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    if "computers" not in data:
        data["computers"] = {}
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


# --- Directory helpers ---

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


# --- Sync helpers ---

def _get_calc_info(calc_id: str) -> tuple[dict, str, Path]:
    """Read calc metadata and body. Returns (metadata, body, readme_path)."""
    local_dir = _resolve_dir(Path("calc_db"), calc_id)
    readme = local_dir / "README.md"
    if not readme.exists():
        print(f"Error: Calc not found: {readme}", file=sys.stderr)
        sys.exit(1)
    metadata, body = read_frontmatter(readme)
    return metadata, body, readme


def _get_computer_config(computer_name: str) -> dict:
    """Look up computer in registry. Exits on error."""
    if not computer_name or computer_name == "local":
        print(f"Error: Calc has no remote computer set (computer: '{computer_name}')", file=sys.stderr)
        sys.exit(1)
    registry = _read_registry()
    computers = registry.get("computers", {})
    if computer_name not in computers:
        print(f"Error: Computer '{computer_name}' not in registry", file=sys.stderr)
        sys.exit(1)
    config = computers[computer_name]
    if config.get("type") != "hpc":
        print(f"Error: Computer '{computer_name}' is not HPC type", file=sys.stderr)
        sys.exit(1)
    hostname = config.get("hostname", "")
    if not hostname:
        print(f"Error: No hostname for computer '{computer_name}'", file=sys.stderr)
        sys.exit(1)
    return config


def _ensure_hpc_path(metadata: dict, body: str, readme: Path, config: dict, calc_id: str) -> str:
    """Resolve hpc_path, writing it to frontmatter if auto-generated."""
    hpc_path = metadata.get("hpc_path", "")
    if not hpc_path:
        work_dir = config.get("work_dir", "")
        if not work_dir:
            print(f"Error: No work_dir set for computer and no hpc_path in calc", file=sys.stderr)
            sys.exit(1)
        project_name = Path.cwd().name
        hpc_path = f"{work_dir}/{project_name}/{calc_id}/"
        metadata["hpc_path"] = hpc_path
        write_frontmatter(readme, metadata, body)
    if not hpc_path.endswith("/"):
        hpc_path += "/"
    return hpc_path


def _rsync(src: str, dst: str, exclude: list[str] | None = None,
           max_size: str | None = None) -> subprocess.CompletedProcess:
    cmd = ["rsync", "-avz", "-e", "ssh"]
    if max_size:
        cmd.extend(["--max-size", max_size])
    if exclude:
        for ex in exclude:
            cmd.extend(["--exclude", ex])
    cmd.extend([src, dst])
    print(f"  {' '.join(cmd)}", file=sys.stderr)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=600)


def _ssh_run(hostname: str, command: str, timeout: int = 60) -> subprocess.CompletedProcess:
    """Run a command on remote host via SSH."""
    return subprocess.run(
        ["ssh", hostname, command],
        capture_output=True, text=True, timeout=timeout,
    )


def _update_index_status(calc_id: str, status: str) -> None:
    """Update status column in calc_db/index.md."""
    index_path = Path("calc_db") / "index.md"
    if not index_path.exists():
        return
    preamble, headers, rows = read_index(index_path)
    if not headers:
        return
    try:
        status_idx = headers.index("status")
    except ValueError:
        return
    for i, row in enumerate(rows):
        if row[0].strip() == calc_id:
            rows[i][status_idx] = status
            write_index(index_path, preamble, headers, rows)
            return


# --- Subcommands ---

def cmd_preflight(calc_id: str) -> None:
    """Validate calc is ready to run. Outputs JSON with calc info."""
    metadata, body, readme = _get_calc_info(calc_id)
    computer_name = metadata.get("computer", "")
    config = _get_computer_config(computer_name)
    hostname = config["hostname"]

    # SSH check
    ssh_ok = _ssh_check(hostname)

    # Resolve hpc_path
    hpc_path = _ensure_hpc_path(metadata, body, readme, config, calc_id)

    # List local input/code files
    local_dir = readme.parent
    input_files = []
    input_dir = local_dir / "input"
    if input_dir.exists():
        input_files = [str(f.relative_to(input_dir)) for f in input_dir.rglob("*") if f.is_file()]

    code_files = []
    code_dir = local_dir / "code"
    if code_dir.exists():
        code_files = [str(f.relative_to(code_dir)) for f in code_dir.rglob("*") if f.is_file()]

    result = {
        "calc_id": calc_id,
        "status": metadata.get("status", ""),
        "code": metadata.get("code", ""),
        "computer": computer_name,
        "hostname": hostname,
        "ssh_connected": ssh_ok,
        "hpc_path": hpc_path,
        "job_id": metadata.get("job_id", ""),
        "input_files": input_files,
        "code_files": code_files,
        "scheduler": config.get("scheduler", ""),
        "account": config.get("account", ""),
        "queues": config.get("queues", []),
        "modules": config.get("modules", []),
        "job_template": config.get("job_template", ""),
    }
    print(json.dumps(result, indent=2))


def cmd_push(calc_id: str) -> None:
    """Push input/, code/, README.md to remote hpc_path."""
    metadata, body, readme = _get_calc_info(calc_id)
    computer_name = metadata.get("computer", "")
    config = _get_computer_config(computer_name)
    hostname = config["hostname"]

    if not _ssh_check(hostname):
        print(f"Error: SSH not connected to {computer_name} ({hostname}). Run: ssh -MNf {hostname}", file=sys.stderr)
        sys.exit(2)

    hpc_path = _ensure_hpc_path(metadata, body, readme, config, calc_id)
    local_dir = readme.parent
    remote_base = f"{hostname}:{hpc_path}"

    # Create remote directory
    _ssh_run(hostname, f"mkdir -p {hpc_path}", timeout=30)

    # Push input/
    input_dir = local_dir / "input"
    if input_dir.exists():
        _ssh_run(hostname, f"mkdir -p {hpc_path}input", timeout=30)
        result = _rsync(f"{input_dir}/", f"{remote_base}input/")
        if result.returncode != 0:
            print(f"Error: rsync input/ failed: {result.stderr}", file=sys.stderr)
            sys.exit(1)

    # Push code/
    code_dir = local_dir / "code"
    if code_dir.exists():
        _ssh_run(hostname, f"mkdir -p {hpc_path}code", timeout=30)
        result = _rsync(f"{code_dir}/", f"{remote_base}code/")
        if result.returncode != 0:
            print(f"Error: rsync code/ failed: {result.stderr}", file=sys.stderr)
            sys.exit(1)

    # Push README.md
    local_readme = local_dir / "README.md"
    if local_readme.exists():
        result = _rsync(str(local_readme), remote_base)
        if result.returncode != 0:
            print(f"Error: rsync README.md failed: {result.stderr}", file=sys.stderr)
            sys.exit(1)

    print(f"Pushed {calc_id} to {hostname}:{hpc_path}")


def cmd_submit(calc_id: str, job_script: str) -> None:
    """Write job script to remote and submit. Prints job_id."""
    metadata, body, readme = _get_calc_info(calc_id)
    computer_name = metadata.get("computer", "")
    config = _get_computer_config(computer_name)
    hostname = config["hostname"]

    if not _ssh_check(hostname):
        print(f"Error: SSH not connected to {computer_name} ({hostname}). Run: ssh -MNf {hostname}", file=sys.stderr)
        sys.exit(2)

    hpc_path = _ensure_hpc_path(metadata, body, readme, config, calc_id)
    scheduler = config.get("scheduler", "slurm")

    # Write job script to remote
    remote_script = f"{hpc_path}job.sh"
    # Use heredoc via ssh to write the script
    write_cmd = f"cat > {remote_script} << 'PSIEOF'\n{job_script}\nPSIEOF"
    result = subprocess.run(
        ["ssh", hostname, "bash", "-c", write_cmd],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        print(f"Error: Failed to write job script: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Make executable
    _ssh_run(hostname, f"chmod +x {remote_script}", timeout=10)

    # Submit
    if scheduler == "pbs":
        submit_cmd = f"cd {hpc_path} && qsub job.sh"
    else:
        submit_cmd = f"cd {hpc_path} && sbatch job.sh"

    result = _ssh_run(hostname, submit_cmd, timeout=30)
    if result.returncode != 0:
        print(f"Error: Job submission failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    output = result.stdout.strip()
    # Parse job ID
    job_id = ""
    if scheduler == "pbs":
        # PBS output: "12345.hostname"
        job_id = output.strip()
    else:
        # Slurm output: "Submitted batch job 12345"
        match = re.search(r"(\d+)", output)
        if match:
            job_id = match.group(1)

    if not job_id:
        print(f"Warning: Could not parse job ID from: {output}", file=sys.stderr)
        print(json.dumps({"submitted": True, "raw_output": output}))
        return

    # Store job_id in frontmatter
    metadata["job_id"] = job_id
    metadata["status"] = "running"
    write_frontmatter(readme, metadata, body)
    _update_index_status(calc_id, "running")

    print(json.dumps({"submitted": True, "job_id": job_id}))


def cmd_monitor(calc_id: str) -> None:
    """Check job status on remote. Outputs JSON."""
    metadata, body, readme = _get_calc_info(calc_id)
    computer_name = metadata.get("computer", "")
    config = _get_computer_config(computer_name)
    hostname = config["hostname"]

    if not _ssh_check(hostname):
        print(json.dumps({"error": "ssh_disconnected", "hostname": hostname}))
        sys.exit(2)

    hpc_path = _ensure_hpc_path(metadata, body, readme, config, calc_id)
    scheduler = config.get("scheduler", "slurm")
    job_id = metadata.get("job_id", "")

    # Check queue
    queue_state = ""
    job_finished = True
    if job_id:
        if scheduler == "pbs":
            result = _ssh_run(hostname, f"qstat {job_id} 2>/dev/null", timeout=30)
        else:
            result = _ssh_run(hostname, f"squeue -j {job_id} -h -o '%T' 2>/dev/null", timeout=30)

        output = result.stdout.strip()
        if result.returncode == 0 and output:
            if scheduler == "pbs":
                # Parse PBS qstat output
                lines = output.strip().split("\n")
                for line in lines:
                    if job_id.split(".")[0] in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            queue_state = parts[-2]
                job_finished = queue_state == "" or queue_state == "C"
            else:
                queue_state = output.strip()
                job_finished = False
        else:
            # Job not in queue -> finished
            job_finished = True

    # List remote output files
    output_files = []
    result = _ssh_run(hostname, f"find {hpc_path}output/ -type f 2>/dev/null | head -100", timeout=30)
    if result.returncode == 0 and result.stdout.strip():
        for line in result.stdout.strip().split("\n"):
            rel = line.replace(f"{hpc_path}output/", "")
            if rel:
                output_files.append(rel)

    # List scheduler log files
    log_files = []
    if scheduler == "pbs":
        log_pattern = f"{hpc_path}*.o* {hpc_path}*.e*"
    else:
        log_pattern = f"{hpc_path}slurm-*.out"
    result = _ssh_run(hostname, f"ls {log_pattern} 2>/dev/null", timeout=30)
    if result.returncode == 0 and result.stdout.strip():
        log_files = [Path(f).name for f in result.stdout.strip().split("\n")]

    print(json.dumps({
        "calc_id": calc_id,
        "job_id": job_id,
        "queue_state": queue_state,
        "job_finished": job_finished,
        "output_files": output_files,
        "log_files": log_files,
    }, indent=2))


def cmd_pull(calc_id: str, pull_all: bool = False) -> None:
    """Pull output/ from remote. 50MB limit by default."""
    metadata, body, readme = _get_calc_info(calc_id)
    computer_name = metadata.get("computer", "")
    config = _get_computer_config(computer_name)
    hostname = config["hostname"]

    if not _ssh_check(hostname):
        print(f"Error: SSH not connected to {computer_name} ({hostname}). Run: ssh -MNf {hostname}", file=sys.stderr)
        sys.exit(2)

    hpc_path = _ensure_hpc_path(metadata, body, readme, config, calc_id)
    local_dir = readme.parent
    remote_base = f"{hostname}:{hpc_path}"
    scheduler = config.get("scheduler", "slurm")

    # Pull output/
    output_dir = local_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    max_size = None if pull_all else "50M"
    result = _rsync(f"{remote_base}output/", f"{output_dir}/", max_size=max_size)
    if result.returncode != 0:
        print(f"Warning: rsync output/ returned code {result.returncode}: {result.stderr}", file=sys.stderr)

    # Pull scheduler log files into output/
    if scheduler == "pbs":
        log_pattern = f"{hpc_path}*.o* {hpc_path}*.e*"
    else:
        log_pattern = f"{hpc_path}slurm-*.out"
    log_result = _ssh_run(hostname, f"ls {log_pattern} 2>/dev/null", timeout=30)
    if log_result.returncode == 0 and log_result.stdout.strip():
        for log_file in log_result.stdout.strip().split("\n"):
            log_name = Path(log_file).name
            rsync_result = _rsync(f"{hostname}:{log_file}", str(output_dir / log_name))
            if rsync_result.returncode != 0:
                print(f"Warning: Failed to pull {log_name}", file=sys.stderr)

    # Report large files that were skipped
    if not pull_all:
        large_result = _ssh_run(
            hostname,
            f"find {hpc_path}output/ -size +50M -exec ls -lh {{}} \\;",
            timeout=30,
        )
        if large_result.returncode == 0 and large_result.stdout.strip():
            print("Large files skipped (>50MB):", file=sys.stderr)
            print(large_result.stdout, file=sys.stderr)

    print(f"Pulled {calc_id} from {hostname}:{hpc_path}")


def cmd_update_status(calc_id: str, status: str, job_id: str | None = None) -> None:
    """Update calc status and optionally job_id in frontmatter and index."""
    metadata, body, readme = _get_calc_info(calc_id)
    metadata["status"] = status
    if job_id is not None:
        metadata["job_id"] = job_id
    write_frontmatter(readme, metadata, body)
    _update_index_status(calc_id, status)
    print(f"Updated {calc_id}: status={status}" + (f", job_id={job_id}" if job_id else ""))


# --- Main ---

def main() -> None:
    parser = argparse.ArgumentParser(description="Run a calculation lifecycle")
    sub = parser.add_subparsers(dest="command", required=True)

    p_pre = sub.add_parser("preflight", help="Validate calc is ready to run")
    p_pre.add_argument("calc_id", help="Calculation ID (e.g., c001)")

    p_push = sub.add_parser("push", help="Push input/code/README to remote")
    p_push.add_argument("calc_id", help="Calculation ID")

    p_sub = sub.add_parser("submit", help="Write job script and submit")
    p_sub.add_argument("calc_id", help="Calculation ID")
    p_sub.add_argument("job_script", help="Job script content")

    p_mon = sub.add_parser("monitor", help="Check job status")
    p_mon.add_argument("calc_id", help="Calculation ID")

    p_pull = sub.add_parser("pull", help="Pull output/ from remote")
    p_pull.add_argument("calc_id", help="Calculation ID")
    p_pull.add_argument("--all", action="store_true", dest="pull_all", help="Pull all files (no size limit)")

    p_stat = sub.add_parser("update-status", help="Update calc status")
    p_stat.add_argument("calc_id", help="Calculation ID")
    p_stat.add_argument("status", help="New status value")
    p_stat.add_argument("--job-id", default=None, help="Job ID to store")

    args = parser.parse_args()

    if args.command == "preflight":
        cmd_preflight(args.calc_id)
    elif args.command == "push":
        cmd_push(args.calc_id)
    elif args.command == "submit":
        cmd_submit(args.calc_id, args.job_script)
    elif args.command == "monitor":
        cmd_monitor(args.calc_id)
    elif args.command == "pull":
        cmd_pull(args.calc_id, args.pull_all)
    elif args.command == "update-status":
        cmd_update_status(args.calc_id, args.status, args.job_id)


if __name__ == "__main__":
    main()
