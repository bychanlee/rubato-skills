# psi-agent

A Claude Code custom agent for computational research provenance tracking. Manages calculation and report tracking using a lightweight, file-based system inspired by AiiDA's provenance graph — no database, no daemon, just markdown and YAML.

## Installation

Copy `psi.md` to your Claude Code agents directory:

```bash
cp psi.md ~/.claude/agents/psi.md
```

## Usage

Issue commands prefixed with `psi:` in Claude Code:

| Command | Description |
|---------|-------------|
| `psi:init` | Initialize tracking in current project |
| `psi:new-calc [title] [code] [parents:...] [tags:...]` | Create a new calculation entry |
| `psi:update-calc [id] [field=value ...]` | Update calculation metadata |
| `psi:new-report [title] [calcs:...] [tags:...]` | Create a new report |
| `psi:update-report [id] [field=value ...]` | Update report metadata |
| `psi:status` | Show project status summary |
| `psi:graph [id?]` | Display provenance DAG |
| `psi:rebuild-index` | Rebuild index files from front matter |

## How It Works

psi tracks two entities:
- **Calculations** (`calc_db/c{NNN}/`) — individual computational jobs (DFT, post-processing, scripts)
- **Reports** (`reports/r{NNN}/`) — analysis documents referencing one or more calculations

Relationships form a DAG (directed acyclic graph):

```
c001 (relax) → c002 (scf) → c003 (bands)
                  └→ c004 (dos)
       r001 references c002, c003
```

All data is stored as markdown with YAML front matter — fully git-friendly, human-readable, and diff-able.

## License

MIT
