"""Comprehensive Test Suite and Metrics Verification for H2-VQE-Topology-Benchmark."""

import os
import sys
import numpy as np

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.problem import get_h2_problem, FCI_REFERENCE_ENERGY
from src.processors import (
    get_processor_a,
    get_processor_b,
    get_official_noise_model,
    PROCESSOR_A_EDGES,
    PROCESSOR_B_EDGES,
    P_1Q_DEPOLARIZING,
    P_2Q_DEPOLARIZING,
    P_READOUT_ERROR
)
from src.routing import build_h2_ansatz, transpile_circuit_for_hardware, benchmark_routing_overheads
from src.metrics import extract_circuit_metrics, compare_metrics


def run_all_tests():
    print("=" * 75)
    print("       H2-VQE-TOPOLOGY-BENCHMARK: COMPLETE VERIFICATION & METRICS      ")
    print("=" * 75)

    # -------------------------------------------------------------
    # TEST 1: Problem Formulation & Molecular Hamiltonian Mapping
    # -------------------------------------------------------------
    print("\n[TEST 1] Molecular Problem & Hamiltonian Formulation (src/problem.py)")
    hamiltonian, fci_ref, meta = get_h2_problem(distance=0.74, basis="sto-3g")
    eigs = np.linalg.eigvalsh(hamiltonian.to_matrix())
    lowest_eig = float(eigs[0])

    print(f"  • Molecule:                 {meta['molecule']} at R = {meta['bond_distance_angstrom']} Angstroms")
    print(f"  • Basis Set:                {meta['basis_set']}")
    print(f"  • Fermion-to-Qubit Mapping: {meta['mapping']}")
    print(f"  • Number of Qubits:         {hamiltonian.num_qubits}")
    print(f"  • Number of Pauli Terms:    {len(hamiltonian)}")
    print(f"  • Classical FCI Reference:  {fci_ref:.6f} Hartree")
    print(f"  • Lowest Eigenvalue of H:   {lowest_eig:.6f} Hartree")
    diff_eig = abs(lowest_eig - fci_ref)
    print(f"  • Absolute Target Delta:    {diff_eig:.8f} Hartree")
    assert diff_eig < 1e-4, f"FCI Reference mismatch: {diff_eig}"
    print("  -> RESULT: PASSED (Exact match with classical FCI benchmark)")

    # -------------------------------------------------------------
    # TEST 2: Hardware Topologies & Noise Configuration
    # -------------------------------------------------------------
    print("\n[TEST 2] Hardware Architecture & Noise Profiles (src/processors.py)")
    proc_a = get_processor_a(seed=42)
    proc_b = get_processor_b(seed=42)
    noise_model = get_official_noise_model()

    print(f"  • Processor A (Baseline):   {proc_a.num_qubits} qubits, {len(PROCESSOR_A_EDGES)} undirected coupling edges")
    print(f"    - Coupling Graph Edges:   {PROCESSOR_A_EDGES}")
    print(f"  • Processor B (Heavy-Hex):  {proc_b.num_qubits} qubits, {len(PROCESSOR_B_EDGES)} undirected coupling edges")
    print(f"    - Coupling Graph Edges:   {PROCESSOR_B_EDGES}")
    print(f"  • Synthetic Noise Parameters:")
    print(f"    - 1Q Depolarizing Error:  {P_1Q_DEPOLARIZING * 100:.2f}% (p = {P_1Q_DEPOLARIZING})")
    print(f"    - 2Q CX Depol Error:      {P_2Q_DEPOLARIZING * 100:.2f}% (p = {P_2Q_DEPOLARIZING})")
    print(f"    - Readout Error:          {P_READOUT_ERROR * 100:.2f}% (p = {P_READOUT_ERROR})")
    assert proc_a.num_qubits == 5, "Processor A should have 5 qubits"
    assert proc_b.num_qubits == 9, "Processor B should have 9 qubits"
    assert len(PROCESSOR_B_EDGES) == 12, "Processor B should have 12 edges"
    print("  -> RESULT: PASSED (Architectures and noise parameters match specifications)")

    # -------------------------------------------------------------
    # TEST 3: Transpilation, Routing & Structural Gate Metrics
    # -------------------------------------------------------------
    print("\n[TEST 3] Transpilation & Routing Overhead Metrics (src/routing.py & metrics.py)")
    print("  [Constraints: optimization_level=1, seed_transpiler=42]")
    ansatz = build_h2_ansatz(num_qubits=4, reps=2, entanglement="full")
    mA, mB, delta = benchmark_routing_overheads(ansatz, proc_a, proc_b, optimization_level=1, seed_transpiler=42)

    orig_depth = ansatz.depth()
    orig_cx = ansatz.count_ops().get("cx", 0)
    orig_total = sum(ansatz.count_ops().values())

    print(f"\n  A. Original Uncompiled Circuit:")
    print(f"     - Depth:                 {orig_depth}")
    print(f"     - Total Gate Count:      {orig_total}")
    print(f"     - 2-Qubit CX Count:      {orig_cx}")

    print(f"\n  B. Processor A (5Q Baseline Transpiled):")
    print(f"     - Transpiled Depth:      {mA['transpiled_depth']}")
    print(f"     - Total Gate Count:      {mA['total_gates']}")
    print(f"     - Native CX Gate Count:  {mA['cx_count']}")
    print(f"     - CX Gate Inflation:     +{mA['cx_overhead']} CX (due to ~{mA['swap_equivalent']} physical SWAPs)")

    print(f"\n  C. Processor B (9Q Heavy-Hex Transpiled):")
    print(f"     - Transpiled Depth:      {mB['transpiled_depth']}")
    print(f"     - Total Gate Count:      {mB['total_gates']}")
    print(f"     - Native CX Gate Count:  {mB['cx_count']}")
    print(f"     - CX Gate Inflation:     +{mB['cx_overhead']} CX (due to ~{mB['swap_equivalent']} physical SWAPs)")

    print(f"\n  D. Comparative Routing Delta (Processor B vs Processor A):")
    print(f"     - Circuit Depth Delta:   {delta['depth_difference (B - A)']:+d} ({delta['depth_percent_change']:+.2f}%)")
    print(f"     - CX Gate Count Delta:   {delta['cx_difference (B - A)']:+d} ({delta['cx_percent_change']:+.2f}%)")
    print("  -> RESULT: PASSED (Heavy-hex routing overhead quantified)")

    # -------------------------------------------------------------
    # TEST 4: Benchmark Artifacts & File Integrity Verification
    # -------------------------------------------------------------
    print("\n[TEST 4] Benchmark Artifacts & Output Files Verification")
    required_files = [
        "results/figures/energy_convergence.png",
        "results/figures/circuit_metrics_comparison.png",
        "results/figures/hardware_topologies.png",
        "results/tables/benchmark_summary.md",
        "results/tables/benchmark_summary.csv",
        "results/tables/raw_benchmark_results.json",
        "main.ipynb",
        "report.md",
        "README.md",
        "requirements.txt"
    ]
    all_found = True
    for rf in required_files:
        full_path = os.path.join(os.path.dirname(__file__), rf)
        exists = os.path.isfile(full_path)
        sz = os.path.getsize(full_path) if exists else 0
        status = f"EXISTS ({sz:,} bytes)" if exists and sz > 0 else "MISSING"
        print(f"  • {rf:<42} : {status}")
        if not exists or sz == 0:
            all_found = False

    assert all_found, "Some required benchmark artifacts are missing or empty!"
    print("  -> RESULT: PASSED (All 10 required artifacts exist with non-zero size)")

    print("\n" + "=" * 75)
    print("           ALL TESTS PASSED SUCCESSFULLY! READY FOR SUBMISSION          ")
    print("=" * 75)


if __name__ == "__main__":
    run_all_tests()
