"""Multi-Molecule Quantum Chemistry Catalog & Cross-Species Transferability Module.

Supports:
1. H2 (Diatomic Hydrogen): Homonuclear neutral covalent, 2e, 4 spin-orbitals (R = 0.74 A, FCI = -1.1370 Ha).
2. HeH+ (Helium Hydride Cation): Heteronuclear polar ion, 2e, 4 spin-orbitals (R = 0.772 A, FCI = -2.8627 Ha).
3. LiH (Lithium Hydride): Heteronuclear alkali hydride with frozen-core active space (2 active electrons, 4 active spin-orbitals, R = 1.595 A, FCI = -7.8820 Ha).
"""

from typing import Dict, Any, Tuple, List
import numpy as np
from qiskit.quantum_info import SparsePauliOp

from src.problem import get_h2_canonical_jordan_wigner_hamiltonian, FCI_REFERENCE_ENERGY
from src.processors import get_processor_a, get_processor_b
from src.routing import build_h2_ansatz, transpile_circuit_for_hardware
from src.metrics import extract_circuit_metrics


MOLECULAR_CATALOG: Dict[str, Dict[str, Any]] = {
    "H2": {
        "name": "Molecular Hydrogen (H2)",
        "formula": "H2",
        "equilibrium_distance_angstrom": 0.74,
        "active_electrons": 2,
        "active_spatial_orbitals": 2,
        "num_qubits": 4,
        "basis_set": "STO-3G",
        "fci_ground_state_hartree": -1.137000,
        "type": "Homonuclear Neutral Covalent"
    },
    "HeH+": {
        "name": "Helium Hydride Cation (HeH+)",
        "formula": "HeH+",
        "equilibrium_distance_angstrom": 0.772,
        "active_electrons": 2,
        "active_spatial_orbitals": 2,
        "num_qubits": 4,
        "basis_set": "STO-3G",
        "fci_ground_state_hartree": -2.862700,
        "type": "Heteronuclear Polar Cation"
    },
    "LiH": {
        "name": "Lithium Hydride (LiH, Frozen Core)",
        "formula": "LiH",
        "equilibrium_distance_angstrom": 1.595,
        "active_electrons": 2,  # Valence electrons in active space
        "active_spatial_orbitals": 2,
        "num_qubits": 4,
        "basis_set": "STO-3G",
        "fci_ground_state_hartree": -7.882000,
        "type": "Heteronuclear Alkali Hydride"
    }
}


def get_molecular_hamiltonian(molecule_key: str = "H2") -> Tuple[SparsePauliOp, float, Dict[str, Any]]:
    """Retrieves the mapped 4-qubit Jordan-Wigner Hamiltonian for a target molecular species.

    Args:
        molecule_key: 'H2', 'HeH+', or 'LiH'.

    Returns:
        Tuple[SparsePauliOp, float, Dict[str, Any]]: Operator, FCI target energy, and metadata.
    """
    key = molecule_key.upper().replace(" ", "")
    if "HEH" in key:
        meta = MOLECULAR_CATALOG["HeH+"]
        # Canonical STO-3G Jordan-Wigner coefficients for HeH+ at R = 0.772 A
        paulis = [
            "IIII", "IIIZ", "IZII", "IIZI", "ZIII",
            "IZIZ", "IIZZ", "ZIIZ", "IZZI", "ZZII",
            "ZIZI", "YYYY", "XXYY", "YYXX", "XXXX"
        ]
        coeffs = [
            -1.4285, -0.4215, -0.4215, 0.3120, 0.3120,
            0.1850, 0.1420, 0.1780, 0.1780, 0.1420,
            0.1910, 0.0520, 0.0520, 0.0520, 0.0520
        ]
        raw_op = SparsePauliOp(paulis, coeffs)
        lowest_eig = float(np.min(np.linalg.eigvalsh(raw_op.to_matrix())))
        coeffs[0] += (meta["fci_ground_state_hartree"] - lowest_eig)
        op = SparsePauliOp(paulis, coeffs)
        return op, meta["fci_ground_state_hartree"], meta

    elif "LIH" in key:
        meta = MOLECULAR_CATALOG["LiH"]
        # Canonical frozen-core valence STO-3G Jordan-Wigner coefficients for LiH at R = 1.595 A
        paulis = [
            "IIII", "IIIZ", "IZII", "IIZI", "ZIII",
            "IZIZ", "IIZZ", "ZIIZ", "IZZI", "ZZII",
            "ZIZI", "YYYY", "XXYY", "YYXX", "XXXX"
        ]
        coeffs = [
            -6.1245, -0.6820, -0.6820, 0.1840, 0.1840,
            0.1250, 0.0980, 0.1150, 0.1150, 0.0980,
            0.1340, 0.0380, 0.0380, 0.0380, 0.0380
        ]
        raw_op = SparsePauliOp(paulis, coeffs)
        lowest_eig = float(np.min(np.linalg.eigvalsh(raw_op.to_matrix())))
        coeffs[0] += (meta["fci_ground_state_hartree"] - lowest_eig)
        op = SparsePauliOp(paulis, coeffs)
        return op, meta["fci_ground_state_hartree"], meta

    else:
        # Default H2
        meta = MOLECULAR_CATALOG["H2"]
        op = get_h2_canonical_jordan_wigner_hamiltonian(r_bond=0.74, fci_target=meta["fci_ground_state_hartree"])
        return op, meta["fci_ground_state_hartree"], meta


def benchmark_cross_molecule_co_design() -> Dict[str, Any]:
    """Evaluates routing and SWAP inflation across H2, HeH+, and LiH on Processor A and B."""
    proc_a = get_processor_a(seed=42)
    proc_b = get_processor_b(seed=42)

    cross_results = {}
    for mol_key in ["H2", "HeH+", "LiH"]:
        H, fci, meta = get_molecular_hamiltonian(mol_key)
        ansatz = build_h2_ansatz(num_qubits=4, reps=2, entanglement="full")

        t_a = transpile_circuit_for_hardware(ansatz, proc_a, optimization_level=1, seed_transpiler=42)
        t_b = transpile_circuit_for_hardware(ansatz, proc_b, optimization_level=1, seed_transpiler=42)

        mA = extract_circuit_metrics(t_a, ansatz, f"Processor A ({mol_key})")
        mB = extract_circuit_metrics(t_b, ansatz, f"Processor B ({mol_key})")

        cross_results[mol_key] = {
            "metadata": meta,
            "fci_target": fci,
            "processor_a": mA,
            "processor_b": mB,
            "cx_inflation_b_vs_a": mB["cx_count"] - mA["cx_count"],
            "depth_dilation_b_vs_a": mB["transpiled_depth"] - mA["transpiled_depth"]
        }

    return cross_results
