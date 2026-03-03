# psi-skills

Claude Code skills for computational research provenance tracking. Manages calculations and reports using a lightweight, file-based system inspired by AiiDA's provenance graph — no database, no daemon, just markdown and YAML.

## Installation

Copy the `skills/` directory into your project or Claude Code skills path:

```bash
cp -r skills/psi-* /path/to/your/project/.claude/skills/
```

Requires Python >= 3.10 and PyYAML (`pip install pyyaml`).

## Usage

Invoke skills with `/` prefix in Claude Code:

| Skill | Description |
|-------|-------------|
| `/psi-init` | Initialize tracking in current project |
| `/psi-new-calc <title> <code> [parents:...] [tags:...]` | Create a new calculation |
| `/psi-update-calc <id> [field=value ...]` | Update calculation metadata |
| `/psi-new-report <title> [calcs:...] [tags:...]` | Create a new report |
| `/psi-update-report <id> [field=value ...]` | Update report metadata |
| `/psi-status` | Show project status summary |
| `/psi-graph [id]` | Display provenance DAG |
| `/psi-rebuild-index` | Rebuild index files from front matter |
| `/psi-add-computer <name> <type> [hostname:...] [...]` | Register an HPC/local computer |
| `/psi-list-computers` | List registered computers |
| `/psi-update-computer <name> [field=value ...]` | Update a computer's configuration |
| `/psi-remove-computer <name>` | Remove a computer |

## How It Works

psi tracks two entities:
- **Calculations** (`calc_db/c{NNN}/`) — individual computational jobs (DFT, post-processing, scripts)
- **Reports** (`reports/r{NNN}/`) — analysis documents referencing one or more calculations

Relationships form a DAG:

```
c001 (relax) → c002 (scf) → c003 (bands)
                  └→ c004 (dos)
       r001 references c002, c003
```

Each entry is a directory with a `README.md` containing YAML front matter and markdown body. Index files (`calc_db/index.md`, `reports/index.md`) provide tabular overviews. All data is git-friendly, human-readable, and diff-able.

## Architecture

Each skill is a self-contained pair:
- **SKILL.md** — prompt that handles argument parsing, user interaction, and behavioral rules
- **Python script** — handles deterministic file operations (frontmatter, index tables, file locking, rsync)

Scripts inline all needed utilities — no shared modules or packages. The computer registry is stored globally at `~/.claude/agent-memory/psi/computers.yaml`.

## Authors

- **Young Woo Choi** (ywchoi02@sogang.ac.kr, https://yw-choi.github.io)
- **Byeongchan Lee** (bychan.lee@sogang.ac.kr)

## License

MIT
