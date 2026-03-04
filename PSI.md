# Using psi skills

Add this to your project's `CLAUDE.md`:

```markdown
## psi — Provenance Tracking

This project uses psi skills (`skills/psi-*`) for computation provenance tracking.

### Setup

Skills are in `skills/psi-*/`. Each has a SKILL.md prompt and a self-contained Python script (requires PyYAML).

### Quick Reference

- `/psi-init` — Initialize `calc_db/` and `reports/` directories
- `/psi-new-calc <title> <code> [parents:...] [tags:...] [computer:...] [type:multi] [subjobs:400,500,600]` — Create calculation
- `/psi-update-calc <id> field=value ...` — Update calculation (supports dot notation: `key_results.energy=-5.43`, `subjobs.500.status=completed`)
- `/psi-new-report <title> [calcs:...] [tags:...]` — Create report
- `/psi-update-report <id> field=value ...` — Update report
- `/psi-status` — Project summary
- `/psi-graph [id]` — Provenance DAG
- `/psi-rebuild-index` — Rebuild indexes from front matter
- `/psi-run-calc <calc_id>` — Push, submit, monitor, and pull a calculation on remote HPC
- `/psi-add-computer`, `/psi-list-computers`, `/psi-update-computer`, `/psi-remove-computer` — Computer registry
- `/psi-fetch-struct <query> [output_dir:path]` — Fetch structure from Materials Project

### Key Rules

- Run `/psi-init` before any other psi skill.
- Create calcs with the same parent **sequentially**, not in parallel.
- Computer registry is project-local at `calc_db/computers.yaml`.
- Do not manually edit `index.md` files — use the skills.
- **Do NOT access other project directories.** Stay within the current project.
- Directory names include tags: `c001_mos2_bulk_relax/`, `r001_mos2_stability/`. The `id` in frontmatter stays bare (`c001`). Always reference calcs/reports by their `id`, not the directory name.

### Creating Reports

- Before creating a report, check `calc_db/index.md` for existing calculations that are relevant.
- If suitable calculations exist, reference them with `calcs:c001,c002,...` when creating the report.
- If no suitable calculation exists, create one first with `/psi-new-calc`, then create the report referencing it.
- Reports must always be grounded in actual calculation data with provenance links maintained.

### Multi-Job Calculations

Use `type:multi` for systematic parameter variations (convergence tests, parameter sweeps) where jobs share the same code but vary parameters:

```
/psi-new-calc "ENCUT Convergence" VASP type:multi subjobs:400,500,600 tags:encut,convergence
```

This creates a single calc with shared `code/` and per-subjob `{label}/input/`, `{label}/output/` directories. Sub-job statuses are tracked individually and auto-aggregated to the top-level status.

Update sub-job status with dot notation:
```
/psi-update-calc c002 subjobs.500.status=completed
```

Run multi-job calcs with `/psi-run-calc` — sub-jobs are submitted sequentially with approval per script.

### Post-Processing

- When asked to do post-processing or analysis, create a report with `/psi-new-report` linking the relevant calculations.
- Save any scripts used for post-processing in the report directory.
```
