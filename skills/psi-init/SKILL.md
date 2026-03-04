---
name: psi-init
user-invokable: true
description: Initialize psi provenance tracking in the current project
---

Initialize psi in the current workspace.

## Usage

```
psi:init
```

## Execution

```bash
python {skill_dir}/init.py
```

This creates `calc_db/` and `reports/` directories with correctly-formatted `index.md` files.

The computer registry lives at `calc_db/computers.yaml` (created on first `psi-add-computer`).

After running, check the computer registry:

```bash
python {psi-list-computers}/list_computers.py --json
```

- If empty: ask the user about their computing environment, then register computers with `psi:add-computer`.
- If populated: show the list and ask if they want to add more.
- For HPC computers: check SSH connectivity and provide setup instructions if disconnected.
