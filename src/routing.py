"""Compilation and Routing Module for VQE Circuits.

Implements:
- VQE Ansatz construction with Hartree-Fock state initialization.
- Hardware-targeted transpilation with strict hackathon specifications:
  - optimization_level = 1
  - seed_transpiler = 42
- Comparative routing and gate metric extraction.
"""

from typing import Tuple, Dict, Any, Optional
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import n_local
from qiskit.providers.backend import BackendV2

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.metrics import extract_circuit_metrics, compare_metrics


def build_h2_ansatz(
    num_qubits: int = 4,
    reps: int = 2,
    entanglement: str = "full",
    init_hartree_fock: bool = True
) -> QuantumCircuit:
    """Constructs a hardware-efficient VQE ansatz for the H2 molecular Hamiltonian.

    Initializes the state into the Hartree-Fock configuration |1010> (two electrons
    occupying spatial orbital 0 for both alpha and beta spins), followed by parameterized
    single-qubit rotation layers (RY, RZ) and entangling CX layers.

    Args:
        num_qubits: Number of qubits matching Jordan-Wigner mapped H2 (default: 4).
        reps: Repetitions of the variational rotation-entanglement layers (default: 2).
        entanglement: Entanglement topology ('full' or 'linear').
        init_hartree_fock: Whether to prepend Hartree-Fock state preparation (default: True).

    Returns:
        QuantumCircuit: Parameterized VQE ansatz circuit.
    """
    ansatz = QuantumCircuit(num_qubits, name="H2_VQE_Ansatz")

    if init_hartree_fock:
        # Spin-orbital occupation for singlet H2 ground state |1010>
        # (qubits 1 and 3 in Qiskit little-endian indexing)
        ansatz.x(1)
        ansatz.x(3)

    var_layer = n_local(
        num_qubits=num_qubits,
        rotation_blocks=["ry", "rz"],
        entanglement_blocks="cx",
        reps=reps,
        entanglement=entanglement,
        insert_barriers=False,
        name="VariationalForm"
    )
    ansatz.compose(var_layer, inplace=True)
    return ansatz


def transpile_circuit_for_hardware(
    circuit: QuantumCircuit,
    backend: BackendV2,
    optimization_level: int = 1,
    seed_transpiler: int = 42
) -> QuantumCircuit:
    """Transpiles a quantum circuit for the target processor under official constraints.

    Args:
        circuit: Input quantum circuit (parameterized or bound).
        backend: Target GenericBackendV2 hardware backend.
        optimization_level: Transpiler optimization level (default: 1).
        seed_transpiler: Transpiler random seed for deterministic routing (default: 42).

    Returns:
        QuantumCircuit: Transpiled circuit routed to physical hardware coupling topology.
    """
    transpiled = transpile(
        circuit,
        backend=backend,
        optimization_level=optimization_level,
        seed_transpiler=seed_transpiler
    )
    return transpiled


def benchmark_routing_overheads(
    ansatz: QuantumCircuit,
    backend_a: BackendV2,
    backend_b: BackendV2,
    optimization_level: int = 1,
    seed_transpiler: int = 42
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Runs comparative transpilation and extracts routing metrics for Processors A and B.

    Args:
        ansatz: Original uncompiled VQE ansatz.
        backend_a: Processor A backend (5-qubit baseline).
        backend_b: Processor B backend (9-qubit heavy-hex).
        optimization_level: Transpilation optimization level (default: 1).
        seed_transpiler: Random seed (default: 42).

    Returns:
        metrics_a: Metrics dictionary for Processor A.
        metrics_b: Metrics dictionary for Processor B.
        delta: Comparative routing delta between B and A.
    """
    t_a = transpile_circuit_for_hardware(ansatz, backend_a, optimization_level, seed_transpiler)
    t_b = transpile_circuit_for_hardware(ansatz, backend_b, optimization_level, seed_transpiler)

    metrics_a = extract_circuit_metrics(t_a, ansatz, processor_name="Processor A (5Q Baseline)")
    metrics_b = extract_circuit_metrics(t_b, ansatz, processor_name="Processor B (9Q Heavy-Hex)")
    delta = compare_metrics(metrics_a, metrics_b)

    return metrics_a, metrics_b, delta


if __name__ == "__main__":
    from src.processors import get_processor_a, get_processor_b

    ansatz = build_h2_ansatz(num_qubits=4, reps=2, entanglement="full")
    proc_a = get_processor_a(seed=42)
    proc_b = get_processor_b(seed=42)

    mA, mB, delta = benchmark_routing_overheads(ansatz, proc_a, proc_b)

    print("=== Routing Benchmark (optimization_level=1, seed=42) ===")
    print(f"Original Circuit: Depth={ansatz.depth()}, CX={ansatz.count_ops().get('cx', 0)}, Total={sum(ansatz.count_ops().values())}")
    print(f"\nProcessor A (5Q): Depth={mA['transpiled_depth']}, CX={mA['cx_count']}, CX Overhead={mA['cx_overhead']} (equiv ~{mA['swap_equivalent']} SWAPs)")
    print(f"Processor B (9Q): Depth={mB['transpiled_depth']}, CX={mB['cx_count']}, CX Overhead={mB['cx_overhead']} (equiv ~{mB['swap_equivalent']} SWAPs)")
    print(f"\nComparative Delta (B - A): Depth Diff = {delta['depth_difference (B - A)']}, CX Diff = {delta['cx_difference (B - A)']}")
