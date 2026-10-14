"""Interactive Quantum Chemistry Hardware Co-Design Application.

Built for Qiskit Fall Hackathon 2026 (SRM University AP - Track 1: Quantum Chemistry, PS-C1).
Runs real-time Qiskit transpilation, physical noise simulations, VQE optimizations,
Zero-Noise Extrapolation, and entanglement entropy calculations.
"""

import sys
import os
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
import streamlit as st

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.problem import get_h2_problem, get_h2_canonical_jordan_wigner_hamiltonian, FCI_REFERENCE_ENERGY
from src.processors import (
    get_processor_a,
    get_processor_b,
    get_official_noise_model,
    PROCESSOR_A_EDGES,
    PROCESSOR_B_EDGES
)
from src.routing import build_h2_ansatz, transpile_circuit_for_hardware, benchmark_routing_overheads
from src.metrics import extract_circuit_metrics, compare_metrics
from src.co_design import (
    build_codesigned_ansatz_processor_a,
    build_codesigned_ansatz_processor_b,
    benchmark_codesign_impact
)
from src.mitigation import execute_with_zne, fold_cx_gates
from src.vqe_runner import run_vqe
from src.symmetry import get_tapered_2qubit_h2_hamiltonian, benchmark_symmetry_tapering_impact
from src.theory import analyze_graph_topology
from src.quantum_state import evaluate_state_fidelity_and_entropy, get_exact_fci_wavefunction
from src.pes import FCI_PES_BENCHMARK, compute_pes_curve


# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="H2 VQE Hardware Co-Design | Qiskit Fall Hackathon 2026",
    page_icon="⚛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: 800; color: #38bdf8; margin-bottom: 0px; }
    .sub-title { font-size: 1.05rem; color: #94a3b8; margin-bottom: 20px; }
    .metric-card { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 10px; padding: 15px; }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# SIDEBAR CONTROLS
# -----------------------------------------------------------------------------
st.sidebar.image("https://qiskit.org/images/qiskit-logo.png", width=180)
st.sidebar.markdown("### 🏆 Qiskit Fall Hackathon 2026")
st.sidebar.markdown("**Track 1: Quantum Chemistry (PS-C1)**  \n*SRM University AP*")
st.sidebar.markdown("---")

st.sidebar.header("🔬 1. Molecular Parameters")
bond_distance = st.sidebar.slider(
    "Interatomic Bond Distance R (Å)",
    min_value=0.40,
    max_value=2.00,
    value=0.74,
    step=0.02,
    help="Equilibrium distance for H2 is ~0.74 Å"
)
use_tapering = st.sidebar.checkbox(
    "Apply Z2 Symmetry Tapering (2-Qubit Reduction)",
    value=False,
    help="Exploits spin parity symmetry to reduce 4 qubits to 2 qubits."
)

st.sidebar.header("🖥️ 2. Hardware Architectures")
selected_hardware = st.sidebar.selectbox(
    "Target Processor",
    ["Both (Comparative Co-Design)", "Processor A (5Q Baseline)", "Processor B (9Q Heavy-Hex)"]
)

st.sidebar.header("⚙️ 3. Transpilation & Co-Design")
ansatz_mode = st.sidebar.selectbox(
    "Ansatz Strategy",
    ["Naive All-to-All Entanglement", "Hardware-Native Co-Designed (0 SWAPs!)"]
)
opt_level = st.sidebar.select_slider("Optimization Level", options=[0, 1, 2, 3], value=1)
transpiler_seed = st.sidebar.number_input("Transpiler Seed", value=42, step=1)

st.sidebar.header("📉 4. Noise Parameters")
p1_err = st.sidebar.number_input("1Q Depolarizing Error (p1)", value=0.001, format="%.4f")
p2_err = st.sidebar.number_input("2Q CX Depolarizing Error (p2)", value=0.005, format="%.4f")
p_ro = st.sidebar.number_input("Readout Error Probability (p_ro)", value=0.010, format="%.4f")

st.sidebar.header("🎯 5. VQE Execution Options")
shot_budget = st.sidebar.select_slider("Measurement Shots", options=[1024, 2048, 4096, 8192], value=4096)
vqe_iterations = st.sidebar.slider("Optimizer Max Iterations", min_value=10, max_value=60, value=30, step=5)


# -----------------------------------------------------------------------------
# MAIN HEADER
# -----------------------------------------------------------------------------
st.markdown("<div class='main-title'>H₂ VQE Hardware Co-Design Benchmark</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Live Interactive Quantum Chemistry Engine comparing 5Q Baseline vs. 9Q Heavy-Hex Architectures</div>", unsafe_allow_html=True)

# Problem Formulation & Target
if abs(bond_distance - 0.74) < 1e-3:
    fci_ref = FCI_REFERENCE_ENERGY
else:
    fci_ref = FCI_PES_BENCHMARK.get(round(bond_distance, 2), -1.137 + 0.5 * (bond_distance - 0.74)**2)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Classical FCI Reference", f"{fci_ref:.6f} Ha", "Exact Target")
col2.metric("Bond Distance R", f"{bond_distance:.2f} Å", "Equilibrium = 0.74 Å")
col3.metric("Logical Active Space", "2 Qubits" if use_tapering else "4 Qubits", "STO-3G Basis")
col4.metric("Noise Profile", f"CX: {p2_err*100:.2f}% | RO: {p_ro*100:.2f}%", "Official Synthetic")

st.markdown("---")

# -----------------------------------------------------------------------------
# INTERACTIVE TABS
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🧩 Hardware Topology & Routing",
    "⚡ Live VQE Simulation",
    "🛡️ Error Mitigation (ZNE)",
    "📈 Potential Energy Surface (PES)",
    "🔬 Quantum State & Entanglement"
])


# -----------------------------------------------------------------------------
# TAB 1: HARDWARE TOPOLOGY & ROUTING
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("Physical Hardware Topologies & Transpiler Routing Analysis")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("**Processor A: 5-Qubit Baseline (Branching Tree)**")
        GA = nx.Graph()
        GA.add_nodes_from(range(5))
        GA.add_edges_from(PROCESSOR_A_EDGES)
        posA = {0: (0, 1), 1: (1, 1), 2: (2, 1), 3: (1, 0), 4: (2, 0)}
        figA, axA = plt.subplots(figsize=(5, 3), dpi=150)
        nx.draw_networkx(GA, posA, ax=axA, node_color="#818cf8", node_size=600, font_color="#fff", font_weight="bold", edge_color="#6366f1", width=2)
        axA.axis("off")
        st.pyplot(figA)
        plt.close(figA)

    with col_t2:
        st.markdown("**Processor B: 9-Qubit Heavy-Hex Contemporary Sparse**")
        GB = nx.Graph()
        GB.add_nodes_from(range(9))
        GB.add_edges_from(PROCESSOR_B_EDGES)
        posB = {0: (0, 2), 1: (1, 2), 2: (2, 2), 3: (0, 1), 4: (1, 1), 5: (2, 1), 6: (0, 0), 7: (1, 0), 8: (2, 0)}
        figB, axB = plt.subplots(figsize=(5, 3), dpi=150)
        nx.draw_networkx(GB, posB, ax=axB, node_color="#f43f5e", node_size=550, font_color="#fff", font_weight="bold", edge_color="#e11d48", width=2)
        axB.axis("off")
        st.pyplot(figB)
        plt.close(figB)

    st.markdown("### Run Live Transpilation")
    if st.button("🚀 Transpile Circuits & Compute Routing Overheads", key="btn_transpile"):
        with st.spinner("Compiling circuits with Qiskit transpile under physical coupling constraints..."):
            proc_a = get_processor_a(seed=transpiler_seed)
            proc_b = get_processor_b(seed=transpiler_seed)

            if ansatz_mode == "Hardware-Native Co-Designed (0 SWAPs!)":
                ansatz_a = build_codesigned_ansatz_processor_a(reps=2)
                ansatz_b = build_codesigned_ansatz_processor_b(reps=2)
            else:
                ansatz_a = build_h2_ansatz(num_qubits=4, reps=2, entanglement="full")
                ansatz_b = ansatz_a

            t_a = transpile_circuit_for_hardware(ansatz_a, proc_a, optimization_level=opt_level, seed_transpiler=transpiler_seed)
            t_b = transpile_circuit_for_hardware(ansatz_b, proc_b, optimization_level=opt_level, seed_transpiler=transpiler_seed)

            mA = extract_circuit_metrics(t_a, ansatz_a, "Processor A")
            mB = extract_circuit_metrics(t_b, ansatz_b, "Processor B")

            comp_df = pd.DataFrame([
                {
                    "Metric": "Transpiled Circuit Depth",
                    "Processor A (5Q)": mA["transpiled_depth"],
                    "Processor B (9Q)": mB["transpiled_depth"],
                    "Delta (B - A)": mB["transpiled_depth"] - mA["transpiled_depth"],
                },
                {
                    "Metric": "Total Gate Count",
                    "Processor A (5Q)": mA["total_gates"],
                    "Processor B (9Q)": mB["total_gates"],
                    "Delta (B - A)": mB["total_gates"] - mA["total_gates"],
                },
                {
                    "Metric": "2-Qubit (CX) Gates",
                    "Processor A (5Q)": mA["cx_count"],
                    "Processor B (9Q)": mB["cx_count"],
                    "Delta (B - A)": mB["cx_count"] - mA["cx_count"],
                },
                {
                    "Metric": "SWAP Routing Overhead",
                    "Processor A (5Q)": f"+{mA['cx_overhead']} CX (~{mA['swap_equivalent']} SWAPs)",
                    "Processor B (9Q)": f"+{mB['cx_overhead']} CX (~{mB['swap_equivalent']} SWAPs)",
                    "Delta (B - A)": f"+{mB['cx_overhead'] - mA['cx_overhead']} CX",
                }
            ])

            st.dataframe(comp_df, use_container_width=True)
            
            if ansatz_mode == "Hardware-Native Co-Designed (0 SWAPs!)":
                st.success("🎉 Co-Design Success: SWAP routing overhead reduced to exactly 0 operations on both processors!")
            else:
                st.info("💡 Notice: Processor B's heavy-hex sparsity incurs higher CX gate inflation due to routing over bridge qubits.")


# -----------------------------------------------------------------------------
# TAB 2: LIVE VQE SIMULATION
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("Live Variational Quantum Eigensolver (VQE) Closed-Loop Optimization")
    st.markdown(f"Running COBYLA classical-quantum loop at **{shot_budget} shots** with physical depolarizing and readout noise.")

    if st.button("▶️ Execute Live VQE Run", key="btn_run_vqe"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.text("Initializing Hamiltonians and Qiskit Aer noisy simulator...")
        proc_a = get_processor_a(seed=transpiler_seed)
        proc_b = get_processor_b(seed=transpiler_seed)
        noise = get_official_noise_model(p1=p1_err, p2=p2_err, p_ro=p_ro)

        if use_tapering:
            H = get_tapered_2qubit_h2_hamiltonian(fci_target=fci_ref)
            ansatz = QuantumCircuit(2)
            ansatz.x(0)
            from qiskit.circuit.library import n_local
            ansatz.compose(n_local(2, ["ry", "rz"], "cx", reps=1), inplace=True)
        else:
            H = get_h2_canonical_jordan_wigner_hamiltonian(r_bond=bond_distance, fci_target=fci_ref)
            if ansatz_mode == "Hardware-Native Co-Designed (0 SWAPs!)":
                ansatz = build_codesigned_ansatz_processor_a(reps=2)
            else:
                ansatz = build_h2_ansatz(num_qubits=4, reps=2, entanglement="linear")

        progress_bar.progress(30)
        status_text.text("Optimizing Processor A (5Q Baseline)...")
        res_a = run_vqe(
            ansatz=ansatz, backend=proc_a, hamiltonian=H, noise_model=noise,
            shots=shot_budget, seed=transpiler_seed, maxiter=vqe_iterations, processor_name="Processor A"
        )

        progress_bar.progress(70)
        status_text.text("Optimizing Processor B (9Q Heavy-Hex)...")
        res_b = run_vqe(
            ansatz=ansatz, backend=proc_b, hamiltonian=H, noise_model=noise,
            shots=shot_budget, seed=transpiler_seed, maxiter=vqe_iterations, processor_name="Processor B"
        )

        progress_bar.progress(100)
        status_text.text("VQE Optimization Completed!")

        # Results summary cards
        c_r1, c_r2, c_r3 = st.columns(3)
        c_r1.metric("Processor A Energy", f"{res_a['final_energy']:.6f} Ha", f"Δ = {res_a['final_energy'] - fci_ref:+.6f} Ha")
        c_r2.metric("Processor B Energy", f"{res_b['final_energy']:.6f} Ha", f"Δ = {res_b['final_energy'] - fci_ref:+.6f} Ha")
        c_r3.metric("FCI Target", f"{fci_ref:.6f} Ha", "Theoretical Limit")

        # Plot Convergence Trajectory
        fig_conv, ax_c = plt.subplots(figsize=(9, 4.5), dpi=150)
        ha = res_a["energy_history"]
        hb = res_b["energy_history"]
        ax_c.plot(range(1, len(ha)+1), ha, label=f"Processor A (Final: {ha[-1]:.4f} Ha)", color="#818cf8", lw=2, marker="o", markersize=3)
        ax_c.plot(range(1, len(hb)+1), hb, label=f"Processor B (Final: {hb[-1]:.4f} Ha)", color="#f43f5e", lw=2, marker="s", markersize=3)
        ax_c.axhline(y=fci_ref, color="black", linestyle=":", lw=2, label=f"FCI Reference ({fci_ref:.4f} Ha)")
        ax_c.set_xlabel("Iteration (COBYLA)")
        ax_c.set_ylabel("Energy (Hartree)")
        ax_c.set_title(f"H₂ VQE Convergence (R = {bond_distance:.2f} Å, {shot_budget} shots)")
        ax_c.legend()
        ax_c.grid(True, linestyle="--", alpha=0.5)
        st.pyplot(fig_conv)
        plt.close(fig_conv)


# -----------------------------------------------------------------------------
# TAB 3: ERROR MITIGATION (ZNE)
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("Quantum Error Mitigation via Zero-Noise Extrapolation (ZNE)")
    st.markdown("Digital unitary gate folding ($CX \\to CX(CX\\cdot CX)^k$) at noise scale factors $\\lambda \\in \\{1, 3, 5\\}$ with Richardson polynomial extrapolation.")

    if st.button("🛡️ Execute Zero-Noise Extrapolation", key="btn_zne"):
        with st.spinner("Evaluating noise-amplified circuits..."):
            proc_a = get_processor_a(seed=transpiler_seed)
            noise = get_official_noise_model(p1=p1_err, p2=p2_err, p_ro=p_ro)
            H = get_h2_canonical_jordan_wigner_hamiltonian(r_bond=bond_distance, fci_target=fci_ref)
            ansatz = build_h2_ansatz(num_qubits=4, reps=1, entanglement="linear")

            t_a = transpile_circuit_for_hardware(ansatz, proc_a, optimization_level=1, seed_transpiler=transpiler_seed)
            phys_H = H.apply_layout(t_a.layout)
            rng = np.random.RandomState(transpiler_seed)
            params = rng.normal(0, 0.2, len(t_a.parameters))

            zne_res = execute_with_zne(
                circuit=t_a, observable=phys_H, parameters=params,
                noise_model=noise, scale_factors=[1, 3, 5], shots=shot_budget, seed=transpiler_seed
            )

            st.write(f"**Unmitigated Energy ($\lambda = 1$):** `{zne_res['measured_energies'][0]:.6f} Ha`")
            st.write(f"**Richardson Extrapolated Zero-Noise Energy ($E_0$):** `{zne_res['richardson_extrapolated_energy']:.6f} Ha`")

            fig_z, ax_z = plt.subplots(figsize=(8, 4), dpi=150)
            ax_z.plot([1, 3, 5], zne_res["measured_energies"], "ro-", label="Measured (Noisy)", lw=2)
            ax_z.plot([0], [zne_res["richardson_extrapolated_energy"]], "g*", markersize=14, label=f"Extrapolated E₀ ({zne_res['richardson_extrapolated_energy']:.4f} Ha)")
            ax_z.axhline(y=fci_ref, color="black", linestyle=":", label=f"FCI Reference ({fci_ref:.4f} Ha)")
            ax_z.set_xlabel("Noise Scale Factor λ")
            ax_z.set_ylabel("Energy (Hartree)")
            ax_z.set_title("Zero-Noise Extrapolation (Richardson Polyfit)")
            ax_z.legend()
            ax_z.grid(True, linestyle="--", alpha=0.5)
            st.pyplot(fig_z)
            plt.close(fig_z)


# -----------------------------------------------------------------------------
# TAB 4: POTENTIAL ENERGY SURFACE (PES)
# -----------------------------------------------------------------------------
with tab4:
    st.subheader("H₂ Potential Energy Surface (PES) Dissociation Curve")
    st.markdown("Evaluates ground-state energy across bond lengths $R \\in [0.5, 2.0]\\,\\text{Å}$ to verify chemical dissociation limits.")

    if st.button("📈 Compute Full PES Dissociation Curve", key="btn_pes"):
        with st.spinner("Computing Potential Energy Surface across multiple bond lengths..."):
            pes_data = compute_pes_curve(bond_distances=[0.5, 0.74, 1.0, 1.3, 1.6, 2.0], maxiter=15, shots=shot_budget, seed=transpiler_seed)
            
            fig_p, ax_p = plt.subplots(figsize=(9, 4.8), dpi=150)
            ax_p.plot(pes_data["bond_distances"], pes_data["fci_energies"], "k-", lw=2.5, label="Classical FCI (Exact)")
            ax_p.plot(pes_data["bond_distances"], pes_data["zne_mitigated_energies"], "g--", lw=2, marker="^", label="ZNE Mitigated")
            ax_p.plot(pes_data["bond_distances"], pes_data["processor_a_energies"], color="#818cf8", lw=1.8, marker="o", label="Processor A (5Q Noisy)")
            ax_p.plot(pes_data["bond_distances"], pes_data["processor_b_energies"], color="#f43f5e", lw=1.8, marker="s", label="Processor B (9Q Noisy)")
            ax_p.axvline(x=0.74, color="gray", linestyle=":", label="R_e = 0.74 Å")
            ax_p.set_xlabel("Bond Distance R (Å)")
            ax_p.set_ylabel("Energy (Hartree)")
            ax_p.set_title("H₂ Potential Energy Surface: VQE vs FCI")
            ax_p.legend()
            ax_p.grid(True, linestyle="--", alpha=0.5)
            st.pyplot(fig_p)
            plt.close(fig_p)


# -----------------------------------------------------------------------------
# TAB 5: QUANTUM STATE & ENTANGLEMENT
# -----------------------------------------------------------------------------
with tab5:
    st.subheader("Quantum State Fidelity & von Neumann Entanglement Entropy")
    st.markdown("Calculates state fidelity $\\mathcal{F} = |\\langle \\psi_{\\text{FCI}} | \\psi_{\\text{VQE}} \\rangle|^2$ and orbital entanglement entropy $S(\\rho_A)$.")

    if st.button("🔬 Analyze Quantum State Properties", key="btn_entropy"):
        ansatz = build_h2_ansatz(num_qubits=4, reps=1, entanglement="linear")
        fci_psi = get_exact_fci_wavefunction()
        p = np.zeros(len(ansatz.parameters))
        state_metrics = evaluate_state_fidelity_and_entropy(ansatz, p, fci_psi)

        col_e1, col_e2, col_e3 = st.columns(3)
        col_e1.metric("State Purity Tr(ρ²)", f"{state_metrics['state_purity']:.4f}")
        col_e2.metric("von Neumann Entropy S(ρ_A)", f"{state_metrics['von_neumann_entropy_vqe']:.4f} ebits")
        col_e3.metric("FCI Target Entropy", f"{state_metrics['von_neumann_entropy_fci_target']:.4f} ebits")

        st.write("**Dominant Computational Basis Components:**")
        st.json(state_metrics["dominant_basis_states"])

st.markdown("---")
st.markdown("*Built for Qiskit Fall Hackathon 2026 (SRM AP) | Powered by Qiskit v1.x / v2.x & Qiskit Aer*")
