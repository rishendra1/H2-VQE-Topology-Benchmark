"""Native Superconducting Basis Gate Decomposition Module (ECR and CZ).

Benchmarking physical microwave decompositions used on real IBM Quantum devices:
1. Heron / Falcon Basis: {rz, sx, x, ecr} (Echoed Cross-Resonance)
2. Eagle / System Two Basis: {rz, sx, x, cz} (Controlled-Phase)
3. Standard Textbook Basis: {rz, sx, x, cx} (Controlled-NOT)
"""

from typing import Dict, Any, List, Tuple
from qiskit import QuantumCircuit, transpile
from qiskit.providers.backend import BackendV2

from src.routing import build_h2_ansatz
from src.processors import get_processor_a, get_processor_b


NATIVE_BASIS_SETS = {
    "CX_Standard": ["rz", "sx", "x", "cx"],
    "ECR_Falcon": ["rz", "sx", "x", "ecr"],
    "CZ_Eagle": ["rz", "sx", "x", "cz"]
}


def transpile_to_native_basis(
    circuit: QuantumCircuit,
    backend: BackendV2,
    basis_name: str = "ECR_Falcon",
    optimization_level: int = 1,
    seed: int = 42
) -> Tuple[QuantumCircuit, Dict[str, Any]]:
    """Transpiles a circuit targeting a specific native superconducting gate basis."""
    basis_gates = NATIVE_BASIS_SETS.get(basis_name, NATIVE_BASIS_SETS["CX_Standard"])
    transpiled = transpile(
        circuit,
        backend=backend,
        basis_gates=basis_gates,
        optimization_level=optimization_level,
        seed_transpiler=seed
    )

    ops = dict(transpiled.count_ops())
    depth = transpiled.depth()
    total_gates = sum(ops.values())

    # Count 2-qubit native entangling gates
    entangling_count = ops.get("ecr", 0) + ops.get("cz", 0) + ops.get("cx", 0)

    summary = {
        "basis_name": basis_name,
        "basis_gates": basis_gates,
        "transpiled_depth": depth,
        "total_gates": total_gates,
        "entangling_gate_count": entangling_count,
        "ops_breakdown": ops,
    }
    return transpiled, summary


def benchmark_all_native_bases(ansatz: QuantumCircuit = None) -> Dict[str, Any]:
    """Evaluates transpilation across standard CX, native ECR, and native CZ on Processor A and B."""
    if ansatz is None:
        ansatz = build_h2_ansatz(num_qubits=4, reps=2, entanglement="linear")

    proc_a = get_processor_a(seed=42)
    proc_b = get_processor_b(seed=42)

    results_a = {}
    results_b = {}

    for b_name in NATIVE_BASIS_SETS.keys():
        _, s_a = transpile_to_native_basis(ansatz, proc_a, basis_name=b_name)
        _, s_b = transpile_to_native_basis(ansatz, proc_b, basis_name=b_name)
        results_a[b_name] = s_a
        results_b[b_name] = s_b

    return {
        "processor_a": results_a,
        "processor_b": results_b,
    }
