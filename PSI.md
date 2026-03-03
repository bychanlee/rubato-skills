# Using psi skills

Add this to your project's `CLAUDE.md`:

```markdown
## psi — Provenance Tracking

This project uses psi skills (`skills/psi-*`) for computation provenance tracking.

### Setup

Skills are in `skills/psi-*/`. Each has a SKILL.md prompt and a self-contained Python script (requires PyYAML).

### Quick Reference

- `/psi-init` — Initialize `calc_db/` and `reports/` directories
- `/psi-new-calc <title> <code> [parents:...] [tags:...] [computer:...]` — Create calculation
- `/psi-update-calc <id> field=value ...` — Update calculation (supports dot notation: `key_results.energy=-5.43`)
- `/psi-new-report <title> [calcs:...] [tags:...]` — Create report
- `/psi-update-report <id> field=value ...` — Update report
- `/psi-status` — Project summary
- `/psi-graph [id]` — Provenance DAG
- `/psi-rebuild-index` — Rebuild indexes from front matter
- `/psi-add-computer`, `/psi-list-computers`, `/psi-update-computer`, `/psi-remove-computer` — Computer registry

### Key Rules

- Run `/psi-init` before any other psi skill.
- Create calcs with the same parent **sequentially**, not in parallel.
- Computer registry is global (`~/.claude/agent-memory/psi/computers.yaml`), not per-project.
- Do not manually edit `index.md` files — use the skills.
```
