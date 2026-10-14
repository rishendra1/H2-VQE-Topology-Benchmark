"""Master Orchestration CLI Script for H2-VQE-Topology-Benchmark."""

import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.problem import get_h2_problem, FCI_REFERENCE_ENERGY
from src.processors import get_processor_a, get_processor_b, get_official_noise_model
from src.routing import build_h2_ansatz
from src.vqe_runner import run_full_benchmark_suite
from src.visualization import (
    plot_energy_convergence,
    plot_circuit_metrics_comparison,
    plot_hardware_topologies,
    generate_benchmark_table
)
from src.mitigation import execute_with_zne
from src.co_design import benchmark_codesign_impact
from src.pes import compute_pes_curve, plot_potential_energy_surface
from src.optimizers import compare_cobyla_vs_spsa, plot_optimizer_comparison


def main():
    print("=" * 75)
    print("  H2-VQE-Topology-Benchmark: Advanced Hardware Co-Design Suite (PS-C1)  ")
    print("=" * 75)

    # 1. Run Core Hardware Benchmark (Processor A vs Processor B vs Ideal)
    print("\n>>> [1/5] Executing Core VQE Benchmark across Hardware Topologies...")
    results = run_full_benchmark_suite(maxiter=40, shots=4096, seed=42, entanglement="full", reps=2)

    # 2. Run Quantum Error Mitigation (Zero-Noise Extrapolation)
    print("\n>>> [2/5] Applying Zero-Noise Extrapolation (ZNE) with Unitary Gate Folding...")
    proc_a = get_processor_a(seed=42)
    noise_model = get_official_noise_model()
    t_a = results["processor_a"]["transpiled_circuit"]
    H, _, _ = get_h2_problem()
    phys_H = H.apply_layout(t_a.layout)
    opt_params = np.array(results["processor_a"]["optimal_parameters"])

    zne_results = execute_with_zne(
        circuit=t_a,
        observable=phys_H,
        parameters=opt_params,
        noise_model=noise_model,
        scale_factors=[1, 3, 5],
        shots=4096,
        seed=42
    )
    print(f"    Raw Unmitigated Energy:      {zne_results['raw_unmitigated_energy']:.6f} Ha")
    print(f"    Linear Extrapolated Energy:  {zne_results['linear_extrapolated_energy']:.6f} Ha")
    print(f"    Richardson Extrapolated (E0): {zne_results['richardson_extrapolated_energy']:.6f} Ha")
    print(f"    ZNE Error Recovery Delta:    {zne_results['mitigation_delta_hartree']:.6f} Ha")

    # 3. Algorithm-Hardware Co-Design Analysis
    print("\n>>> [3/5] Benchmarking Algorithm-Hardware Co-Design (Native Graph vs Naive)...")
    codesign_results = benchmark_codesign_impact(optimization_level=1, seed_transpiler=42)
    print(f"    Processor A Naive:     Depth={codesign_results['naive_a']['transpiled_depth']}, CX={codesign_results['naive_a']['cx_count']}, SWAPs=~{codesign_results['naive_a']['swap_equivalent']}")
    print(f"    Processor A CoDesign:  Depth={codesign_results['codesign_a']['transpiled_depth']}, CX={codesign_results['codesign_a']['cx_count']}, SWAPs={codesign_results['codesign_a']['swap_equivalent']} (ZERO SWAPs!)")
    print(f"    Processor A Reduction: -{codesign_results['proc_a_cx_savings']} CX gates, -{codesign_results['proc_a_depth_reduction']} circuit depth")

    print(f"    Processor B Naive:     Depth={codesign_results['naive_b']['transpiled_depth']}, CX={codesign_results['naive_b']['cx_count']}, SWAPs=~{codesign_results['naive_b']['swap_equivalent']}")
    print(f"    Processor B CoDesign:  Depth={codesign_results['codesign_b']['transpiled_depth']}, CX={codesign_results['codesign_b']['cx_count']}, SWAPs={codesign_results['codesign_b']['swap_equivalent']} (ZERO SWAPs!)")
    print(f"    Processor B Reduction: -{codesign_results['proc_b_cx_savings']} CX gates, -{codesign_results['proc_b_depth_reduction']} circuit depth")

    # 4. Multi-Optimizer Study (COBYLA vs SPSA)
    print("\n>>> [4/5] Executing Optimizer Benchmark: COBYLA vs SPSA (4096 shots)...")
    opt_data = compare_cobyla_vs_spsa(maxiter=35, shots=4096, seed=42)
    opt_fig = plot_optimizer_comparison(opt_data)
    print(f"    COBYLA Final: {opt_data['cobyla_final_energy']:.6f} Ha | SPSA Final: {opt_data['spsa_final_energy']:.6f} Ha")
    print(f"    Saved: {opt_fig}")

    # 5. Potential Energy Surface (PES) Dissociation Curve
    print("\n>>> [5/5] Computing H2 Potential Energy Surface (PES) across Bond Dissociation...")
    pes_data = compute_pes_curve(bond_distances=[0.5, 0.74, 1.0, 1.3, 1.6, 2.0], maxiter=20, shots=4096, seed=42)
    pes_fig = plot_potential_energy_surface(pes_data)
    print(f"    Saved: {pes_fig}")

    # Generate Primary Visualizations
    print("\n>>> Generating Primary Benchmark Figures...")
    conv_fig = plot_energy_convergence(results)
    print(f"    Saved: {conv_fig}")
    metrics_fig = plot_circuit_metrics_comparison(results)
    print(f"    Saved: {metrics_fig}")
    topologies_fig = plot_hardware_topologies()
    print(f"    Saved: {topologies_fig}")

    # Summary Tables
    print("\n>>> Generating Summary Tables...")
    md_table, df = generate_benchmark_table(results)
    print("\n" + md_table + "\n")

    # Save comprehensive JSON
    json_path = os.path.join(os.path.dirname(__file__), "results", "tables", "raw_benchmark_results.json")
    payload = {
        "problem_metadata": results["problem_metadata"],
        "fci_target": results["fci_target"],
        "processor_a": results["processor_a"],
        "processor_b": results["processor_b"],
        "ideal": results["ideal"],
        "zne_mitigation": zne_results,
        "co_design": codesign_results,
        "optimizer_comparison": {
            "cobyla_final": opt_data["cobyla_final_energy"],
            "spsa_final": opt_data["spsa_final_energy"],
            "cobyla_time": opt_data["cobyla_time"],
            "spsa_time": opt_data["spsa_time"]
        },
        "pes_summary": pes_data
    }
    # Clean non-serializable fields
    payload["processor_a"].pop("transpiled_circuit", None)
    payload["processor_b"].pop("transpiled_circuit", None)
    payload["ideal"].pop("transpiled_circuit", None)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"    Saved: {json_path}")
    print("\n>>> ALL BENCHMARK PHASES & ENHANCEMENTS COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
