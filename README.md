# psi-skills

Claude Code skills for computational research provenance tracking. Manages calculations and reports using a lightweight, file-based system inspired by AiiDA's provenance graph — no database, no daemon, just markdown and YAML.

## Quick Install

```bash
./install.sh
```

This will:
- Verify Python >= 3.10 is installed
- Install PyYAML dependency if needed
- Copy all 14 skills to `.claude/skills/`

### Materials Project API Key (for `/psi-fetch-struct`)

`/psi-fetch-struct` requires a [Materials Project](https://materialsproject.org/) API key and the `mp-api`/`pymatgen` packages:

```bash
pip install pymatgen mp-api
```

Set your API key via pymatgen config:

```bash
pmg config --add PMG_MAPI_KEY your_key
```

Get a free key at https://materialsproject.org/api.


## Usage

Invoke skills with `/` prefix in Claude Code:

| Skill | Description |
|-------|-------------|
| `/psi-init` | Initialize tracking in current project |
| `/psi-new-calc <title> <code> [parents:...] [tags:...] [type:multi] [subjobs:...]` | Create a new calculation |
| `/psi-update-calc <id> [field=value ...]` | Update calculation metadata |
| `/psi-new-report <title> [calcs:...] [tags:...]` | Create a new report |
| `/psi-update-report <id> [field=value ...]` | Update report metadata |
| `/psi-status` | Show project status summary |
| `/psi-graph [id]` | Display provenance DAG |
| `/psi-rebuild-index` | Rebuild index files from front matter |
| `/psi-run-calc <calc_id>` | Run a calc: push, submit, monitor, pull |
| `/psi-add-computer <name> <type> [hostname:...] [...]` | Register an HPC/local computer |
| `/psi-list-computers` | List registered computers |
| `/psi-update-computer <name> [field=value ...]` | Update a computer's configuration |
| `/psi-remove-computer <name>` | Remove a computer |
| `/psi-fetch-struct <query> [output_dir:path]` | Fetch structure from Materials Project |

## How It Works

psi tracks two entities:
- **Calculations** (`calc_db/c{NNN}_tag1_tag2/`) — individual computational jobs (DFT, post-processing, scripts)
- **Reports** (`reports/r{NNN}_tag1_tag2/`) — analysis documents referencing one or more calculations

Relationships form a DAG:

```
c001_si_relax (relax) → c002_si_scf (scf) → c003_si_bands (bands)
                          └→ c004_si_dos (dos)
       r001_si_stability references c002, c003
```

Each entry is a directory with a `README.md` containing YAML front matter and markdown body. Directory names include tags for readability (e.g., `c001_mos2_relax/`) while the `id` in frontmatter stays bare (`c001`). Index files (`calc_db/index.md`, `reports/index.md`) provide tabular overviews. All data is git-friendly, human-readable, and diff-able.

Calculations support **multi-job** mode (`type:multi`) for parameter sweeps and convergence tests — a single calc with shared `code/` and per-subjob `{label}/input/`, `{label}/output/` directories, with automatic status aggregation.

## Architecture

Each skill is a self-contained pair:
- **SKILL.md** — prompt that handles argument parsing, user interaction, and behavioral rules
- **Python script** — handles deterministic file operations (frontmatter, index tables, file locking, rsync)

Scripts inline all needed utilities — no shared modules or packages. The computer registry is stored per-project at `calc_db/computers.yaml`.

## Authors

- **Young Woo Choi** (ywchoi02@sogang.ac.kr, https://yw-choi.github.io)
- **Byeongchan Lee** (bychan.lee@sogang.ac.kr, https://brycebyeongchan.github.io/)

## License

MIT
