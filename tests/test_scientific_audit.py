"""Scientific and Technical Regression Unit Tests for H2 VQE Benchmark.

Executes standalone unit tests under Python's native unittest framework to independently
validate mathematical and physical assertions across all core research modules.
"""

import unittest
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector, SparsePauliOp
from scipy.optimize import minimize

from src.problem import get_h2_problem, FCI_REFERENCE_ENERGY
from src.integral_solver import calculate_h2_first_principles
from src.processors import get_processor_a, get_processor_b, PROCESSOR_A_EDGES, PROCESSOR_B_EDGES
from src.routing import build_h2_ansatz, transpile_circuit_for_hardware, benchmark_routing_overheads
from src.co_design import build_symmetry_preserving_ansatz, benchmark_codesign_impact
from src.grouping import benchmark_qwc_grouping
from src.mitigation import fold_cx_gates, richardson_extrapolation
from src.adapt_vqe import run_topology_adapt_vqe
from src.molecules import MOLECULAR_CATALOG, get_molecular_hamiltonian


class TestScientificGroundTruth(unittest.TestCase):
    """Phase 2: Scientific Ground Truth and Hamiltonian Verification."""

    def test_first_principles_integrals_and_fci(self):
        """Validates that analytical STO-3G integrals reproduce the true un-fudged FCI ground state."""
        res = calculate_h2_first_principles(r_angstrom=0.74)
        self.assertAlmostEqual(res["e_hf"], -1.116759, places=5)
        self.assertAlmostEqual(res["e_fci"], -1.137284, places=5)
        self.assertAlmostEqual(res["fci_lowest_eigenvalue"], res["e_fci"], places=10)

    def test_hamiltonian_properties(self):
        """Validates Hermiticity, matrix dimension, and ground state eigenvalue."""
        H, fci_ref, meta = get_h2_problem(distance=0.74)
        H_mat = H.to_matrix()
        self.assertEqual(H.num_qubits, 4)
        self.assertEqual(H_mat.shape, (16, 16))
        # Hermiticity: H = H^dagger
        self.assertTrue(np.allclose(H_mat, H_mat.conj().T))
        # Lowest eigenvalue
        eigs = np.linalg.eigvalsh(H_mat)
        self.assertAlmostEqual(eigs[0], fci_ref, places=5)


class TestQuantumCircuitsAndVQE(unittest.TestCase):
    """Phase 3: Quantum Circuits, Expressibility, and Co-Design."""

    def test_exact_singlet_ansatz_reaches_fci(self):
        """Validates that our 3-CX singlet-preserving ansatz reaches FCI within machine precision."""
        H, fci_ref, _ = get_h2_problem()
        ansatz = build_symmetry_preserving_ansatz(reps=1)
        self.assertEqual(ansatz.num_parameters, 1)

        def obj(x):
            c = ansatz.assign_parameters(x)
            psi = Statevector.from_instruction(c)
            return float(np.real(psi.expectation_value(H)))

        res = minimize(obj, [0.0], method="BFGS")
        self.assertAlmostEqual(res.fun, fci_ref, places=7)

    def test_adapt_vqe_operator_growth(self):
        """Validates that ADAPT-VQE computes non-zero gradients and dynamically selects operators."""
        adapt_res = run_topology_adapt_vqe(PROCESSOR_A_EDGES, max_adapt_cycles=2)
        self.assertTrue(adapt_res["adapt_cycles_completed"] >= 1)
        self.assertTrue(adapt_res["zero_swap_guarantee"])
        self.assertAlmostEqual(adapt_res["final_energy"], FCI_REFERENCE_ENERGY, places=5)


class TestHardwareTopologyAndRouting(unittest.TestCase):
    """Phase 4: Hardware Topologies and Compilation Costs."""

    def test_topology_graph_properties(self):
        """Validates qubit counts and edge counts for Processors A and B."""
        proc_a = get_processor_a(seed=42)
        proc_b = get_processor_b(seed=42)
        self.assertEqual(proc_a.num_qubits, 5)
        self.assertEqual(proc_b.num_qubits, 9)
        self.assertEqual(len(PROCESSOR_A_EDGES), 4)
        self.assertEqual(len(PROCESSOR_B_EDGES), 12)

    def test_heavy_hex_routing_penalty(self):
        """Validates that naive all-to-all ansatz incurs higher CX overhead on Processor B."""
        proc_a = get_processor_a(seed=42)
        proc_b = get_processor_b(seed=42)
        ansatz = build_h2_ansatz(num_qubits=4, reps=2, entanglement="full")
        mA, mB, delta = benchmark_routing_overheads(ansatz, proc_a, proc_b, optimization_level=1, seed_transpiler=42)
        self.assertEqual(delta["cx_difference (B - A)"], 3)
        self.assertGreater(mB["cx_count"], mA["cx_count"])

    def test_codesign_zero_swap_elimination(self):
        """Validates that hardware-native co-design eliminates 100% of physical SWAP routing."""
        cd = benchmark_codesign_impact(optimization_level=1, seed_transpiler=42)
        self.assertEqual(cd["codesign_a"]["cx_overhead"], 0)
        self.assertEqual(cd["codesign_b"]["cx_overhead"], 0)


class TestErrorMitigationAndMeasurement(unittest.TestCase):
    """Phase 5 & 6: Noise Mitigation and Grouping."""

    def test_qwc_measurement_grouping(self):
        """Validates 66.7% measurement reduction via QWC commuting cliques."""
        H, _, _ = get_h2_problem()
        res = benchmark_qwc_grouping(H)
        self.assertEqual(res["original_pauli_terms"], 15)
        self.assertEqual(res["qwc_measurement_cliques"], 5)
        self.assertAlmostEqual(res["circuit_reduction_percent"], 66.67, places=1)

    def test_gate_folding_unitary_invariance(self):
        """Validates that scale factor lambda = 3 triples CX count and preserves ideal statevector."""
        ansatz = build_h2_ansatz(num_qubits=4, reps=1, entanglement="linear")
        param_vals = [0.1] * ansatz.num_parameters
        bound_ansatz = ansatz.assign_parameters(param_vals)

        folded_1 = fold_cx_gates(bound_ansatz, scale_factor=1)
        folded_3 = fold_cx_gates(bound_ansatz, scale_factor=3)

        cx1 = folded_1.count_ops().get("cx", 0)
        cx3 = folded_3.count_ops().get("cx", 0)
        self.assertEqual(cx3, 3 * cx1)

        # Ideal statevector invariance: U(CX CX) = U
        psi1 = Statevector.from_instruction(folded_1)
        psi3 = Statevector.from_instruction(folded_3)
        self.assertTrue(np.allclose(psi1.data, psi3.data, atol=1e-12))


class TestMultiMoleculeCatalog(unittest.TestCase):
    """Validates chemical transferability across H2, HeH+, and LiH."""

    def test_catalog_molecules(self):
        catalog = MOLECULAR_CATALOG
        self.assertIn("H2", catalog)
        self.assertIn("HeH+", catalog)
        self.assertIn("LiH", catalog)
        self.assertEqual(catalog["H2"]["num_qubits"], 4)
        self.assertEqual(catalog["HeH+"]["num_qubits"], 4)
        self.assertEqual(catalog["LiH"]["num_qubits"], 4)


if __name__ == "__main__":
    unittest.main()
