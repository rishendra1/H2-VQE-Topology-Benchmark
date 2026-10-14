# H2-VQE-Topology-Benchmark
### $H_2$ VQE Algorithm-Hardware Co-Design & Architecture Benchmark
**Event:** Qiskit Fall Hackathon 2026 -- SRM University AP (SRM AP)  
**Track:** Track 1: Quantum Chemistry (Problem Statement PS-C1)  
**Target Reference:** Classical Full Configuration Interaction (FCI) = $-1.137000\text{ Hartree}$

---

## 🔬 Project Overview
This repository provides a modular, scalable, and reusable quantum chemistry benchmark architecture comparing the performance of Variational Quantum Eigensolvers (VQE) across two distinct physical superconducting quantum processor topologies:
1. **Processor A (5-Qubit Baseline):** Constrained branching tree coupling map (4 undirected edges).
2. **Processor B (9-Qubit Heavy-Hex):** Contemporary sparse heavy-hex architecture (12 undirected edges).

We evaluate molecular hydrogen ($H_2$ at equilibrium bond length $R = 0.74\text{ Å}$) mapped via the **Jordan-Wigner transformation** into a 4-qubit Hamiltonian observable, investigating how architectural routing overhead, SWAP inflation, and physical gate errors impact convergence to the classical FCI target of **$-1.137\text{ Hartree}$**.

---

## 🌟 Hackathon-Winning Research & Engineering Features
Built specifically to stand out at the **Qiskit Fall Hackathon 2026 (SRM AP)**:
- 💻 **Flagship PyCharm & Terminal Runner (`main.py`):** Single entry point that loads `.env`, executes the entire 9-step research pipeline, outputs formatted terminal tables via `rich`, and saves publication figures.
- ⚙️ **Zero-Friction PyCharm Integration (`.env`):** Fully customizable environment parameters (shots, iterations, noise rates, molecule selection) loaded automatically with `python-dotenv`.
- ⚡ **True Algorithm-Hardware Co-Design (`src/co_design.py`):** Custom native topology-matched ansätze that **completely eliminate 100% of physical SWAP gates (0 SWAPs)** and reduce CX count by **$71.4\%$**.
- 🧪 **Multi-Molecule Chemical Transferability (`src/molecules.py`):** Universal benchmark evaluating $H_2$, $HeH^+$, and $LiH$ across both physical hardware backends.
- ⚡ **QWC Measurement Grouping (`src/grouping.py`):** Groups 15 Pauli strings into 5 qubit-wise commuting cliques, slashing quantum circuit executions by **$66.7\%$** (3.00x shot speedup).
- 🛡️ **Quantum Error Mitigation (`src/mitigation.py`):** Unitary gate folding ($\lambda = 1, 3, 5$) with Richardson polynomial extrapolation (Zero-Noise Extrapolation).
- ⏱️ **Dynamical Decoupling (`src/dynamical_decoupling.py`):** CPMG ($X_\pi - X_\pi$) and XY4 ($X_\pi - Y_\pi - X_\pi - Y_\pi$) pulse train insertion on idle spectator qubits during routing delay.
- 📐 **Exact Quantum Gradients (`src/parameter_shift.py`):** Analytical Parameter-Shift Rule quantum gradient descent without finite-difference noise.
- 🔌 **Native IBM Hardware Basis Decompositions (`src/pulse_basis.py`):** Direct decomposition into IBM Falcon (`{rz, sx, x, ecr}`) and IBM Eagle (`{rz, sx, x, cz}`) pulse gate sets.
- ⚛️ **$Z_2$ Symmetry Tapering (`src/symmetry.py`):** Tapers 4 qubits down to 2 qubits using molecular spin-parity symmetries, slashing circuit depth by $74.5\%$.
- 📈 **Potential Energy Surface (PES) (`src/pes.py`):** Full molecular dissociation curve across $R \in [0.5, 2.0]\text{ Å}$.
- 🎯 **Multi-Optimizer Study (`src/optimizers.py`):** COBYLA vs Simultaneous Perturbation Stochastic Approximation (SPSA).
- 🧩 **Modular Reusable API (`src/benchmark_api.py`):** Object-oriented `VQETopologyBenchmark` class for plug-and-play evaluation on any molecule or hardware.

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
| **Z2 Tapered Subspace** | **2** | 1 | **13** | **22** | **2** | **0 SWAPs** | **-1.041240** | -1.137000 | $+0.095760$ |
| **Ideal Baseline (Noiseless)** | 5 | 4 | 48 | 85 | 21 | +9 CX | **-1.032685** | -1.137000 | $+0.104315$ |

---

## 📁 Repository Structure
```
H2-VQE-Topology-Benchmark/
├── .env                           # Active environment configuration
├── .env.example                   # Environment configuration template
├── README.md                      # Comprehensive project documentation
├── report.md                      # Formal technical report with in-depth analysis
├── main.py                        # Flagship PyCharm & Terminal Runner
├── cli_app.py                     # Interactive Rich Terminal Application
├── run_benchmark.py               # Master CLI orchestration script
├── test_submission.py             # 10-module master verification suite
├── main.ipynb                     # Fully executed Jupyter notebook with all outputs
├── requirements.txt               # Pinned Python dependencies
├── paper/                         # Scientific paper (paper.tex, paper.md, references.bib)
├── src/
│   ├── __init__.py                # Package initializer
│   ├── benchmark_api.py           # Reusable object-oriented benchmark API
│   ├── problem.py                 # H2 STO-3G Hamiltonian & FCI baseline
│   ├── processors.py              # GenericBackendV2 topologies & noise model
│   ├── routing.py                 # Ansatz compilation & transpilation
│   ├── metrics.py                 # Structural metrics & SWAP overhead analysis
│   ├── vqe_runner.py              # VQE execution engine with AerEstimator
│   ├── mitigation.py              # Zero-Noise Extrapolation (ZNE) & gate folding
│   ├── co_design.py               # Hardware-adapted native topology ansätze (0 SWAPs)
│   ├── grouping.py                # QWC measurement clique grouping (66.7% speedup)
│   ├── molecules.py               # Universal multi-molecule catalog (H2, HeH+, LiH)
│   ├── dynamical_decoupling.py    # CPMG & XY4 idle spectator qubit pulse sequences
│   ├── parameter_shift.py         # Exact analytical Parameter-Shift Rule gradients
│   ├── pulse_basis.py             # Native IBM hardware basis gates (ECR Falcon, CZ Eagle)
│   ├── symmetry.py                # Z2 spin-parity symmetry tapering (2Q reduction)
│   ├── theory.py                  # Graph Laplacian spectrum & algebraic connectivity (lambda_2)
│   ├── quantum_state.py           # State fidelity & von Neumann entanglement entropy
│   ├── mapper_engine.py           # Optimal subgraph layout permutation solver
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

## 🚀 How to Run in PyCharm & Terminal

### 1. PyCharm Direct Execution (Zero Setup)
1. Open PyCharm and select **Open** -> choose `H2-VQE-Topology-Benchmark`.
2. Configure your Python Interpreter (**Python 3.10 or 3.11**).
3. Right-click on **`main.py`** in the project explorer and click **Run 'main'** (or press `Shift + F10`).
4. Output, rich progress bars, ASCII tables, and convergence logs will display immediately in the PyCharm Run Console.

### 2. Terminal Execution
From PowerShell, Command Prompt, or bash:

```bash
# Clone the repository
git clone https://github.com/<your-username>/H2-VQE-Topology-Benchmark.git
cd H2-VQE-Topology-Benchmark

# Install dependencies
pip install -r requirements.txt

# Run the flagship benchmark
python main.py

# Or run fast verification (fewer iterations)
python main.py --quick

# Or open interactive terminal menu
python main.py --interactive

# Or run the master 10-module verification test suite
python test_submission.py
```

### 3. Environment Configuration (`.env`)
The project loads runtime settings from `.env` automatically via `python-dotenv`:
```ini
BOND_DISTANCE=0.74        # Interatomic distance in Angstroms
SHOTS=4096                # Quantum measurement shot budget
MAX_ITER=35               # Maximum VQE optimization iterations
OPTIMIZATION_LEVEL=1      # Qiskit transpiler level (Level 1)
SEED=42                   # Transpiler and simulation seed
P1_ERROR=0.001            # 1-qubit depolarizing error (0.10%)
P2_ERROR=0.005            # 2-qubit CX depolarizing error (0.50%)
PRO_ERROR=0.010           # Readout error (1.00%)
```

---

## 💡 Using the Reusable Python API in Your Own Code
```python
from src.benchmark_api import VQETopologyBenchmark

# Initialize benchmark for H2 at equilibrium (0.74 A)
bench = VQETopologyBenchmark(bond_distance=0.74)

# Transpile circuit across Processor A and Processor B
metrics = bench.transpile(optimization_level=1, ansatz_type="native")

# Execute noisy VQE optimization with ZNE error mitigation
results = bench.run_vqe(shots=4096, maxiter=30, apply_zne=True)

# View summary table
print(bench.get_summary_dataframe())
```

---
*Developed for Qiskit Fall Hackathon 2026 (SRM AP) | Track 1: Quantum Chemistry (PS-C1)*
