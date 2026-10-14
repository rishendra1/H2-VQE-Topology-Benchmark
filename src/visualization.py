"""Visualization and Reporting Module for H2 VQE Benchmark.

Generates:
1. Energy convergence trajectory comparison plots (Processor A vs Processor B vs FCI).
2. Structural metrics comparison bar charts (Circuit Depth, CX Count, SWAP Overhead).
3. Hardware coupling topology graph visualizations.
4. Summary benchmark tables saved in Markdown and CSV formats.
"""

from typing import Dict, Any, List, Tuple
import os
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from tabulate import tabulate

from src.problem import FCI_REFERENCE_ENERGY
from src.processors import PROCESSOR_A_EDGES, PROCESSOR_B_EDGES


FIGURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results", "figures"))
TABLES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results", "tables"))


def ensure_directories():
    """Ensures results output directories exist."""
    os.makedirs(FIGURES_DIR, exist_ok=True)
    os.makedirs(TABLES_DIR, exist_ok=True)


def plot_energy_convergence(
    results: Dict[str, Any],
    save_path: str = None
) -> str:
    """Plots VQE energy convergence histories against classical FCI target.

    Args:
        results: Benchmark dictionary returned by run_full_benchmark_suite.
        save_path: Destination file path. If None, saves in results/figures/.

    Returns:
        str: Absolute path of saved figure.
    """
    ensure_directories()
    if save_path is None:
        save_path = os.path.join(FIGURES_DIR, "energy_convergence.png")

    hist_a = results["processor_a"]["energy_history"]
    hist_b = results["processor_b"]["energy_history"]
    hist_ideal = results["ideal"]["energy_history"]
    fci_target = results.get("fci_target", FCI_REFERENCE_ENERGY)

    plt.figure(figsize=(10, 6), dpi=300)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # Plot trajectories
    plt.plot(range(1, len(hist_a) + 1), hist_a, label="Processor A (5Q Baseline, Noisy)", color="#1f77b4", lw=2, marker="o", markersize=3, alpha=0.9)
    plt.plot(range(1, len(hist_b) + 1), hist_b, label="Processor B (9Q Heavy-Hex, Noisy)", color="#d62728", lw=2, marker="s", markersize=3, alpha=0.9)
    plt.plot(range(1, len(hist_ideal) + 1), hist_ideal, label="Ideal Baseline (Noiseless, 4096 shots)", color="#2ca02c", lw=2, linestyle="--", alpha=0.85)

    # Reference FCI line
    plt.axhline(y=fci_target, color="#000000", linestyle=":", lw=2.2, label=f"Classical FCI Target ({fci_target:.4f} Ha)")

    # Chemical accuracy band (1 kcal/mol = 0.0016 Hartree)
    plt.fill_between(
        range(1, max(len(hist_a), len(hist_b)) + 1),
        fci_target - 0.0016,
        fci_target + 0.0016,
        color="gray",
        alpha=0.18,
        label="Chemical Accuracy (±1.6 mHa / 1 kcal/mol)"
    )

    plt.title(r"$\mathrm{H}_2$ VQE Ground-State Energy Convergence ($R = 0.74\,\mathrm{\AA}$)", fontsize=14, fontweight="bold", pad=12)
    plt.xlabel("Optimization Iteration (COBYLA)", fontsize=12)
    plt.ylabel("Energy (Hartree)", fontsize=12)
    plt.legend(frameon=True, fontsize=10, loc="upper right")
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    return save_path


def plot_circuit_metrics_comparison(
    results: Dict[str, Any],
    save_path: str = None
) -> str:
    """Plots comparative bar charts for depth, CX count, and gate inflation.

    Args:
        results: Benchmark dictionary.
        save_path: Destination file path.

    Returns:
        str: Absolute path of saved figure.
    """
    ensure_directories()
    if save_path is None:
        save_path = os.path.join(FIGURES_DIR, "circuit_metrics_comparison.png")

    mA = results["processor_a"]["circuit_metrics"]
    mB = results["processor_b"]["circuit_metrics"]

    categories = ["Transpiled Depth", "CX Gate Count", "SWAP Overhead (CX Inflation)", "Total Gates"]
    val_a = [mA["transpiled_depth"], mA["cx_count"], mA["cx_overhead"], mA["total_gates"]]
    val_b = [mB["transpiled_depth"], mB["cx_count"], mB["cx_overhead"], mB["total_gates"]]

    x = range(len(categories))
    width = 0.35

    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)
    rects1 = ax.bar([i - width / 2 for i in x], val_a, width, label="Processor A (5Q Baseline)", color="#1f77b4", edgecolor="black", alpha=0.88)
    rects2 = ax.bar([i + width / 2 for i in x], val_b, width, label="Processor B (9Q Heavy-Hex)", color="#d62728", edgecolor="black", alpha=0.88)

    ax.set_ylabel("Count / Gate Units", fontsize=12)
    ax.set_title("Architectural Routing & Structural Gate Overhead Comparison", fontsize=13, fontweight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=11)
    ax.legend(frameon=True, fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.6)

    # Value labels on top of bars
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f"{height}",
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center", va="bottom", fontsize=10, fontweight="bold")

    autolabel(rects1)
    autolabel(rects2)

    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    return save_path


def plot_hardware_topologies(save_path: str = None) -> str:
    """Visualizes the coupling graphs for Processor A (5Q) and Processor B (9Q Heavy-Hex).

    Args:
        save_path: Destination file path.

    Returns:
        str: Absolute path of saved figure.
    """
    ensure_directories()
    if save_path is None:
        save_path = os.path.join(FIGURES_DIR, "hardware_topologies.png")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6), dpi=300)

    # 1. Processor A (5-qubit branching tree)
    GA = nx.Graph()
    GA.add_nodes_from(range(5))
    GA.add_edges_from(PROCESSOR_A_EDGES)
    pos_A = {
        0: (0.0, 1.0),
        1: (1.0, 1.0),
        2: (2.0, 1.0),
        3: (1.0, 0.0),
        4: (2.0, 0.0)
    }
    nx.draw_networkx_nodes(GA, pos_A, ax=ax1, node_color="#aec7e8", edgecolors="#1f77b4", node_size=800, linewidths=2.5)
    nx.draw_networkx_labels(GA, pos_A, ax=ax1, font_size=12, font_weight="bold", font_color="#000000")
    nx.draw_networkx_edges(GA, pos_A, ax=ax1, edge_color="#1f77b4", width=2.5)
    ax1.set_title("Processor A: 5-Qubit Baseline\n(Constrained Branching Tree, 4 Edges)", fontsize=12, fontweight="bold", pad=10)
    ax1.axis("off")

    # 2. Processor B (9-qubit heavy-hex sparse)
    GB = nx.Graph()
    GB.add_nodes_from(range(9))
    GB.add_edges_from(PROCESSOR_B_EDGES)
    pos_B = {
        0: (0.0, 2.0), 1: (1.0, 2.0), 2: (2.0, 2.0),
        3: (0.0, 1.0), 4: (1.0, 1.0), 5: (2.0, 1.0),
        6: (0.0, 0.0), 7: (1.0, 0.0), 8: (2.0, 0.0)
    }
    nx.draw_networkx_nodes(GB, pos_B, ax=ax2, node_color="#ff9896", edgecolors="#d62728", node_size=800, linewidths=2.5)
    nx.draw_networkx_labels(GB, pos_B, ax=ax2, font_size=12, font_weight="bold", font_color="#000000")
    nx.draw_networkx_edges(GB, pos_B, ax=ax2, edge_color="#d62728", width=2.5)
    ax2.set_title("Processor B: 9-Qubit Heavy-Hex Sparse\n(12 Coupling Edges, Hexagonal Subgraph)", fontsize=12, fontweight="bold", pad=10)
    ax2.axis("off")

    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    return save_path


def generate_benchmark_table(
    results: Dict[str, Any],
    save_md_path: str = None,
    save_csv_path: str = None
) -> Tuple[str, pd.DataFrame]:
    """Generates the official summary benchmark comparison table.

    Args:
        results: Benchmark dictionary.
        save_md_path: Markdown table path.
        save_csv_path: CSV table path.

    Returns:
        Tuple[str, pd.DataFrame]: Markdown formatted table string and pandas DataFrame.
    """
    ensure_directories()
    if save_md_path is None:
        save_md_path = os.path.join(TABLES_DIR, "benchmark_summary.md")
    if save_csv_path is None:
        save_csv_path = os.path.join(TABLES_DIR, "benchmark_summary.csv")

    fci = results.get("fci_target", FCI_REFERENCE_ENERGY)
    res_a = results["processor_a"]
    res_b = results["processor_b"]
    res_ideal = results["ideal"]

    mA = res_a["circuit_metrics"]
    mB = res_b["circuit_metrics"]
    mIdeal = res_ideal["circuit_metrics"]

    table_data = [
        {
            "Architecture / Metric": "Processor A (5Q Baseline)",
            "Qubits": 5,
            "Coupling Edges": len(PROCESSOR_A_EDGES),
            "Noise Model": "Official Synthetic (0.1% 1Q, 0.5% CX, 1% RO)",
            "Transpiled Depth": mA["transpiled_depth"],
            "Total Gates": mA["total_gates"],
            "CX Gates": mA["cx_count"],
            "SWAP Overhead (CX)": mA["cx_overhead"],
            "Final Energy (Ha)": f"{res_a['final_energy']:.6f}",
            "FCI Target (Ha)": f"{fci:.6f}",
            "Energy Error (Ha)": f"{res_a['energy_error_hartree']:+.6f}",
            "Error (kcal/mol)": f"{res_a['energy_error_kcal_mol']:+.2f}",
        },
        {
            "Architecture / Metric": "Processor B (9Q Heavy-Hex)",
            "Qubits": 9,
            "Coupling Edges": len(PROCESSOR_B_EDGES),
            "Noise Model": "Official Synthetic (0.1% 1Q, 0.5% CX, 1% RO)",
            "Transpiled Depth": mB["transpiled_depth"],
            "Total Gates": mB["total_gates"],
            "CX Gates": mB["cx_count"],
            "SWAP Overhead (CX)": mB["cx_overhead"],
            "Final Energy (Ha)": f"{res_b['final_energy']:.6f}",
            "FCI Target (Ha)": f"{fci:.6f}",
            "Energy Error (Ha)": f"{res_b['energy_error_hartree']:+.6f}",
            "Error (kcal/mol)": f"{res_b['energy_error_kcal_mol']:+.2f}",
        },
        {
            "Architecture / Metric": "Ideal Baseline (Noiseless)",
            "Qubits": 5,
            "Coupling Edges": len(PROCESSOR_A_EDGES),
            "Noise Model": "None (Noiseless 4096 shots)",
            "Transpiled Depth": mIdeal["transpiled_depth"],
            "Total Gates": mIdeal["total_gates"],
            "CX Gates": mIdeal["cx_count"],
            "SWAP Overhead (CX)": mIdeal["cx_overhead"],
            "Final Energy (Ha)": f"{res_ideal['final_energy']:.6f}",
            "FCI Target (Ha)": f"{fci:.6f}",
            "Energy Error (Ha)": f"{res_ideal['energy_error_hartree']:+.6f}",
            "Error (kcal/mol)": f"{res_ideal['energy_error_kcal_mol']:+.2f}",
        },
    ]

    df = pd.DataFrame(table_data)
    df.to_csv(save_csv_path, index=False)

    md_table = tabulate(df, headers="keys", tablefmt="github", showindex=False)
    with open(save_md_path, "w", encoding="utf-8") as f:
        f.write("# H2 VQE Hardware Co-Design Benchmark Summary Table\n\n")
        f.write(md_table)
        f.write("\n\n")
        f.write(f"*Note: Chemical accuracy threshold is 1 kcal/mol ≈ 0.001594 Hartree. Compilation constraints: optimization_level=1, seed=42, shots=4096.*\n")

    return md_table, df
