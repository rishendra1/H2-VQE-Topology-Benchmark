"""Quantum State Tomography, Fidelity, and Entanglement Entropy Module.

Computes:
1. Pure State Fidelity F = |<psi_FCI | psi_VQE>|^2 relative to exact FCI wavefunction.
2. Reduced Density Matrix rho_A across spatial orbital molecular bipartitions.
3. von Neumann Entanglement Entropy S(rho_A) = -Tr(rho_A log2 rho_A).
4. Quantum State Purity gamma = Tr(rho^2).
"""

from typing import Dict, Any, Tuple
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, partial_trace, entropy

from src.problem import get_h2_problem


def get_exact_fci_wavefunction() -> Statevector:
    """Computes the exact classical Full Configuration Interaction (FCI) ground-state eigenvector."""
    H, _, _ = get_h2_problem()
    vals, vecs = np.linalg.eigh(H.to_matrix())
    fci_ground_vector = vecs[:, 0]
    return Statevector(fci_ground_vector)


def evaluate_state_fidelity_and_entropy(
    ansatz: QuantumCircuit,
    parameters: np.ndarray,
    fci_state: Statevector = None
) -> Dict[str, Any]:
    """Evaluates the quantum state fidelity, reduced density matrix, and entanglement entropy.

    Args:
        ansatz: Original parameterized VQE ansatz circuit.
        parameters: Optimal variational parameters.
        fci_state: Exact FCI statevector. If None, computed automatically.

    Returns:
        Dict[str, Any]: State fidelity, von Neumann entropy, purity, and state probabilities.
    """
    if fci_state is None:
        fci_state = get_exact_fci_wavefunction()

    bound_circuit = ansatz.assign_parameters(parameters)
    vqe_state = Statevector.from_instruction(bound_circuit)

    # 1. State Fidelity F = |<psi_FCI | psi_VQE>|^2
    fidelity = float(abs(np.vdot(fci_state.data, vqe_state.data)) ** 2)

    # 2. Reduced Density Matrix tracing out qubits 2 and 3 (bipartition across spatial orbitals)
    # Subsystem A: Qubits 0 and 1 (Orbital 0, alpha and beta spins)
    rho_A = partial_trace(vqe_state, [2, 3])

    # 3. von Neumann Entanglement Entropy S(rho_A)
    # Quantifies the quantum entanglement generated across the H2 covalent bond
    vqe_entropy = float(entropy(rho_A, base=2))

    # FCI reference entanglement entropy
    rho_A_fci = partial_trace(fci_state, [2, 3])
    fci_entropy = float(entropy(rho_A_fci, base=2))

    # 4. State Purity gamma = Tr(rho^2)
    purity = float(np.real(np.trace(vqe_state.to_operator().data @ vqe_state.to_operator().data)))

    # Computational basis dominant components
    probs = vqe_state.probabilities_dict()
    dominant_states = {k: float(v) for k, v in sorted(probs.items(), key=lambda x: x[1], reverse=True)[:4]}

    return {
        "state_fidelity": fidelity,
        "von_neumann_entropy_vqe": vqe_entropy,
        "von_neumann_entropy_fci_target": fci_entropy,
        "entropy_delta": abs(vqe_entropy - fci_entropy),
        "state_purity": purity,
        "dominant_basis_states": dominant_states,
    }
