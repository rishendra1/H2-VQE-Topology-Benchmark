"""Structural and Architectural Metrics Module for VQE Circuits.

Computes:
- Transpiled circuit depth
- Total gate count
- 2-qubit (CX) gate count
- Physical SWAP routing overhead (SWAP gates inserted and CX gate inflation)
- Hardware routing efficiency ratios
"""

from typing import Dict, Any
from qiskit import QuantumCircuit


def extract_circuit_metrics(
    transpiled_circuit: QuantumCircuit,
    original_circuit: QuantumCircuit = None,
    processor_name: str = "Unknown"
) -> Dict[str, Any]:
    """Extracts structural and routing performance metrics from a transpiled circuit.

    Args:
        transpiled_circuit: The transpiled QuantumCircuit targeted to physical hardware.
        original_circuit: Optional uncompiled abstract circuit for comparative overhead analysis.
        processor_name: Identifier string for the target processor.

    Returns:
        Dict[str, Any]: Metric dictionary with depth, gate counts, SWAP count, and overheads.
    """
    ops = transpiled_circuit.count_ops()
    depth = transpiled_circuit.depth()
    total_gates = sum(ops.values())
    cx_count = ops.get("cx", 0) + ops.get("ecr", 0) + ops.get("cz", 0)
    swap_count = ops.get("swap", 0)

    # If original circuit is provided, calculate overhead
    orig_cx = 0
    orig_total = 0
    orig_depth = 0
    if original_circuit is not None:
        orig_ops = original_circuit.count_ops()
        orig_cx = orig_ops.get("cx", 0) + orig_ops.get("ecr", 0) + orig_ops.get("cz", 0)
        orig_total = sum(orig_ops.values())
        orig_depth = original_circuit.depth()

    # In transpiled circuits with native CX basis, SWAP gates are typically decomposed into 3 CX gates.
    # Therefore, CX inflation (transpiled CX - original CX) directly reflects routing and basis synthesis overhead.
    cx_overhead = max(0, cx_count - orig_cx)
    swap_equivalent = cx_overhead // 3 if orig_cx > 0 else swap_count

    return {
        "processor": processor_name,
        "transpiled_depth": depth,
        "total_gates": total_gates,
        "cx_count": cx_count,
        "swap_count": swap_count,
        "cx_overhead": cx_overhead,
        "swap_equivalent": swap_equivalent,
        "original_depth": orig_depth,
        "original_cx": orig_cx,
        "original_total_gates": orig_total,
        "ops_breakdown": dict(ops),
    }


def compare_metrics(metrics_a: Dict[str, Any], metrics_b: Dict[str, Any]) -> Dict[str, Any]:
    """Computes comparative routing efficiency delta between Processor A and Processor B.

    Args:
        metrics_a: Metrics dictionary for Processor A (5-qubit baseline).
        metrics_b: Metrics dictionary for Processor B (9-qubit heavy-hex).

    Returns:
        Dict[str, Any]: Comparative differential metrics.
    """
    depth_diff = metrics_b["transpiled_depth"] - metrics_a["transpiled_depth"]
    cx_diff = metrics_b["cx_count"] - metrics_a["cx_count"]
    depth_pct = (depth_diff / metrics_a["transpiled_depth"]) * 100.0 if metrics_a["transpiled_depth"] > 0 else 0.0
    cx_pct = (cx_diff / metrics_a["cx_count"]) * 100.0 if metrics_a["cx_count"] > 0 else 0.0

    return {
        "depth_difference (B - A)": depth_diff,
        "depth_percent_change": depth_pct,
        "cx_difference (B - A)": cx_diff,
        "cx_percent_change": cx_pct,
    }
