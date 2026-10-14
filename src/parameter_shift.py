"""Analytical Parameter-Shift Rule Quantum Gradient Module.

Implements exact analytical quantum differentiation for parameterized rotation circuits:
    d<H>/d(theta_j) = [ <H(theta + pi/2 * e_j)> - <H(theta - pi/2 * e_j)> ] / 2

Enables exact Quantum Gradient Descent (QGD) and Quantum Adam optimization on physical
noisy quantum backends without finite-difference numerical errors.
"""

from typing import List, Dict, Any, Tuple, Callable
import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer.primitives import Estimator as AerEstimator
from qiskit_aer.noise import NoiseModel

from src.problem import FCI_REFERENCE_ENERGY


def compute_parameter_shift_gradient(
    circuit: QuantumCircuit,
    observable,
    parameters: np.ndarray,
    noise_model: NoiseModel = None,
    shots: int = 4096,
    seed: int = 42
) -> Tuple[np.ndarray, float]:
    """Computes the exact analytical gradient vector using the Parameter-Shift Rule.

    Args:
        circuit: Transpiled parameterized QuantumCircuit.
        observable: Physical Hamiltonian mapped to circuit layout.
        parameters: Current parameter vector theta.
        noise_model: Hardware noise model.
        shots: Measurement shot budget (default: 4096).
        seed: Random seed.

    Returns:
        Tuple[np.ndarray, float]: Analytical gradient vector (d<H>/d theta) and current energy.
    """
    estimator = AerEstimator(
        backend_options={"noise_model": noise_model} if noise_model is not None else {},
        run_options={"shots": shots, "seed": seed},
        approximation=False
    )

    dim = len(parameters)
    gradient = np.zeros(dim)
    shift = np.pi / 2.0

    # Current energy evaluation
    cur_job = estimator.run([circuit], [observable], [parameters])
    current_energy = float(cur_job.result().values[0])

    # Parameter-shift evaluations for each parameter component
    for j in range(dim):
        p_plus = parameters.copy()
        p_minus = parameters.copy()
        p_plus[j] += shift
        p_minus[j] -= shift

        job_plus = estimator.run([circuit], [observable], [p_plus])
        job_minus = estimator.run([circuit], [observable], [p_minus])

        e_plus = float(job_plus.result().values[0])
        e_minus = float(job_minus.result().values[0])

        gradient[j] = (e_plus - e_minus) / 2.0

    return gradient, current_energy


def run_quantum_gradient_descent(
    circuit: QuantumCircuit,
    observable,
    initial_params: np.ndarray,
    noise_model: NoiseModel = None,
    learning_rate: float = 0.15,
    max_steps: int = 20,
    shots: int = 4096,
    seed: int = 42
) -> Dict[str, Any]:
    """Executes closed-loop Quantum Gradient Descent using parameter-shift gradients."""
    params = initial_params.copy()
    energy_history: List[float] = []
    grad_norm_history: List[float] = []

    for step in range(max_steps):
        grad, energy = compute_parameter_shift_gradient(
            circuit=circuit,
            observable=observable,
            parameters=params,
            noise_model=noise_model,
            shots=shots,
            seed=seed + step
        )
        energy_history.append(energy)
        grad_norm = float(np.linalg.norm(grad))
        grad_norm_history.append(grad_norm)

        # Gradient update step
        params -= learning_rate * grad

    # Final energy evaluation
    final_grad, final_energy = compute_parameter_shift_gradient(
        circuit=circuit, observable=observable, parameters=params,
        noise_model=noise_model, shots=shots, seed=seed + max_steps
    )
    energy_history.append(final_energy)

    return {
        "final_energy": final_energy,
        "energy_history": energy_history,
        "gradient_norm_history": grad_norm_history,
        "optimal_parameters": params.tolist(),
        "total_steps": max_steps,
    }
