"""VQE Execution and Optimization Engine.

Orchestrates:
- Transpiled circuit execution with physical layout mapping.
- Noisy simulation via AerEstimator with official synthetic noise (shots=4096, seed=42).
- Classical optimization loop (COBYLA) tracking convergence trajectories.
- Comparative evaluation across Processor A, Processor B, and Ideal baseline.
"""

from typing import List, Dict, Any, Callable, Optional, Tuple
import sys
import os
import time
import numpy as np
from scipy.optimize import minimize
from qiskit import QuantumCircuit, transpile
from qiskit.providers.backend import BackendV2
from qiskit_aer.primitives import Estimator as AerEstimator
from qiskit_aer.noise import NoiseModel

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.problem import FCI_REFERENCE_ENERGY, get_h2_problem
from src.processors import (
    get_processor_a,
    get_processor_b,
    get_official_noise_model
)
from src.routing import build_h2_ansatz, transpile_circuit_for_hardware
from src.metrics import extract_circuit_metrics, compare_metrics


def run_vqe(
    ansatz: QuantumCircuit,
    backend: BackendV2,
    hamiltonian,
    noise_model: Optional[NoiseModel] = None,
    shots: int = 4096,
    seed: int = 42,
    maxiter: int = 45,
    initial_params: Optional[np.ndarray] = None,
    processor_name: str = "Hardware",
    optimization_level: int = 1
) -> Dict[str, Any]:
    """Executes the complete VQE optimization loop for a target processor backend.

    Args:
        ansatz: Original parameterized VQE ansatz circuit.
        backend: Target physical processor backend (e.g. GenericBackendV2).
        hamiltonian: Logical SparsePauliOp Hamiltonian for H2.
        noise_model: NoiseModel to apply. If None, runs noiseless ideal simulation.
        shots: Measurement shot budget (default: 4096).
        seed: Random seed for transpiler, noise, and sampling reproducibility (default: 42).
        maxiter: Maximum classical optimizer iterations (default: 45).
        initial_params: Initial parameter vector. If None, initializes near Hartree-Fock point.
        processor_name: Human-readable name for logging.
        optimization_level: Transpiler optimization level (default: 1).

    Returns:
        Dict[str, Any]: Complete results bundle including convergence history,
                        final energy, optimal parameters, circuit metrics, and runtime.
    """
    start_time = time.time()

    # 1. Transpile ansatz for physical hardware topology
    transpiled_circuit = transpile_circuit_for_hardware(
        ansatz,
        backend=backend,
        optimization_level=optimization_level,
        seed_transpiler=seed
    )

    # 2. Map logical Hamiltonian to physical qubit layout
    physical_hamiltonian = hamiltonian.apply_layout(transpiled_circuit.layout)

    # 3. Configure AerEstimator primitive
    backend_options = {"noise_model": noise_model} if noise_model is not None else {}
    estimator = AerEstimator(
        backend_options=backend_options,
        run_options={"shots": shots, "seed": seed},
        approximation=False
    )

    # 4. Convergence tracking
    energy_history: List[float] = []
    eval_count: int = 0

    def objective_function(parameters: np.ndarray) -> float:
        nonlocal eval_count
        eval_count += 1
        job = estimator.run(
            circuits=[transpiled_circuit],
            observables=[physical_hamiltonian],
            parameter_values=[parameters]
        )
        val = float(job.result().values[0])
        energy_history.append(val)
        return val

    # 5. Parameter initialization
    num_params = len(transpiled_circuit.parameters)
    if initial_params is None:
        # Subtle non-zero perturbation to break symmetry while staying near Hartree-Fock
        rng = np.random.RandomState(seed)
        initial_params = rng.normal(0.0, 0.08, num_params)
    elif len(initial_params) != num_params:
        rng = np.random.RandomState(seed)
        initial_params = rng.normal(0.0, 0.08, num_params)

    # 6. Execute Classical Optimizer (COBYLA)
    opt_result = minimize(
        objective_function,
        initial_params,
        method="COBYLA",
        options={"maxiter": maxiter, "rhobeg": 0.25}
    )

    elapsed_time = time.time() - start_time

    # 7. Extract circuit structural metrics
    circuit_metrics = extract_circuit_metrics(
        transpiled_circuit=transpiled_circuit,
        original_circuit=ansatz,
        processor_name=processor_name
    )

    final_energy = float(opt_result.fun)
    fci_error = final_energy - FCI_REFERENCE_ENERGY

    return {
        "processor_name": processor_name,
        "final_energy": final_energy,
        "fci_target": FCI_REFERENCE_ENERGY,
        "energy_error_hartree": fci_error,
        "energy_error_kcal_mol": fci_error * 627.509,  # 1 Hartree = 627.509 kcal/mol
        "converged": opt_result.success,
        "total_evaluations": eval_count,
        "optimal_parameters": opt_result.x.tolist(),
        "energy_history": energy_history,
        "transpiled_circuit": transpiled_circuit,
        "circuit_metrics": circuit_metrics,
        "elapsed_time_sec": elapsed_time,
        "shots": shots,
        "noisy": noise_model is not None,
    }


def run_full_benchmark_suite(
    maxiter: int = 40,
    shots: int = 4096,
    seed: int = 42,
    entanglement: str = "full",
    reps: int = 2
) -> Dict[str, Any]:
    """Runs the complete comparative benchmark across Processor A, Processor B, and Ideal baseline.

    Args:
        maxiter: Iterations per VQE run (default: 40).
        shots: Number of shots (default: 4096).
        seed: Random seed (default: 42).
        entanglement: Entanglement topology for ansatz ('full' or 'linear').
        reps: Ansatz repetitions (default: 2).

    Returns:
        Dict[str, Any]: Full benchmarking report with all metrics, histories, and comparisons.
    """
    hamiltonian, fci_ref, prob_meta = get_h2_problem()
    ansatz = build_h2_ansatz(num_qubits=4, reps=reps, entanglement=entanglement)

    proc_a = get_processor_a(seed=seed)
    proc_b = get_processor_b(seed=seed)
    noise_model = get_official_noise_model()

    print(">>> Starting Processor A (5-Qubit Baseline) VQE run...")
    res_a = run_vqe(
        ansatz=ansatz,
        backend=proc_a,
        hamiltonian=hamiltonian,
        noise_model=noise_model,
        shots=shots,
        seed=seed,
        maxiter=maxiter,
        processor_name="Processor A (5Q Baseline)"
    )
    print(f"    Processor A Final Energy: {res_a['final_energy']:.6f} Ha (Error: {res_a['energy_error_hartree']:.6f} Ha)")

    print(">>> Starting Processor B (9-Qubit Heavy-Hex) VQE run...")
    res_b = run_vqe(
        ansatz=ansatz,
        backend=proc_b,
        hamiltonian=hamiltonian,
        noise_model=noise_model,
        shots=shots,
        seed=seed,
        maxiter=maxiter,
        processor_name="Processor B (9Q Heavy-Hex)"
    )
    print(f"    Processor B Final Energy: {res_b['final_energy']:.6f} Ha (Error: {res_b['energy_error_hartree']:.6f} Ha)")

    print(">>> Starting Ideal (Noiseless) Baseline VQE run...")
    res_ideal = run_vqe(
        ansatz=ansatz,
        backend=proc_a,
        hamiltonian=hamiltonian,
        noise_model=None,
        shots=shots,
        seed=seed,
        maxiter=maxiter,
        processor_name="Ideal Noiseless Baseline"
    )
    print(f"    Ideal Baseline Final Energy: {res_ideal['final_energy']:.6f} Ha (Error: {res_ideal['energy_error_hartree']:.6f} Ha)")

    comparison_delta = compare_metrics(res_a["circuit_metrics"], res_b["circuit_metrics"])

    return {
        "problem_metadata": prob_meta,
        "processor_a": res_a,
        "processor_b": res_b,
        "ideal": res_ideal,
        "comparison_delta": comparison_delta,
        "fci_target": fci_ref,
    }


if __name__ == "__main__":
    results = run_full_benchmark_suite(maxiter=25, shots=4096, seed=42)
    print("\n=== Benchmark Completed Successfully ===")
