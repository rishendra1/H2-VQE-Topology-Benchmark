"""Optimizer Comparison Module: COBYLA vs SPSA under Noisy Quantum Simulation.

Compares:
1. COBYLA: Standard simplex/linear-approximation derivative-free optimizer.
2. SPSA: Simultaneous Perturbation Stochastic Approximation, resilient to statistical shot noise and gate errors.
"""

from typing import Dict, Any, List, Tuple
import os
import time
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from qiskit import QuantumCircuit
from qiskit.providers.backend import BackendV2
from qiskit_aer.primitives import Estimator as AerEstimator
from qiskit_aer.noise import NoiseModel

from src.problem import FCI_REFERENCE_ENERGY, get_h2_problem
from src.processors import get_processor_a, get_official_noise_model
from src.routing import build_h2_ansatz, transpile_circuit_for_hardware


def run_spsa(
    objective_fn,
    initial_params: np.ndarray,
    maxiter: int = 40,
    a: float = 0.2,
    c: float = 0.1,
    alpha: float = 0.602,
    gamma: float = 0.101,
    seed: int = 42
) -> Tuple[np.ndarray, float, List[float]]:
    """Executes 2-measurement SPSA optimization."""
    rng = np.random.RandomState(seed)
    params = initial_params.copy()
    dim = len(params)
    history: List[float] = []

    for k in range(1, maxiter + 1):
        ak = a / (k ** alpha)
        ck = c / (k ** gamma)

        # Bernoulli random perturbation vector delta in {-1, +1}^d
        delta = rng.choice([-1.0, 1.0], size=dim)

        p_plus = params + ck * delta
        p_minus = params - ck * delta

        y_plus = objective_fn(p_plus)
        y_minus = objective_fn(p_minus)

        # Simultaneous stochastic gradient estimation
        ghat = (y_plus - y_minus) / (2.0 * ck * delta)
        params = params - ak * ghat

        cur_energy = objective_fn(params)
        history.append(cur_energy)

    return params, history[-1], history


def compare_cobyla_vs_spsa(
    ansatz: QuantumCircuit = None,
    backend: BackendV2 = None,
    noise_model: NoiseModel = None,
    maxiter: int = 35,
    shots: int = 4096,
    seed: int = 42
) -> Dict[str, Any]:
    """Runs a side-by-side optimization benchmark between COBYLA and SPSA."""
    if ansatz is None:
        ansatz = build_h2_ansatz(num_qubits=4, reps=1, entanglement="linear")
    if backend is None:
        backend = get_processor_a(seed=seed)
    if noise_model is None:
        noise_model = get_official_noise_model()

    hamiltonian, fci_ref, _ = get_h2_problem()
    t_circuit = transpile_circuit_for_hardware(ansatz, backend, optimization_level=1, seed_transpiler=seed)
    phys_H = hamiltonian.apply_layout(t_circuit.layout)

    estimator = AerEstimator(
        backend_options={"noise_model": noise_model},
        run_options={"shots": shots, "seed": seed},
        approximation=False
    )

    # 1. COBYLA
    cobyla_history: List[float] = []
    def cobyla_obj(p):
        job = estimator.run(circuits=[t_circuit], observables=[phys_H], parameter_values=[p])
        val = float(job.result().values[0])
        cobyla_history.append(val)
        return val

    rng = np.random.RandomState(seed)
    init_p = rng.normal(0.0, 0.08, len(t_circuit.parameters))

    t0 = time.time()
    res_cobyla = minimize(cobyla_obj, init_p, method="COBYLA", options={"maxiter": maxiter, "rhobeg": 0.25})
    t_cobyla = time.time() - t0

    # 2. SPSA
    spsa_eval_history: List[float] = []
    def spsa_obj(p):
        job = estimator.run(circuits=[t_circuit], observables=[phys_H], parameter_values=[p])
        val = float(job.result().values[0])
        spsa_eval_history.append(val)
        return val

    t0 = time.time()
    opt_p_spsa, final_e_spsa, spsa_step_history = run_spsa(spsa_obj, init_p, maxiter=maxiter, seed=seed)
    t_spsa = time.time() - t0

    return {
        "cobyla_final_energy": float(res_cobyla.fun),
        "spsa_final_energy": float(final_e_spsa),
        "fci_target": fci_ref,
        "cobyla_history": cobyla_history,
        "spsa_history": spsa_step_history,
        "cobyla_time": t_cobyla,
        "spsa_time": t_spsa,
    }


def plot_optimizer_comparison(opt_data: Dict[str, Any], save_path: str = None) -> str:
    """Plots and saves convergence comparison between COBYLA and SPSA."""
    if save_path is None:
        save_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results", "figures", "optimizer_comparison.png"))

    c_hist = opt_data["cobyla_history"]
    s_hist = opt_data["spsa_history"]
    fci = opt_data["fci_target"]

    plt.figure(figsize=(9, 5.5), dpi=300)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    plt.plot(range(1, len(c_hist) + 1), c_hist, label=f"COBYLA (Final: {c_hist[-1]:.4f} Ha)", color="#1f77b4", lw=2, marker="o", markersize=3)
    plt.plot(range(1, len(s_hist) + 1), s_hist, label=f"SPSA (Final: {s_hist[-1]:.4f} Ha)", color="#ff7f0e", lw=2, marker="s", markersize=3)
    plt.axhline(y=fci, color="black", linestyle=":", lw=2, label=f"Classical FCI Target ({fci:.4f} Ha)")

    plt.title("Noisy VQE Convergence: COBYLA vs SPSA (4096 Shots)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Optimizer Iteration / Step", fontsize=11)
    plt.ylabel("Energy (Hartree)", fontsize=11)
    plt.legend(frameon=True, fontsize=10)
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    return save_path
