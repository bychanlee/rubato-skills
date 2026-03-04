---
name: psi-update-computer
user-invokable: true
description: Update a registered computer's configuration
argument-hint: "<name> [field=value ...]"
---

Update fields on an existing computer in the project registry.

## Usage

```
psi:update-computer <name> [field=value ...]
```

**You** parse the field=value pairs into a JSON object. Then run:

## Execution

```bash
python {skill_dir}/update_computer.py <name> '<json>'
```

The script deep-merges updates into the existing config and writes back to the registry.

If type is `hpc` and hostname is present, the script checks SSH connectivity afterward.

## Rules

- **The computer registry is project-local at `calc_db/computers.yaml`.**
- **NEVER hardcode or guess remote environment details.** When updating HPC fields (work_dir, modules, etc.), discover values from the live system or confirm with the user — same rules as psi-add-computer.
- **Dot notation for nested fields**: `env_setup.modules=vasp,qe` → nested dict update.
- **Comma-separated values become lists**: `queues=normal,development` → `["normal", "development"]`.
