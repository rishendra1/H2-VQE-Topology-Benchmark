"""Dynamical Decoupling (DD) Sequences for Idle Qubits during Routing Delays.

Implements:
1. CPMG refocusing sequence (X - X).
2. XY4 robust decoupling sequence (X - Y - X - Y).
3. Automatic insertion of DD pulse trains into idle spectator qubit time slots to suppress
   low-frequency 1/f flux dephasing (T2) during long SWAP routing chains.
"""

from typing import List, Dict, Any, Tuple
from qiskit import QuantumCircuit
from qiskit.circuit.library import XGate, YGate


def insert_dynamical_decoupling(
    circuit: QuantumCircuit,
    sequence: str = "XY4",
    qubits_to_protect: List[int] = None
) -> QuantumCircuit:
    """Inserts a Dynamical Decoupling sequence onto idle spectator qubits in a transpiled circuit.

    Args:
        circuit: Transpiled QuantumCircuit.
        sequence: 'XY4' (X-Y-X-Y) or 'CPMG' (X-X).
        qubits_to_protect: List of physical qubit indices to decouple. If None, applies to all idle lines.

    Returns:
        QuantumCircuit: Circuit augmented with dynamical decoupling refocusing pulses.
    """
    dd_circuit = QuantumCircuit(*circuit.qregs, *circuit.cregs, name=f"{circuit.name}_DD_{sequence}")

    if qubits_to_protect is None:
        qubits_to_protect = list(range(circuit.num_qubits))

    # Append original operations and schedule refocusing pulses
    for instruction in circuit.data:
        op = instruction.operation
        qubits = instruction.qubits
        clbits = instruction.clbits
        dd_circuit.append(op, qubits, clbits)

        # For 2-qubit operations (which incur significant pulse duration),
        # apply decoupling pulses on the spectator physical qubits
        if op.num_qubits == 2:
            active_q_indices = [q._index if hasattr(q, '_index') else circuit.find_bit(q).index for q in qubits]
            spectator_qubits = [q_idx for q_idx in qubits_to_protect if q_idx not in active_q_indices]

            for s_q in spectator_qubits:
                if sequence.upper() == "XY4":
                    dd_circuit.x(s_q)
                    dd_circuit.y(s_q)
                    dd_circuit.x(s_q)
                    dd_circuit.y(s_q)
                elif sequence.upper() == "CPMG":
                    dd_circuit.x(s_q)
                    dd_circuit.x(s_q)

    return dd_circuit


def benchmark_dd_overhead(circuit: QuantumCircuit) -> Dict[str, Any]:
    """Analyzes the gate overhead and refocusing pulse counts introduced by DD sequences."""
    dd_xy4 = insert_dynamical_decoupling(circuit, sequence="XY4")
    dd_cpmg = insert_dynamical_decoupling(circuit, sequence="CPMG")

    orig_ops = circuit.count_ops()
    xy4_ops = dd_xy4.count_ops()
    cpmg_ops = dd_cpmg.count_ops()

    return {
        "original_depth": circuit.depth(),
        "original_total_gates": sum(orig_ops.values()),
        "cpmg_depth": dd_cpmg.depth(),
        "cpmg_total_gates": sum(cpmg_ops.values()),
        "cpmg_refocusing_pulses": sum(cpmg_ops.values()) - sum(orig_ops.values()),
        "xy4_depth": dd_xy4.depth(),
        "xy4_total_gates": sum(xy4_ops.values()),
        "xy4_refocusing_pulses": sum(xy4_ops.values()) - sum(orig_ops.values()),
    }
