"""CLI script to execute the complete H2 VQE Hardware Co-Design Benchmark."""

import os
import sys
import json

from src.vqe_runner import run_full_benchmark_suite
from src.visualization import (
    plot_energy_convergence,
    plot_circuit_metrics_comparison,
    plot_hardware_topologies,
    generate_benchmark_table
)

def main():
    print("================================================================")
    print("  H2-VQE-Topology-Benchmark: Hardware Co-Design Project (PS-C1) ")
    print("================================================================")

    # 1. Run full benchmark suite
    results = run_full_benchmark_suite(maxiter=40, shots=4096, seed=42, entanglement="full", reps=2)

    # 2. Generate all figures
    print("\n>>> Generating visualization figures...")
    conv_fig = plot_energy_convergence(results)
    print(f"    Saved: {conv_fig}")

    metrics_fig = plot_circuit_metrics_comparison(results)
    print(f"    Saved: {metrics_fig}")

    topologies_fig = plot_hardware_topologies()
    print(f"    Saved: {topologies_fig}")

    # 3. Generate summary tables
    print("\n>>> Generating benchmark summary tables...")
    md_table, df = generate_benchmark_table(results)
    print("\n" + md_table + "\n")

    # 4. Save raw results JSON for notebook and reports
    json_path = os.path.join(os.path.dirname(__file__), "results", "tables", "raw_benchmark_results.json")
    clean_results = {
        "problem_metadata": results["problem_metadata"],
        "fci_target": results["fci_target"],
        "processor_a": {
            "final_energy": results["processor_a"]["final_energy"],
            "energy_error_hartree": results["processor_a"]["energy_error_hartree"],
            "energy_error_kcal_mol": results["processor_a"]["energy_error_kcal_mol"],
            "circuit_metrics": results["processor_a"]["circuit_metrics"],
            "energy_history": results["processor_a"]["energy_history"],
            "elapsed_time_sec": results["processor_a"]["elapsed_time_sec"]
        },
        "processor_b": {
            "final_energy": results["processor_b"]["final_energy"],
            "energy_error_hartree": results["processor_b"]["energy_error_hartree"],
            "energy_error_kcal_mol": results["processor_b"]["energy_error_kcal_mol"],
            "circuit_metrics": results["processor_b"]["circuit_metrics"],
            "energy_history": results["processor_b"]["energy_history"],
            "elapsed_time_sec": results["processor_b"]["elapsed_time_sec"]
        },
        "ideal": {
            "final_energy": results["ideal"]["final_energy"],
            "energy_error_hartree": results["ideal"]["energy_error_hartree"],
            "energy_error_kcal_mol": results["ideal"]["energy_error_kcal_mol"],
            "circuit_metrics": results["ideal"]["circuit_metrics"],
            "energy_history": results["ideal"]["energy_history"],
            "elapsed_time_sec": results["ideal"]["elapsed_time_sec"]
        },
        "comparison_delta": results["comparison_delta"]
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(clean_results, f, indent=2)
    print(f"    Saved raw results: {json_path}")
    print("\n>>> Complete benchmark finished successfully!")

if __name__ == "__main__":
    main()
