# RUBATO

**RUBATO: Research Utility Bot for Ab-initio TOolkits**

Every ab-initio researcher knows the feeling: you just finished a QE bands calculation and now you need to plot it — so you dig up a plotting script from a previous project, fix the hardcoded paths, remember what `lsym` does, and spend 30 minutes on something that should take 30 seconds. Or you want a QE input for a new material and spend time copy-pasting a template and manually looking up pseudopotentials.

RUBATO is a collection of [Claude Code](https://claude.ai/code) slash commands (skills) that eliminate that friction. Each command handles one specific task — fetching a structure, preparing an input file, plotting a band structure, generating a job script — and can be used independently, whenever you need it.

---

## Supported Codes

| Code | Version | Purpose |
|------|---------|---------|
| [Quantum ESPRESSO](https://www.quantum-espresso.org/) | 7.3.1 | Relax, SCF, NSCF, Bands, Phonons (DFPT) |
| [BerkeleyGW](https://berkeleygw.org/) | 4.0 | GW self-energy, BSE optical spectra |

---

## Setup

```bash
git clone https://github.com/BryceByeongchan/rubato-skills.git ~/tools/rubato
cd ~/tools/rubato && ./install.sh
```

The installer handles everything: checks Python 3.10+, installs required packages (`pyyaml`, `numpy`, `matplotlib`), and symlinks all skills into `~/.claude/skills/`. After install, `/rubato:*` commands are available in **every** Claude Code project.

For `/rubato:fetch-struct` and `/rubato:qe-input-generator` (Materials Project integration), also run:

```bash
pip install pymatgen mp-api
export MP_API_KEY="your-key-here"   # https://materialsproject.org/api
```

To update: `cd ~/tools/rubato && git pull` (symlinks update in place).
To uninstall: `cd ~/tools/rubato && ./install.sh --uninstall`

---

## How It Works

Each command is **independent** — use whichever you need, whenever you need it. No setup, no state to maintain.

```
/rubato:fetch-struct "2H bulk MoS2"        <- grab CIF from Materials Project
/rubato:qe-input-generator MoS2.cif scf   <- generate SCF input with physics-aware defaults
  ... run your QE calculation ...
/rubato:qe-plotbands MoS2.bands.xml        <- plot band structure from XML, done
```

---

## Skills Reference

### General

| Command | Description |
|---------|-------------|
| `/rubato:fetch-struct` | Fetch CIF files from the Materials Project database by MP-ID, formula, or natural language (e.g. `"2H bulk WS2"`) |

### Quantum ESPRESSO

| Command | Description |
|---------|-------------|
| `/rubato:qe-input-generator` | Generate QE input with physics-aware suggestions (magnetic, metallic, DFT+U, SOC) |
| `/rubato:qe-input-validator` | Validate QE input against official flags from documentation |
| `/rubato:qe-plotbands` | Plot band structure from `bands.x` XML output (spin-polarized, SOC) |

### BerkeleyGW

| Command | Description |
|---------|-------------|
| `/rubato:bgw-kgridx` | Generate `kgrid.inp` from XSF structure file for k-point generation |
| `/rubato:bgw-pw2bgw` | Generate `pw2bgw.inp` (QE -> BGW format conversion) |
| `/rubato:bgw-parabands` | Generate `parabands.inp` (many empty bands via pseudobands) |
| `/rubato:bgw-epsilon` | Generate and validate `epsilon.inp` (dielectric function) |
| `/rubato:bgw-sigma` | Generate and validate `sigma.inp` (self-energy / QP correction) |
| `/rubato:bgw-kernel` | Generate and validate `kernel.inp` (BSE electron-hole kernel) |
| `/rubato:bgw-absorption` | Generate and validate `absorption.inp` (BSE optical absorption) |
| `/rubato:bgw-gw-conv-sigma` | Convergence sweep: sigma-only (fixed epsmat) |
| `/rubato:bgw-gw-conv-epsilon` | Convergence sweep: epsilon+sigma (coarse q-grid) |
| `/rubato:bgw-gw-conv-analyze` | Parse `sigma.out` -> QP gap convergence table |

---

## Input Validation

### How it works

The BerkeleyGW input skills (`epsilon`, `sigma`, `kernel`, `absorption`) have a built-in **input validator** that catches keyword errors before you submit a calculation.

Each skill has two modes:

```
/rubato:bgw-epsilon epsilon_cutoff:15 number_bands:200 ...   # generate mode
/rubato:bgw-epsilon validate:epsilon.inp                      # validate mode
```

In **generate mode**, the validator runs automatically on the generated file before showing it to you. In **validate mode**, you can check any existing input file on demand.

### Reference keyword database

The validator checks keywords against a **reference JSON** extracted from the BerkeleyGW 4.0 source code (`inread.f90` for each executable). These files live in each skill's `refs/` directory:

```
skills/rubato-bgw-epsilon/refs/epsilon.json    (~85 keywords)
skills/rubato-bgw-sigma/refs/sigma.json        (~95 keywords)
skills/rubato-bgw-kernel/refs/kernel.json      (~40 keywords)
skills/rubato-bgw-absorption/refs/absorption.json  (~105 keywords)
```

Each keyword entry includes:

```json
{
  "epsilon_cutoff": {
    "type": "REAL",
    "default": null,
    "info": "Energy cutoff for the dielectric matrix in Ry."
  }
}
```

Keywords were extracted from:
- Main `inread.f90` / `inread_kernel.f90` routines (direct `case('keyword')` parsing)
- Shared modules: `scissors.f90` (scissors operators), `inread_common.f90` (Coulomb truncation, screening), `algos_*.f90` (GPU algorithms)
- Official documentation files in `documentation/input_files/`

### Validation layers

**1. Mechanical validation** (Python script `bgw_validate.py`):
- **Unknown keyword detection** — catches typos with fuzzy suggestions (e.g., `screening_semicondcutor` -> `screening_semiconductor`)
- **Type checking** — INTEGER, REAL, LOGICAL, STRING values validated against expected types
- **Unknown block detection** — flags unrecognized `begin ... end` blocks
- **Deprecated keyword warnings** — flags keywords marked as deprecated in the reference

**2. Semantic validation** (Claude's domain knowledge via SKILL.md rules):
- **Cross-file consistency** — `screened_coulomb_cutoff` must be <= `epsilon_cutoff`; `frequency_dependence` must match between epsilon and sigma; `number_val_bands_coarse` must match between kernel and absorption
- **Wrong-file detection** — `screened_coulomb_cutoff` in epsilon.inp is an error (that keyword belongs to sigma.inp)
- **Mutual exclusion** — only one Coulomb truncation type, only one screening model, only one solver algorithm
- **Physics sanity checks** — unusual cutoff values, missing required blocks, 2D system without slab truncation

**3. Keyword lookup** — look up any keyword's official documentation:

```
/rubato:bgw-epsilon validate:epsilon.inp
```

### Comparison with QE validator

| | QE (`rubato-qe-input-validator`) | BGW (`rubato-bgw-epsilon`, etc.) |
|---|---|---|
| Architecture | Standalone validator skill | Integrated into each generator skill |
| Scope | 430 keywords across 7 executables | ~325 keywords across 4 executables |
| Input format | Fortran namelists (`&CONTROL ... /`) | Flat `keyword value` pairs |
| Reference source | QE `INPUT_*.def` files | BGW `inread.f90` source code |
| Regeneration | `qe_source:` flag to re-parse from source | Manual update of refs JSON |

---

## Prerequisites

- [Claude Code](https://claude.ai/code) CLI installed and authenticated
- Python 3.10+ and pip

## Authors

- **Byeongchan Lee** (bychan.lee@sogang.ac.kr, https://brycebyeongchan.github.io/)

## License

MIT
