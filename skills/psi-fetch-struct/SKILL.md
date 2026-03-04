---
name: psi-fetch-struct
user-invokable: true
description: Fetch structure files from Materials Project
argument-hint: "<query> [output_dir:path]"
---

Fetch `.cif` structure files from the Materials Project database.

## Prerequisites

Requires `mp-api` and `pymatgen`:

```bash
pip install pymatgen mp-api
```

Requires Materials Project API key configured via `pmg config --add PMG_MAPI_KEY your_key` (writes to `~/.pmgrc.yaml`). See README.md for setup.

## Usage

```
psi:fetch-struct <query> [output_dir:path]
```

**You** parse the user's arguments — this requires judgment:

- **query**: One of three input types (see below).
- `output_dir:path` — Directory to save the `.cif` file. Defaults to current directory.

### Input Types

1. **MP ID** (e.g., `mp-149`): Direct lookup by Materials Project ID. Downloads and saves the structure.
2. **Formula** (e.g., `WS2`): Search by chemical formula. Lists top results sorted by energy above hull.
3. **Natural Language** (e.g., `"2H bulk WS2"`): Parsed for dimensionality, crystal system, and polymorph hints, then filtered.

## Execution

Build a JSON object from parsed arguments and run:

```bash
python {skill_dir}/fetch_struct.py '<json>'
```

JSON fields:
- `query` (string) — MP ID, formula, or natural language
- `output_dir` (string, optional) — defaults to `.`
- `n_layers` (int, optional) — 1 for monolayer, 2 for bilayer. Extracts layers from bulk and adds vacuum.
- `vacuum` (float, optional) — vacuum thickness in Angstrom, defaults to 15.0

### Output Format

The script returns JSON:

**For MP ID lookup (single result):**
```json
{
  "status": "ok",
  "mode": "mp_id",
  "result": {
    "material_id": "mp-2815",
    "formula": "MoS2",
    "crystal_system": "Hexagonal",
    "filename": "MoS2_monolayer.cif",
    "derived": "monolayer"
  }
}
```

**For formula/natural-language search (multiple results):**
```json
{
  "status": "ok",
  "mode": "search",
  "results": [
    {
      "material_id": "mp-224",
      "formula": "WS2",
      "crystal_system": "Hexagonal",
      "n_atoms": 6,
      "energy_above_hull": 0.0
    }
  ]
}
```

After showing search results, prompt the user to pick a specific MP ID and re-run:

```
psi:fetch-struct mp-224
```

### Monolayer / Bilayer Workflow

Materials Project only has bulk structures. When the user requests a monolayer or bilayer:

1. Parse the natural language to detect `n_layers` (monolayer → 1, bilayer → 2).
2. Run a formula search to list candidate bulk structures.
3. Pick the ground-state structure (lowest energy above hull) — or ask the user if multiple polymorphs are relevant.
4. Re-run with the chosen MP ID and `n_layers` set in the JSON.

The script automatically extracts layers from the bulk by gap-based z-clustering and adds vacuum. If the material is not layered, it returns an error.

## Rules

- If the API key is not configured, `MPRester()` will raise an error. Show the setup instructions from the Prerequisites section and stop.
- For formula searches, show at most 10 results sorted by energy above hull.
- For natural language queries, apply crystal system filters when detected. Polymorph and dimensionality hints are extracted and returned but not filtered server-side (would require fetching full structures for each candidate).
- When saving a `.cif` file, use the naming convention `{Formula}_{Polymorph}.cif` for bulk, `{Formula}_monolayer.cif` / `{Formula}_bilayer.cif` for extracted layers.
- **When the user requests a monolayer/bilayer, always set `n_layers` in the JSON.** Do not save the bulk structure when the user asked for a monolayer.
