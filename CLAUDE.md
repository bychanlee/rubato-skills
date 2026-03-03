# psi-skills

A set of Claude Code skills for computational research provenance tracking. Each skill is a self-contained unit with a SKILL.md prompt and a Python script.

## Project Structure

```
skills/
├── psi-init/           # Initialize project (calc_db/, reports/)
├── psi-new-calc/       # Create a new calculation
├── psi-update-calc/    # Update calculation metadata
├── psi-new-report/     # Create a new report
├── psi-update-report/  # Update report metadata
├── psi-status/         # Show project status summary
├── psi-graph/          # Display provenance DAG
├── psi-add-computer/   # Register a computer
├── psi-list-computers/ # List registered computers
├── psi-remove-computer/# Remove a computer
├── psi-update-computer/# Update a computer's configuration
└── psi-rebuild-index/  # Rebuild index from front matter
```

Each directory contains:
- `SKILL.md` — Skill prompt (usage, rules, execution instructions)
- `*.py` — Self-contained Python script (only depends on PyYAML)

## Design Principles

- **Self-contained scripts**: Each Python script inlines all needed utilities (frontmatter, markdown_table, filelock). No shared imports.
- **Deterministic file ops in Python, judgment in prompts**: Scripts handle file I/O, locking, and index management. SKILL.md prompts handle argument parsing and user interaction.
- **Computer registry is global**: `~/.claude/agent-memory/psi/computers.yaml`, shared across projects.

## Development Rules

- **SKILL.md files are prompts, not code.** Edits must preserve natural-language clarity.
- **Every behavioral fix must become a rule in the relevant SKILL.md.** Not just a memory note.
- **Keep rules minimal and precise.** Each rule addresses one specific failure mode.
- **Do not create shared utility modules.** Each script must be self-contained.
- **After adding or modifying skills, update PSI.md and README.md** to reflect the changes.
