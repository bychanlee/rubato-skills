#!/usr/bin/env python3
"""Fetch structure files from Materials Project database.

Accepts JSON input:
    python fetch_struct.py '{"query": "mp-149", "output_dir": "."}'

Outputs JSON to stdout.
"""

import json
import os
import re
import sys


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SPACEGROUP_TO_POLYMORPH = {
    194: "2H",
    187: "1H",
    166: "3R",
    164: "1T",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NLAYERS_SUFFIX = {1: "monolayer", 2: "bilayer"}


def _make_filename(structure, symmetry, output_dir: str = ".",
                   n_layers: int | None = None,
                   formula_pretty: str | None = None) -> str:
    formula = formula_pretty or structure.composition.reduced_formula
    if n_layers is not None:
        suffix = _NLAYERS_SUFFIX.get(n_layers, f"{n_layers}L")
        name = f"{formula}_{suffix}.cif"
    else:
        sg_number = symmetry.number if symmetry else None
        polymorph = SPACEGROUP_TO_POLYMORPH.get(sg_number)
        if polymorph:
            name = f"{formula}_{polymorph}.cif"
        else:
            name = f"{formula}.cif"
    return os.path.join(output_dir, name)


def _is_mp_id(query: str) -> bool:
    return bool(re.match(r"^mp-\d+$", query.strip()))


def _parse_natural_language(query: str) -> dict:
    """Parse natural language query for dimensionality, crystal system,
    polymorph, and formula hints."""
    query_lower = query.lower()
    hints = {
        "dimensionality": None,
        "crystal_system": None,
        "polymorph": None,
        "formula": None,
        "n_layers": None,
    }

    # Dimensionality & layer count
    if "monolayer" in query_lower or "single layer" in query_lower:
        hints["dimensionality"] = "2D"
        hints["n_layers"] = 1
    elif "bilayer" in query_lower or "double layer" in query_lower:
        hints["dimensionality"] = "2D"
        hints["n_layers"] = 2
    elif "bulk" in query_lower:
        hints["dimensionality"] = "3D"
    elif "2d" in query_lower:
        hints["dimensionality"] = "2D"
        hints["n_layers"] = 1
    elif "3d" in query_lower:
        hints["dimensionality"] = "3D"
    elif "nanoribbon" in query_lower:
        hints["dimensionality"] = "1D"
    elif "nanowire" in query_lower:
        hints["dimensionality"] = "1D"

    # Crystal system
    crystal_systems = [
        "cubic", "hexagonal", "tetragonal", "orthorhombic",
        "monoclinic", "triclinic", "rhombohedral",
    ]
    for cs in crystal_systems:
        if cs in query_lower:
            hints["crystal_system"] = cs.capitalize()
            break

    # Polymorph (1H, 2H, 1T, 3R, etc.)
    polymorph_match = re.search(r"(\d+[HRT])", query, re.IGNORECASE)
    if polymorph_match:
        hints["polymorph"] = polymorph_match.group(1).upper()

    # Formula: skip known keywords, pick first chemical-formula-like token
    skip_words = {
        "bulk", "monolayer", "bilayer", "single", "double", "layer",
        "thin", "film", "crystal",
        "2d", "3d", "1d", "cubic", "hexagonal", "tetragonal", "orthorhombic",
        "monoclinic", "triclinic", "rhombohedral", "nanoribbon", "nanowire",
        "1h", "2h", "3r", "1t",
    }
    formula_re = re.compile(r"^[A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)+$")
    element_re = re.compile(r"^[A-Z][a-z]?\d*$")

    for word in query.split():
        if word.lower() in skip_words:
            continue
        if formula_re.match(word) or element_re.match(word):
            hints["formula"] = word
            break

    return hints


# ---------------------------------------------------------------------------
# Layer extraction
# ---------------------------------------------------------------------------

def _extract_layers(structure, n_layers: int = 1, vacuum: float = 15.0):
    """Extract n_layers from a layered bulk structure and add vacuum.

    Uses cyclic gap analysis on fractional z to handle PBC correctly,
    and operates in fractional coordinates throughout (valid for any
    cell geometry, not just orthogonal cells).

    Returns (new_structure, n_total_layers) or raises ValueError.
    """
    import numpy as np
    from pymatgen.core import Structure, Lattice

    sites = list(structure)
    n_atoms = len(sites)
    frac_zs = np.array([s.frac_coords[2] for s in sites])
    sorted_indices = np.argsort(frac_zs)
    sorted_z = frac_zs[sorted_indices]

    if n_atoms < 3:
        raise ValueError(
            f"Structure has only {n_atoms} atoms — cannot detect layers"
        )

    # Compute gaps including cyclic (PBC) wrap-around gap
    consec_gaps = np.diff(sorted_z)
    cyclic_gap = sorted_z[0] + 1.0 - sorted_z[-1]
    all_gaps = np.append(consec_gaps, cyclic_gap)

    if len(all_gaps) < 2:
        raise ValueError("Too few atoms to identify layered structure")

    max_gap = all_gaps.max()
    other_gaps = np.delete(all_gaps, np.argmax(all_gaps))
    median_other = float(np.median(other_gaps))

    if median_other == 0 or max_gap / median_other < 1.5:
        formula = structure.composition.reduced_formula
        raise ValueError(
            f"{formula} does not appear to be a layered material"
        )

    # Mark large gaps as layer boundaries
    threshold = (max_gap + median_other) / 2
    boundary_mask = all_gaps > threshold

    # Start walk from just after the first boundary gap so no layer
    # straddles the starting point.
    first_boundary = int(np.where(boundary_mask)[0][0])
    start_pos = (first_boundary + 1) % n_atoms

    # Walk through sorted atoms, grouping into layers.
    # Track "unwrapped" fractional z (monotonically increasing) so that
    # layers wrapping around z=0 get correct thickness.
    layers = [[sorted_indices[start_pos]]]
    layer_unwrapped = [[sorted_z[start_pos]]]
    running_z = float(sorted_z[start_pos])

    for step in range(1, n_atoms):
        prev_pos = (start_pos + step - 1) % n_atoms
        curr_pos = (start_pos + step) % n_atoms

        gap = sorted_z[curr_pos] - sorted_z[prev_pos]
        if gap < 0:
            gap += 1.0  # PBC wrap
        running_z += gap

        if boundary_mask[prev_pos]:
            layers.append([sorted_indices[curr_pos]])
            layer_unwrapped.append([running_z])
        else:
            layers[-1].append(sorted_indices[curr_pos])
            layer_unwrapped[-1].append(running_z)

    total_layers = len(layers)
    if n_layers > total_layers:
        raise ValueError(
            f"Requested {n_layers} layers but structure has only "
            f"{total_layers} layers per unit cell"
        )

    # Select layers and compute thickness using fractional z × c
    sel_indices = [i for layer in layers[:n_layers] for i in layer]
    sel_unwrapped = np.array(
        [z for uzs in layer_unwrapped[:n_layers] for z in uzs]
    )

    old_lat = structure.lattice
    old_c = old_lat.c
    frac_thickness = float(sel_unwrapped.max() - sel_unwrapped.min())
    layer_thickness = frac_thickness * old_c
    new_c = layer_thickness + vacuum

    new_lat = Lattice.from_parameters(
        old_lat.a, old_lat.b, new_c,
        old_lat.alpha, old_lat.beta, old_lat.gamma,
    )

    # Build new structure — center layer in the new cell along c
    center_uz = (sel_unwrapped.max() + sel_unwrapped.min()) / 2
    new_species = []
    new_frac_coords = []
    for atom_idx, uz in zip(sel_indices, sel_unwrapped):
        site = sites[atom_idx]
        new_species.append(site.species_string)
        new_frac_z = (uz - center_uz) * (old_c / new_c) + 0.5
        new_frac_coords.append([
            site.frac_coords[0], site.frac_coords[1], new_frac_z,
        ])

    return (
        Structure(new_lat, new_species, new_frac_coords),
        total_layers,
    )


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

def _fetch_by_mp_id(mp_id: str) -> dict | None:
    from mp_api.client import MPRester

    with MPRester() as mpr:
        docs = mpr.materials.summary.search(
            material_ids=[mp_id],
            fields=["material_id", "formula_pretty", "symmetry", "structure"],
        )

    if not docs:
        return None

    result = docs[0]
    return {
        "material_id": str(result.material_id),
        "formula": result.formula_pretty,
        "structure": result.structure,
        "symmetry": result.symmetry,
    }


def _search_by_formula(formula: str, max_results: int = 10) -> list[dict]:
    from mp_api.client import MPRester

    with MPRester() as mpr:
        docs = mpr.materials.summary.search(
            formula=formula,
            fields=[
                "material_id", "formula_pretty", "symmetry",
                "nsites", "energy_above_hull",
            ],
        )

    docs_sorted = sorted(
        docs,
        key=lambda d: (
            d.energy_above_hull
            if d.energy_above_hull is not None
            else float("inf")
        ),
    )
    results = []
    for doc in docs_sorted[:max_results]:
        results.append({
            "material_id": str(doc.material_id),
            "formula": doc.formula_pretty,
            "crystal_system": (
                str(doc.symmetry.crystal_system) if doc.symmetry else None
            ),
            "n_atoms": doc.nsites,
            "energy_above_hull": doc.energy_above_hull,
        })
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _ok(payload: dict) -> str:
    return json.dumps({"status": "ok", **payload}, indent=2)


def _error(message: str) -> str:
    return json.dumps({"status": "error", "message": message}, indent=2)


def main() -> None:
    if len(sys.argv) < 2:
        print(_error("Usage: python fetch_struct.py '<json>'"))
        sys.exit(1)

    try:
        args = json.loads(sys.argv[1])
    except json.JSONDecodeError as exc:
        print(_error(f"Invalid JSON: {exc}"))
        sys.exit(1)

    query = args.get("query", "").strip()
    output_dir = args.get("output_dir", ".")
    n_layers = args.get("n_layers")  # int or None
    vacuum = args.get("vacuum", 15.0)

    if not query:
        print(_error("Missing required field: query"))
        sys.exit(1)

    # Case 1: Direct MP ID lookup
    if _is_mp_id(query):
        try:
            result = _fetch_by_mp_id(query)
        except Exception as exc:
            print(_error(f"Failed to fetch {query}: {exc}"))
            sys.exit(1)

        if result is None:
            print(_error(f"No result found for {query}"))
            sys.exit(1)

        structure = result["structure"]
        derived = None

        # Extract layers if requested
        if n_layers is not None:
            try:
                structure, total_layers = _extract_layers(
                    structure, n_layers=n_layers, vacuum=vacuum,
                )
                derived = _NLAYERS_SUFFIX.get(n_layers, f"{n_layers}L")
            except ValueError as exc:
                print(_error(str(exc)))
                sys.exit(1)

        filename = _make_filename(
            structure, result["symmetry"], output_dir,
            n_layers=n_layers, formula_pretty=result["formula"],
        )
        try:
            os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
            structure.to(filename=filename)
        except Exception as exc:
            print(_error(f"Failed to save structure: {exc}"))
            sys.exit(1)

        crystal_system = (
            str(result["symmetry"].crystal_system)
            if result["symmetry"] else None
        )
        result_payload = {
            "material_id": result["material_id"],
            "formula": result["formula"],
            "crystal_system": crystal_system,
            "filename": os.path.basename(filename),
        }
        if derived:
            result_payload["derived"] = derived

        print(_ok({"mode": "mp_id", "result": result_payload}))
        return

    # Case 2: Natural language or formula search
    hints = _parse_natural_language(query)
    search_formula = hints["formula"] or query.split()[0]

    try:
        results = _search_by_formula(search_formula)
    except Exception as exc:
        print(_error(f"Search failed for {search_formula}: {exc}"))
        sys.exit(1)

    if not results:
        print(_error(f"No results found for {search_formula}"))
        sys.exit(1)

    # Apply natural-language filters
    filtered = results
    if hints["crystal_system"]:
        filtered = [
            r for r in filtered
            if r["crystal_system"]
            and r["crystal_system"].lower() == hints["crystal_system"].lower()
        ]
    # (Polymorph / dimensionality filtering requires structure data;
    #  we skip those for the listing mode to keep API calls light.)

    if not filtered:
        filtered = results  # fall back to unfiltered

    print(_ok({
        "mode": "search",
        "search_formula": search_formula,
        "hints": {k: v for k, v in hints.items() if v is not None},
        "results": filtered,
    }))


if __name__ == "__main__":
    main()
