#!/usr/bin/env python3
"""Plot QE band structure from bands.x XML output.

Dependencies: numpy, matplotlib  (no qwt required)

Usage:
    python qe_plotbands.py bands.xml
    python qe_plotbands.py bands.xml --labels "G M K G"
    python qe_plotbands.py bands.xml --labels "G M K G A L H A" --erange -4 4
    python qe_plotbands.py bands.xml --out my_bands.png --title "WS2 bands"
"""

import argparse
import xml.etree.ElementTree as ET

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

# Physical constants (no external dependency)
_HA_TO_EV   = 27.211396132
_BOHR_TO_ANG = 0.529177210903

mpl.rcParams['font.size'] = 9.0
mpl.rcParams['legend.frameon'] = False
mpl.rcParams['axes.labelweight'] = 'bold'
mpl.rcParams['figure.figsize'] = (3.3, 3.3)
mpl.rcParams['figure.dpi'] = 200

_LABEL_MAP = {
    'G': 'Γ', 'GM': 'Γ', 'GAMMA': 'Γ',
    'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D',
    'H': 'H', 'K': 'K', 'L': 'L', 'M': 'M',
    'R': 'R', 'S': 'S', 'T': 'T', 'U': 'U',
    'V': 'V', 'W': 'W', 'X': 'X', 'Y': 'Y', 'Z': '$\\mathit{Z}$',
}


# ---------------------------------------------------------------------------
# XML parser (replaces qwt.qe.read_band_structure)
# ---------------------------------------------------------------------------

def read_band_structure(pw_xml, relative_to_fermi=True):
    """
    Read band structure from a QE pw.x / bands.x XML file.

    Returns
    -------
    kpath   : ndarray (nk,)       cumulative k-distance [Å⁻¹]
    kpoints : ndarray (nk, 3)     k-points in crystal coordinates
    enk     : ndarray             eigenvalues in eV
                nspin=1 → (nk, nbnd)
                nspin=2 → (2, nk, nbnd)
    """
    root = ET.parse(pw_xml).getroot()
    out  = root.find('output')
    bs   = out.find('band_structure')

    # --- spin type ---
    lsda      = bs.find('lsda').text.strip()      == 'true'
    spinorbit = bs.find('spinorbit').text.strip()  == 'true'
    noncolin  = bs.find('noncolin').text.strip()   == 'true'
    nspin = 4 if (spinorbit or noncolin) else (2 if lsda else 1)

    # --- k-points + eigenvalues ---
    kpoints, enk_list = [], []
    for ks in root.iter('ks_energies'):
        kpoints.append(np.fromstring(ks.find('k_point').text, sep=' '))
        enk_list.append(np.fromstring(ks.find('eigenvalues').text, sep=' '))

    kpoints = np.array(kpoints)          # (nk, 3)
    enk     = np.array(enk_list)         # (nk, nbnd_raw)
    nk      = len(kpoints)

    # nspin=2: eigenvalues are concatenated [up | dn] per k-point
    if nspin == 2:
        nbnd_up = int(bs.find('nbnd_up').text)
        nbnd_dn = int(bs.find('nbnd_dw').text)
        if nbnd_up != nbnd_dn:
            raise ValueError('nbnd_up != nbnd_dn — unequal spin bands not supported')
        nbnd = nbnd_up
        enk  = enk.reshape(nk, 2, nbnd).transpose(1, 0, 2)   # (2, nk, nbnd)

    # --- Fermi energy ---
    ef_node = bs.find('fermi_energy')
    if ef_node is None:
        ef_node = bs.find('highestOccupiedLevel')
    if ef_node is None:
        raise RuntimeError('Fermi energy not found in XML')
    ef = float(ef_node.text) * _HA_TO_EV

    if relative_to_fermi:
        enk = enk * _HA_TO_EV - ef
    else:
        enk = enk * _HA_TO_EV

    # --- reciprocal lattice (crystal coords → Cartesian) ---
    cell_node = out.find('atomic_structure').find('cell')
    avec = np.array([
        np.fromstring(cell_node.find('a1').text, sep=' '),
        np.fromstring(cell_node.find('a2').text, sep=' '),
        np.fromstring(cell_node.find('a3').text, sep=' '),
    ])                                    # in Bohr
    bvec = 2 * np.pi * np.linalg.inv(avec).T   # reciprocal, in Bohr⁻¹

    # --- cumulative k-path [Å⁻¹] ---
    kcart  = kpoints @ bvec               # (nk, 3) in Bohr⁻¹
    dk     = np.linalg.norm(np.diff(kcart, axis=0), axis=1) / _BOHR_TO_ANG
    kpath  = np.concatenate([[0.0], np.cumsum(dk)])

    return kpath, kpoints, enk


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

def parse_labels(label_str):
    return [_LABEL_MAP.get(t.upper(), t) for t in label_str.split()]


def get_hsym_tick_x(kpath, n_labels):
    """Evenly-spaced high-sym positions (standard QE crystal_b)."""
    if n_labels < 2:
        return [kpath[0]]
    idx = np.round(np.linspace(0, len(kpath) - 1, n_labels)).astype(int)
    return kpath[idx].tolist()


def plot_bands(xml_file, labels=None, erange=(-4, 4), out=None, title=None, spin=0):
    kpath, _, enk = read_band_structure(xml_file)

    e = enk[spin] if enk.ndim == 3 else enk   # (nk, nbnd)

    fig, ax = plt.subplots()

    for ib in range(e.shape[1]):
        ax.plot(kpath, e[:, ib], color='blue', lw=0.8)

    if labels is not None:
        tick_x = get_hsym_tick_x(kpath, len(labels))
        # Skip vlines at first/last k-point (borders already serve as boundary)
        for x in tick_x[1:-1]:
            ax.axvline(x=x, color='grey', lw=0.5, ls='--')
        ax.set_xticks(tick_x)
        ax.set_xticklabels(labels, fontsize=10, fontfamily='serif')
    else:
        ax.set_xticks([])

    ax.axhline(y=0, color='grey', ls=':')
    ax.set_xlim(kpath[0], kpath[-1])
    # Hide top/right spines for cleaner look (avoids spine overlapping Z label)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.set_ylim(erange[0], erange[1])
    ax.set_ylabel('Energy (eV)', fontsize=10)
    ax.tick_params(axis='y', labelsize=9)

    if title:
        ax.set_title(title, fontsize=11)

    plt.tight_layout()

    if out is None:
        stem = xml_file.rsplit('.', 1)[0]
        out  = f'{stem}_bands.png'

    fig.savefig(out, dpi=200, bbox_inches='tight')
    print(f'Saved: {out}')
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Plot QE band structure from XML')
    parser.add_argument('xml', help='QE bands XML file (e.g. pwscf.xml)')
    parser.add_argument('--labels', type=str, default=None,
                        help='High-sym k-point labels, space-separated (e.g. "G M K G")')
    parser.add_argument('--erange', type=float, nargs=2, default=[-4, 4],
                        metavar=('EMIN', 'EMAX'), help='Energy window in eV (default: -4 4)')
    parser.add_argument('--out', type=str, default=None,
                        help='Output PNG (default: <xml_stem>_bands.png)')
    parser.add_argument('--title', type=str, default=None, help='Plot title')
    parser.add_argument('--spin', type=int, default=0, choices=[0, 1],
                        help='Spin channel: 0=up, 1=dn (spin-polarized only)')

    args   = parser.parse_args()
    labels = parse_labels(args.labels) if args.labels else None
    plot_bands(args.xml, labels=labels, erange=tuple(args.erange),
               out=args.out, title=args.title, spin=args.spin)


if __name__ == '__main__':
    main()
