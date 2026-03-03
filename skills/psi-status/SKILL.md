---
name: psi-status
user-invokable: true
description: Show project status summary
---

Display a summary of the current psi project.

## Usage

```
psi:status
```

## Execution

```bash
python {skill_dir}/status.py
```

Outputs JSON with: calc counts by status, recent calcs, orphan calcs (completed with no reports), draft reports.

Format the JSON output into a human-readable summary for the user.
