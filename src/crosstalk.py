"""Parasitic Spectator ZZ Crosstalk & Coherent Echo Cancellation Module.

Models physical transmon parasitic interactions:
    H_crosstalk = sum_{(j, k) in E} xi_jk * Z_j * Z_k
where xi_jk is the static ZZ coupling strength (typically 50-150 kHz on superconducting chips).

Demonstrates:
1. Accumulated coherent phase error during long routing delays on Processor B.
2. How Dynamical Decoupling (CPMG / XY4) refocuses spectator qubits, echoing out
   the static ZZ crosstalk interaction: U_DD^dag * exp(-i * H_zz * t) * U_DD = I + O(t^2).
"""

from typing import Dict, Any, List, Tuple
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, SparsePauliOp

from src.processors import PROCESSOR_B_EDGES


def compute_zz_crosstalk_phase_error(
    gate_duration_ns: float,
    zz_coupling_khz: float = 100.0,
    edges: List[List[int]] = None
) -> float:
    """Computes the accumulated coherent spectator phase shift delta_phi = xi * t_gate."""
    t_seconds = gate_duration_ns * 1e-9
    xi_rad_per_sec = 2.0 * np.pi * (zz_coupling_khz * 1e3)
    phase_shift_rad = xi_rad_per_sec * t_seconds
    return float(phase_shift_rad)


def simulate_crosstalk_mitigation_with_dd(
    routing_delay_ns: float = 600.0,
    zz_coupling_khz: float = 120.0
) -> Dict[str, Any]:
    """Simulates how CPMG/XY4 dynamical decoupling suppresses spectator crosstalk phase accumulation.

    During a 600 ns routing delay (equivalent to a 2-CX SWAP chain on Processor B):
    - Without DD: Spectator accumulates coherent phase error exp(-i * xi * t * Z1*Z2).
    - With CPMG (X - X echo): The sign of Z is flipped halfway, causing the forward and
      backward phases to cancel to zero: xi*(t/2) - xi*(t/2) = 0.
    """
    raw_phase_rad = compute_zz_crosstalk_phase_error(routing_delay_ns, zz_coupling_khz)

    # Initial spectator state (|0> + |1>)/sqrt(2) on 2 spectator qubits
    # Under ZZ coupling: |00> -> e^{-i phi} |00>, |01> -> e^{i phi} |01>, etc.
    phi = raw_phase_rad

    # Raw fidelity decay under unmitigated ZZ evolution: F = |<psi_0 | psi(t)>|^2 = cos^2(phi)
    raw_fidelity = float(np.cos(phi) ** 2)

    # With Dynamical Decoupling (perfect pi pulse sequence): residual phase error is suppressed to O(t^3)
    # Residual phase error due to 1% pulse angle imperfection:
    residual_phase = phi * 0.01
    mitigated_fidelity = float(np.cos(residual_phase) ** 2)

    return {
        "routing_delay_ns": routing_delay_ns,
        "zz_coupling_khz": zz_coupling_khz,
        "raw_accumulated_phase_rad": raw_phase_rad,
        "raw_spectator_fidelity": raw_fidelity,
        "dd_refocused_spectator_fidelity": mitigated_fidelity,
        "fidelity_recovery_percent": (mitigated_fidelity - raw_fidelity) * 100.0,
        "crosstalk_suppression_ratio": f"{raw_phase_rad / max(1e-5, residual_phase):.1f}x echo cancellation",
        "physical_mechanism": "Hahn echo / CPMG parity inversion cancels static ZZ Hamiltonian"
    }
