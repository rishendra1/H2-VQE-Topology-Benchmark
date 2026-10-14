# H2-VQE-Topology-Benchmark
### $H_2$ VQE Hardware Co-Design Project
**Track 1: Quantum Chemistry — Problem Statement PS-C1**  
**Target Reference:** Classical Full Configuration Interaction (FCI) = $-1.137000\text{ Hartree}$

---

## 🔬 Project Overview
This repository provides a complete, reproducible Python-based quantum chemistry workflow comparing the performance of Variational Quantum Eigensolvers (VQE) across two distinct physical quantum processor topologies:
1. **Processor A (5-Qubit Baseline):** Constrained branching tree coupling map (4 undirected edges).
2. **Processor B (9-Qubit Heavy-Hex):** Contemporary sparse heavy-hex architecture (12 undirected edges).

We evaluate diatomic hydrogen ($H_2$ at equilibrium bond distance $R = 0.74\text{ Å}$) mapped via the **Jordan-Wigner transformation** into a 4-qubit Hamiltonian observable, investigating how architectural routing overhead, SWAP inflation, and physical gate errors impact convergence to the classical FCI ground-state target of **$-1.137\text{ Hartree}$**.

---

## ⚙️ Standardized Compilation & Noise Specifications
All experiments adhere strictly to official hackathon compilation parameters and synthetic noise profiles:

| Parameter | Specification | Notes |
|:---|:---:|:---|
| **Transpiler Optimization Level** | `1` | Official compilation level |
| **Transpiler Random Seed** | `42` | Deterministic physical qubit mapping & routing |
| **Measurement Budget** | `4096` shots | Shot-based Monte Carlo sampling |
| **1-Qubit Depolarizing Error** | $0.1\%$ ($p = 0.001$) | Applied to all single-qubit gates (`rz`, `sx`, `x`, `h`) |
| **2-Qubit CX Depolarizing Error** | $0.5\%$ ($p = 0.005$) | Applied to entangling gates (`cx`) |
| **Readout Error** | $1.0\%$ ($p = 0.010$) | Symmetric assignment transition error |

---

## 📊 Benchmark Summary Results

| Architecture / Metric | Qubits | Coupling Edges | Transpiled Depth | Total Gates | CX Gates | SWAP Overhead (CX) | Final Energy (Ha) | FCI Target (Ha) | Energy Error (Ha) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Processor A (5Q Baseline)** | 5 | 4 | **48** | **85** | **21** | **9** | **-0.922449** | -1.137000 | $+0.214551$ |
| **Processor B (9Q Heavy-Hex)** | 9 | 12 | **51** | **88** | **24** | **12** | **-0.880541** | -1.137000 | $+0.256459$ |
| **Ideal Baseline (Noiseless)** | 5 | 4 | 48 | 85 | 21 | 9 | **-1.032685** | -1.137000 | $+0.104315$ |

### Key Architectural Findings:
1. **Routing & SWAP Overhead:** Processor B's heavy-hex sparsity requires routing across intermediary bridge qubits, inflating CX gate counts from 12 (uncompiled) to 24 (compiled, $+100\%$ inflation), compared to 21 on Processor A.
2. **Noise Penalty:** Because 2-qubit CX gates carry a 5× higher error rate ($0.5\%$), the 3 additional CX gates and depth dilation on Processor B lead to higher error accumulation ($+0.2565\text{ Ha}$ offset vs $+0.2146\text{ Ha}$ on Processor A).
3. **Co-Design Takeaway:** For small molecules ($H_2$, 4 qubits), compact low-diameter subgraphs outperform distributed sparse layouts. Matching ansatz entanglement to the hardware coupling map is vital for NISQ utility.

---

## 📁 Repository Structure
```
H2-VQE-Topology-Benchmark/
├── README.md                      # Project documentation and quickstart
├── report.md                      # In-depth technical report and architectural analysis
├── main.ipynb                     # End-to-end executable orchestration notebook
├── run_benchmark.py               # Automated CLI benchmark runner script
├── requirements.txt               # Pinned Python dependencies
├── src/
│   ├── __init__.py                # Package initializer
│   ├── problem.py                 # H2 molecular geometry, STO-3G Hamiltonian & FCI baseline
│   ├── processors.py              # GenericBackendV2 definitions & synthetic noise model
│   ├── routing.py                 # Ansatz construction & hardware transpilation
│   ├── metrics.py                 # Circuit depth, CX count, and SWAP routing overhead extraction
│   ├── vqe_runner.py              # COBYLA optimization loop with AerEstimator
│   └── visualization.py          # Convergence curves, bar charts, and topology plots
├── processors/
│   └── __init__.py                # Top-level module alias for processor imports
└── results/
    ├── figures/                   # High-resolution benchmark plots
    │   ├── energy_convergence.png
    │   ├── circuit_metrics_comparison.png
    │   └── hardware_topologies.png
    └── tables/                    # CSV, JSON, and Markdown summary tables
        ├── benchmark_summary.md
        ├── benchmark_summary.csv
        └── raw_benchmark_results.json
```

---

## 🚀 Quickstart & Execution

### 1. Installation
Clone the repository and install dependencies in your virtual environment:
```bash
git clone https://github.com/<your-username>/H2-VQE-Topology-Benchmark.git
cd H2-VQE-Topology-Benchmark
pip install -r requirements.txt
```

### 2. Run the Complete Benchmark Suite (CLI)
To run the automated benchmark and generate all figures and tables:
```bash
python run_benchmark.py
```

### 3. Interactive Jupyter Notebook
Launch Jupyter to explore the step-by-step workflow with pre-evaluated outputs:
```bash
jupyter notebook main.ipynb
```

---

## 📈 Visualizations Generated
The benchmark suite automatically produces three publication-ready figures in `results/figures/`:
1. `energy_convergence.png`: VQE optimization convergence curves across iterations for Processor A, Processor B, and the Ideal baseline, alongside the classical FCI reference line ($-1.137\text{ Ha}$) and the chemical accuracy band ($\pm 1.6\text{ mHa}$).
2. `circuit_metrics_comparison.png`: Comparative bar charts showing circuit depth, total gate count, CX count, and physical SWAP overhead between Processor A and Processor B.
3. `hardware_topologies.png`: Network graph visualizations comparing Processor A's 5-qubit branching tree against Processor B's 9-qubit heavy-hex sparse lattice.

---

## 📚 References
1. Peruzzo, A. et al. *A variational eigenvalue solver on a photonic quantum processor.* Nature Communications 5, 4213 (2014).
2. Kandala, A. et al. *Hardware-efficient variational quantum eigensolver for small molecules and quantum magnets.* Nature 549, 242–246 (2017).
3. Qiskit Development Team. *Qiskit: An Open-source Framework for Quantum Computing* (2024).
