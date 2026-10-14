# H2-VQE-Topology-Benchmark
### $H_2$ VQE Algorithm-Hardware Co-Design & Architecture Benchmark
**Track 1: Quantum Chemistry — Problem Statement PS-C1**  
**Target Reference:** Classical Full Configuration Interaction (FCI) = $-1.137000\text{ Hartree}$

---

## 🔬 Project Overview
This repository provides an advanced, publication-grade quantum chemistry benchmark comparing the performance of Variational Quantum Eigensolvers (VQE) across two distinct physical superconducting quantum processor topologies:
1. **Processor A (5-Qubit Baseline):** Constrained branching tree coupling map (4 undirected edges).
2. **Processor B (9-Qubit Heavy-Hex):** Contemporary sparse heavy-hex architecture (12 undirected edges).

We evaluate molecular hydrogen ($H_2$ at equilibrium bond length $R = 0.74\text{ Å}$) mapped via the **Jordan-Wigner transformation** into a 4-qubit Hamiltonian observable, investigating how architectural routing overhead, SWAP inflation, and physical gate errors impact convergence to the classical FCI target of **$-1.137\text{ Hartree}$**.

---

## 🌟 Hackathon-Level Advanced Enhancements
In addition to the baseline problem specifications, this project implements 5 high-impact extensions:
- 🛡️ **Quantum Error Mitigation:** Zero-Noise Extrapolation (ZNE) with digital unitary gate folding ($\lambda = 1, 3, 5$) and Richardson polynomial extrapolation.
- ⚡ **True Algorithm-Hardware Co-Design:** Custom native topology-matched ansätze that **eliminate 100% of physical SWAP routing overhead** and reduce CX gate counts by **up to 71%**.
- 📈 **Potential Energy Surface (PES):** Complete molecular dissociation curve ($R \in [0.5, 2.0]\text{ Å}$) capturing binding energy and asymptotic dissociation limits.
- 🎯 **Multi-Optimizer Study:** Side-by-side performance and noise-tolerance analysis of **COBYLA vs. SPSA** under $4096\text{ shots}$.
- 🌐 **Interactive Web Dashboard:** Standalone browser-accessible `dashboard.html` for zero-install visual inspection.

---

## ⚙️ Standardized Compilation & Noise Specifications

| Parameter | Specification | Notes |
|:---|:---:|:---|
| **Transpiler Optimization Level** | `1` | Official compilation level |
| **Transpiler Random Seed** | `42` | Deterministic physical qubit mapping & routing |
| **Measurement Budget** | `4096` shots | Shot-based Monte Carlo sampling |
| **1-Qubit Depolarizing Error** | $0.1\%$ ($p = 0.001$) | Applied to all single-qubit gates (`rz`, `sx`, `x`, `h`) |
| **2-Qubit CX Depolarizing Error** | $0.5\%$ ($p = 0.005$) | Applied to entangling gates (`cx`) |
| **Readout Error** | $1.0\%$ ($p = 0.010$) | Symmetric assignment transition error |

---

## 📊 Comprehensive Benchmark Results

| Architecture / Configuration | Qubits | Coupling Edges | Transpiled Depth | Total Gates | CX Gates | SWAP Overhead | Final Energy ($\text{Ha}$) | FCI Reference ($\text{Ha}$) | Energy Error ($\text{Ha}$) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Processor A (5Q Naive)** | 5 | 4 | 48 | 85 | 21 | +9 CX (~3 SWAPs) | **-0.922449** | -1.137000 | $+0.214551$ |
| **Processor B (9Q Heavy-Hex)** | 9 | 12 | 51 | 88 | 24 | +12 CX (~4 SWAPs) | **-0.880541** | -1.137000 | $+0.256459$ |
| **Co-Designed Native (Proc A)** | 5 | 4 | **23** | **44** | **6** | **0 SWAPs** | **-0.961204** | -1.137000 | $+0.175796$ |
| **Ideal Baseline (Noiseless)** | 5 | 4 | 48 | 85 | 21 | +9 CX | **-1.032685** | -1.137000 | $+0.104315$ |

---

## 📁 Repository Structure
```
H2-VQE-Topology-Benchmark/
├── README.md                      # Comprehensive project documentation
├── report.md                      # Formal technical report with in-depth analysis
├── dashboard.html                 # Interactive browser-based dashboard
├── main.ipynb                     # Fully executed Jupyter notebook with all outputs
├── run_benchmark.py               # Master CLI execution script
├── test_submission.py             # Automated unit & metrics verification suite
├── requirements.txt               # Pinned Python dependencies
├── src/
│   ├── __init__.py                # Package initializer
│   ├── problem.py                 # H2 STO-3G Hamiltonian & FCI baseline
│   ├── processors.py              # GenericBackendV2 topologies & noise model
│   ├── routing.py                 # Ansatz compilation & transpilation
│   ├── metrics.py                 # Structural metrics & SWAP overhead analysis
│   ├── vqe_runner.py              # VQE execution engine with AerEstimator
│   ├── mitigation.py              # Zero-Noise Extrapolation (ZNE) & gate folding
│   ├── co_design.py               # Hardware-adapted native topology ansätze
│   ├── pes.py                     # H2 Potential Energy Surface dissociation curve
│   ├── optimizers.py              # Multi-optimizer comparison (COBYLA vs SPSA)
│   └── visualization.py          # Publication plotting & table generation
├── processors/
│   └── __init__.py                # Module alias for top-level imports
└── results/
    ├── figures/                   # 5 publication-ready high-res figures
    │   ├── energy_convergence.png
    │   ├── circuit_metrics_comparison.png
    │   ├── hardware_topologies.png
    │   ├── h2_potential_energy_surface.png
    │   └── optimizer_comparison.png
    └── tables/                    # Summary data files
        ├── benchmark_summary.md
        ├── benchmark_summary.csv
        └── raw_benchmark_results.json
```

---

## 🚀 Quickstart & Execution

### 1. Installation
```bash
git clone https://github.com/<your-username>/H2-VQE-Topology-Benchmark.git
cd H2-VQE-Topology-Benchmark
pip install -r requirements.txt
```

### 2. Run Complete Benchmark Suite (CLI)
Executes all 5 phases, performs ZNE, co-design, PES, and generates all figures:
```bash
python run_benchmark.py
```

### 3. Run Automated Verification Test Suite
```bash
python test_submission.py
```

### 4. Interactive Jupyter Notebook
```bash
jupyter notebook main.ipynb
```

### 5. Interactive Web Dashboard
Simply double-click or open [dashboard.html](file:///c:/Users/rishe/Desktop/H2-VQE-Topology-Benchmark/dashboard.html) in any modern browser!

---

## 🖼️ Publication Figures Generated
All figures are stored in `results/figures/`:
1. `energy_convergence.png`: VQE optimization curves across iterations against the classical FCI reference.
2. `circuit_metrics_comparison.png`: Bar chart of transpiled depth, gate counts, and SWAP overhead.
3. `hardware_topologies.png`: Network graph layouts of Processor A vs. Processor B.
4. `h2_potential_energy_surface.png`: Complete $H_2$ dissociation curve (VQE vs FCI vs ZNE-mitigated).
5. `optimizer_comparison.png`: Convergence stability comparison of COBYLA vs SPSA under shot noise.
