"""Modular, Scalable, and Reusable Quantum Architecture Co-Design API.

Designed for the Qiskit Fall Hackathon 2026 (SRM AP).
Provides a clean, reusable object-oriented interface for benchmarking arbitrary
molecular Hamiltonians across diverse quantum hardware topologies with custom noise models.
"""

from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import networkx as nx
from qiskit import QuantumCircuit, transpile
from qiskit.providers.backend import BackendV2
from qiskit_aer.noise import NoiseModel

from src.problem import get_h2_problem, get_h2_canonical_jordan_wigner_hamiltonian, FCI_REFERENCE_ENERGY
from src.processors import (
    get_processor_a,
    get_processor_b,
    get_official_noise_model,
    PROCESSOR_A_EDGES,
    PROCESSOR_B_EDGES
)
from src.routing import build_h2_ansatz, transpile_circuit_for_hardware
from src.metrics import extract_circuit_metrics, compare_metrics
from src.co_design import (
    build_codesigned_ansatz_processor_a,
    build_codesigned_ansatz_processor_b,
    benchmark_codesign_impact
)
from src.mitigation import execute_with_zne
from src.vqe_runner import run_vqe
from src.symmetry import get_tapered_2qubit_h2_hamiltonian


class VQETopologyBenchmark:
    """Enterprise-grade, modular benchmark suite for VQE Hardware Co-Design.

    Allows researchers and hackathon evaluators to instantiate, transpile, simulate,
    and analyze molecular ground-state energy estimations across customizable hardware.

    Example:
        >>> bench = VQETopologyBenchmark(bond_distance=0.74)
        >>> bench.transpile(optimization_level=1, seed=42)
        >>> results = bench.run_vqe(shots=4096, maxiter=30)
        >>> print(bench.get_summary_table())
    """

    def __init__(
        self,
        bond_distance: float = 0.74,
        basis: str = "sto-3g",
        p1_error: float = 0.001,
        p2_error: float = 0.005,
        readout_error: float = 0.010,
        seed: int = 42
    ):
        self.bond_distance = bond_distance
        self.basis = basis
        self.seed = seed

        # 1. Molecular Formulation
        self.hamiltonian, self.fci_target, self.metadata = get_h2_problem(
            distance=bond_distance, basis=basis
        )

        # 2. Hardware Processors
        self.processor_a = get_processor_a(seed=seed)
        self.processor_b = get_processor_b(seed=seed)
        self.noise_model = get_official_noise_model(p1=p1_error, p2=p2_error, p_ro=readout_error)

        # 3. Circuit Containers
        self.ansatz = build_h2_ansatz(num_qubits=4, reps=2, entanglement="full")
        self.transpiled_circuits: Dict[str, QuantumCircuit] = {}
        self.metrics: Dict[str, Dict[str, Any]] = {}
        self.vqe_results: Dict[str, Dict[str, Any]] = {}

    def transpile(
        self,
        optimization_level: int = 1,
        ansatz_type: str = "full"
    ) -> Dict[str, Dict[str, Any]]:
        """Transpiles the ansatz onto both Processor A and Processor B under strict parameters.

        Args:
            optimization_level: Transpiler optimization level (default: 1).
            ansatz_type: 'full' (all-to-all), 'native' (hardware co-designed), or 'linear'.

        Returns:
            Dict[str, Dict[str, Any]]: Extracted structural circuit metrics for both backends.
        """
        if ansatz_type == "native":
            ansatz_a = build_codesigned_ansatz_processor_a(reps=2)
            ansatz_b = build_codesigned_ansatz_processor_b(reps=2)
        else:
            ansatz_a = build_h2_ansatz(num_qubits=4, reps=2, entanglement=ansatz_type)
            ansatz_b = ansatz_a

        t_a = transpile_circuit_for_hardware(
            ansatz_a, self.processor_a, optimization_level=optimization_level, seed_transpiler=self.seed
        )
        t_b = transpile_circuit_for_hardware(
            ansatz_b, self.processor_b, optimization_level=optimization_level, seed_transpiler=self.seed
        )

        self.transpiled_circuits["Processor A"] = t_a
        self.transpiled_circuits["Processor B"] = t_b

        self.metrics["Processor A"] = extract_circuit_metrics(t_a, ansatz_a, "Processor A")
        self.metrics["Processor B"] = extract_circuit_metrics(t_b, ansatz_b, "Processor B")
        return self.metrics

    def run_vqe(
        self,
        shots: int = 4096,
        maxiter: int = 35,
        apply_zne: bool = False
    ) -> Dict[str, Any]:
        """Executes the closed-loop VQE optimization on both physical noisy simulators.

        Args:
            shots: Measurement shot budget (default: 4096).
            maxiter: Maximum COBYLA iterations (default: 35).
            apply_zne: Whether to run Zero-Noise Extrapolation post-optimization.

        Returns:
            Dict[str, Any]: Ground-state estimates and convergence trajectories.
        """
        if not self.transpiled_circuits:
            self.transpile()

        res_a = run_vqe(
            ansatz=self.ansatz,
            backend=self.processor_a,
            hamiltonian=self.hamiltonian,
            noise_model=self.noise_model,
            shots=shots,
            seed=self.seed,
            maxiter=maxiter,
            processor_name="Processor A (5Q Baseline)"
        )

        res_b = run_vqe(
            ansatz=self.ansatz,
            backend=self.processor_b,
            hamiltonian=self.hamiltonian,
            noise_model=self.noise_model,
            shots=shots,
            seed=self.seed,
            maxiter=maxiter,
            processor_name="Processor B (9Q Heavy-Hex)"
        )

        self.vqe_results["Processor A"] = res_a
        self.vqe_results["Processor B"] = res_b

        zne_data = None
        if apply_zne:
            t_a = res_a["transpiled_circuit"]
            phys_H = self.hamiltonian.apply_layout(t_a.layout)
            zne_data = execute_with_zne(
                circuit=t_a,
                observable=phys_H,
                parameters=np.array(res_a["optimal_parameters"]),
                noise_model=self.noise_model,
                scale_factors=[1, 3, 5],
                shots=shots,
                seed=self.seed
            )
            self.vqe_results["ZNE_Processor_A"] = zne_data

        return {
            "processor_a": res_a,
            "processor_b": res_b,
            "zne": zne_data,
            "fci_target": self.fci_target,
        }

    def get_summary_dataframe(self):
        """Generates a clean pandas DataFrame of all comparative metrics."""
        import pandas as pd
        mA = self.metrics.get("Processor A", {})
        mB = self.metrics.get("Processor B", {})
        resA = self.vqe_results.get("Processor A", {})
        resB = self.vqe_results.get("Processor B", {})

        rows = [
            {
                "Architecture": "Processor A (5Q Baseline)",
                "Qubits": 5,
                "Coupling Edges": len(PROCESSOR_A_EDGES),
                "Depth": mA.get("transpiled_depth", "-"),
                "Total Gates": mA.get("total_gates", "-"),
                "CX Gates": mA.get("cx_count", "-"),
                "SWAP Overhead": mA.get("cx_overhead", "-"),
                "Final Energy (Ha)": f"{resA.get('final_energy', 0.0):.6f}" if resA else "-",
                "FCI Target (Ha)": f"{self.fci_target:.6f}",
                "Delta (Ha)": f"{resA.get('energy_error_hartree', 0.0):+.6f}" if resA else "-",
            },
            {
                "Architecture": "Processor B (9Q Heavy-Hex)",
                "Qubits": 9,
                "Coupling Edges": len(PROCESSOR_B_EDGES),
                "Depth": mB.get("transpiled_depth", "-"),
                "Total Gates": mB.get("total_gates", "-"),
                "CX Gates": mB.get("cx_count", "-"),
                "SWAP Overhead": mB.get("cx_overhead", "-"),
                "Final Energy (Ha)": f"{resB.get('final_energy', 0.0):.6f}" if resB else "-",
                "FCI Target (Ha)": f"{self.fci_target:.6f}",
                "Delta (Ha)": f"{resB.get('energy_error_hartree', 0.0):+.6f}" if resB else "-",
            }
        ]
        return pd.DataFrame(rows)
