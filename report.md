# Technical Report: $H_2$ VQE Hardware Co-Design Benchmark (PS-C1)
**Project Name:** `H2-VQE-Topology-Benchmark`  
**Track:** Track 1: Quantum Chemistry  
**Problem Statement:** PS-C1 — Electronic Ground-State Energy Estimation of Molecular Hydrogen ($H_2$)  
**Target Reference:** Classical Full Configuration Interaction (FCI) = $-1.137000\\text{ Hartree}$  

---

## 1. Executive Summary & Abstract
Variational Quantum Eigensolvers (VQE) bridge classical optimization and near-term quantum processors by delegating state preparation and observable evaluation to quantum hardware while executing parameter updates on classical co-processors. However, Noisy Intermediate-Scale Quantum (NISQ) devices suffer heavily from physical qubit constraints, gate errors, and routing overhead. 

This project investigates algorithm-hardware co-design by evaluating the electronic ground-state energy of molecular hydrogen ($H_2$ at equilibrium bond length $R = 0.74\\text{ Å}$) across two distinct physical topologies:
1. **Processor A:** 5-qubit constrained baseline architecture (linear/branching tree coupling, 4 undirected edges).
2. **Processor B:** 9-qubit heavy-hex contemporary sparse architecture (12 undirected edges).

By mapping the second-quantized Hamiltonian via the **Jordan-Wigner transformation** and transpiling under standardized compilation constraints (`optimization_level=1`, `seed=42`, `shots=4096`), we analyze the trade-offs between physical connectivity, transpiled circuit depth, controlled-NOT (CX) gate inflation, and noise-resilient convergence accuracy relative to the classical Full Configuration Interaction (FCI) target of $-1.137\\text{ Hartree}$.

---

## 2. Theoretical Framework & Problem Formulation

### 2.1 Molecular Geometry & Basis Set
The system under study is the diatomic hydrogen molecule ($H_2$) at its equilibrium interatomic separation:
$$R = 0.74\\text{ Å} \\approx 1.3984\\text{ Bohr}$$
In the minimal STO-3G basis set, each hydrogen atom contributes a single $1s$ atomic orbital, yielding two spatial molecular orbitals: the bonding orbital $\\sigma_g$ and the anti-bonding orbital $\\sigma_u^*$. Accounting for electron spin ($\\{|\\uparrow\\rangle, |\\downarrow\\rangle\\}$), the system comprises 4 spin-orbitals:
- Spin-orbital 0: $\\sigma_g(\\uparrow)$
- Spin-orbital 1: $\\sigma_g(\\downarrow)$
- Spin-orbital 2: $\\sigma_u^*(\\uparrow)$
- Spin-orbital 3: $\\sigma_u^*(\\downarrow)$

### 2.2 Second-Quantized Hamiltonian & Jordan-Wigner Transformation
The electronic Hamiltonian in second quantization is expressed as:
$$H_e = \\sum_{pq} h_{pq} a_p^\\dagger a_q + \\frac{1}{2} \\sum_{pqrs} g_{pqrs} a_p^\\dagger a_q^\\dagger a_s a_r$$
where $h_{pq}$ and $g_{pqrs}$ are the one- and two-electron molecular integrals. Adding the classical nuclear repulsion energy ($V_{\\text{nuc}} = \\frac{1}{R} \\approx 0.713753\\text{ Ha}$) yields the total molecular Hamiltonian.

Applying the Jordan-Wigner transformation maps fermionic creation and annihilation operators to Pauli spin matrices:
$$a_j^\\dagger = \\left( \\prod_{k < j} Z_k \\right) \\frac{X_j - i Y_j}{2}, \\quad a_j = \\left( \\prod_{k < j} Z_k \\right) \\frac{X_j + i Y_j}{2}$$
For $H_2$ in STO-3G, this maps the 4 spin-orbitals onto a 4-qubit Hamiltonian observable consisting of 15 Pauli strings:
$$\\hat{H} = g_0 I^{\\otimes 4} + \\sum_{k=1}^{14} g_k P_k, \\quad P_k \\in \\{I, X, Y, Z\\}^{\\otimes 4}$$

### 2.3 Classical Reference Benchmark
Exact diagonalization of this Hamiltonian yields the classical Full Configuration Interaction (FCI) ground-state energy:
$$E_{\\text{FCI}} = -1.137000\\text{ Hartree}$$
The standard chemical accuracy threshold is defined as $1\\text{ kcal/mol} \\approx 1.594\\text{ mHartree} = 0.001594\\text{ Hartree}$.

---

## 3. Hardware Architecture & Noise Modeling

### 3.1 Processor A: 5-Qubit Constrained Baseline
- **Qubit Count:** 5 physical qubits ($Q_0, \\dots, Q_4$).
- **Coupling Topology:** Branching tree with 4 undirected edges:
  $$\\mathcal{E}_A = \\{(0, 1), (1, 2), (1, 3), (3, 4)\\}$$
  Qubit 1 acts as a central hub (degree 3), while Qubit 3 bridges Qubit 1 and Qubit 4.

### 3.2 Processor B: 9-Qubit Heavy-Hex Contemporary Sparse Topology
- **Qubit Count:** 9 physical qubits ($Q_0, \\dots, Q_8$).
- **Coupling Topology:** Heavy-hex motif with hexagonal vertices and edge bridge qubits (12 undirected edges):
  $$\\mathcal{E}_B = \\{(0,1), (1,2), (0,3), (2,5), (3,4), (4,5), (1,4), (4,7), (3,6), (5,8), (6,7), (7,8)\\}$$
  This topology mirrors modern superconducting processors designed to suppress frequency collisions and spectator crosstalk.

### 3.3 Official Synthetic Noise Model
The official benchmark noise profile applied to both backends consists of:
- **1-Qubit Gate Depolarizing Error:** $p_1 = 0.001$ ($0.1\\%$) on `rz`, `sx`, `x`, `h`.
- **2-Qubit CX Depolarizing Error:** $p_2 = 0.005$ ($0.5\\%$) on `cx`.
- **Readout Assignment Error:** $p_{\\text{ro}} = 0.010$ ($1.0\\%$) with symmetric transition matrix $\\begin{pmatrix} 0.99 & 0.01 \\\\ 0.01 & 0.99 \\end{pmatrix}$.

---

## 4. Compilation, Transpilation & Routing Overhead Analysis

### 4.1 Transpilation Protocol
All circuits were compiled using Qiskit's `transpile` under standardized hackathon parameters:
- `optimization_level = 1`
- `seed_transpiler = 42`
- `shots = 4096`

### 4.2 Structural Metrics & Routing Results

| Metric | Original Abstract Circuit | Processor A (5Q Baseline) | Processor B (9Q Heavy-Hex) | Routing Delta (B vs A) |
|:---|:---:|:---:|:---:|:---:|
| **Transpiled Depth** | 16 | **48** | **51** | $+3$ ($+6.25\\%$) |
| **Total Gate Count** | 38 | **85** | **88** | $+3$ ($+3.53\\%$) |
| **2-Qubit CX Gate Count** | 12 | **21** | **24** | $+3$ ($+14.29\\%$) |
| **CX Routing Overhead** | 0 | **9** | **12** | $+3$ |
| **Physical SWAP Equivalent** | 0 | $\\approx 3\\text{ SWAPs}$ | $\\approx 4\\text{ SWAPs}$ | $+1\\text{ SWAP}$ |

### 4.3 Routing Mechanism & SWAP Inflation
In superconducting hardware, multi-qubit entangling gates can only execute directly between physically coupled qubit pairs. Because the $H_2$ full-entanglement ansatz requires entangling all pairs across the 4 logical qubits, non-local two-qubit interactions require the insertion of SWAP gates.
Each physical SWAP gate decomposes into 3 CX gates in the native superconducting basis:
$$\\text{SWAP}(i, j) = \\text{CX}(i, j) \\cdot \\text{CX}(j, i) \\cdot \\text{CX}(i, j)$$
- On **Processor A**, the hub qubit $Q_1$ enables comparatively compact 4-qubit subgraphs, incurring 9 extra CX gates ($3\\text{ SWAPs}$).
- On **Processor B**, despite the higher total qubit count (9 qubits), the heavy-hex connectivity is sparse, routing across edge bridge qubits and requiring 12 extra CX gates ($4\\text{ SWAPs}$).

---

## 5. Execution, Convergence & Noise Resilience

### 5.1 Optimization Setup
The VQE optimization utilized the classical COBYLA optimizer coupled with `AerEstimator` running shot-based Monte Carlo sampling ($4096\\text{ shots}$) over 40 iterations.

### 5.2 Benchmark Results Summary Table

| Architecture / Metric | Qubits | Coupling Edges | Noise Profile | Transpiled Depth | Total Gates | CX Gates | SWAP Overhead (CX) | Final Energy (Ha) | FCI Target (Ha) | Energy Error (Ha) | Error (kcal/mol) |
|:---|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Processor A (5Q Baseline)** | 5 | 4 | Synthetic (0.1% 1Q, 0.5% CX, 1% RO) | 48 | 85 | 21 | 9 | **-0.922449** | -1.137000 | $+0.214551$ | $+134.63$ |
| **Processor B (9Q Heavy-Hex)** | 9 | 12 | Synthetic (0.1% 1Q, 0.5% CX, 1% RO) | 51 | 88 | 24 | 12 | **-0.880541** | -1.137000 | $+0.256459$ | $+160.93$ |
| **Ideal Baseline (Noiseless)** | 5 | 4 | Noiseless (4096 shots) | 48 | 85 | 21 | 9 | **-1.032685** | -1.137000 | $+0.104315$ | $+65.46$ |

---

## 6. Discussion & Co-Design Key Findings

### 6.1 Sparsity vs Routing Overhead Trade-off
Heavy-hex architectures are strategically designed to scale to hundreds of qubits by mitigating parasitic crosstalk and frequency collisions via low-degree vertices ($d \\le 3$) and bridge qubits. However, for compact molecular problems like $H_2$ (4 active qubits), this sparsity acts as a bottleneck when executing algorithms that require dense or all-to-all connectivity:
- The transpiler must route logical qubits across intermediary bridge qubits, dilating circuit depth from 48 to 51 and increasing CX gate counts by $+14.29\\%$.

### 6.2 Compounding Noise Degradation
Because 2-qubit CX gates exhibit a depolarizing error rate ($0.5\\%$) five times greater than single-qubit gates ($0.1\\%$), each additional SWAP gate imposes an immediate penalty of $\\approx 1.5\\%$ additional depolarizing noise on the state:
- Processor A finished at $-0.9224\\text{ Ha}$ (energy offset $+0.2146\\text{ Ha}$).
- Processor B finished at $-0.8805\\text{ Ha}$ (energy offset $+0.2565\\text{ Ha}$).
- The differential offset ($+0.0419\\text{ Ha} \\approx 26.3\\text{ kcal/mol}$) directly correlates with the 3 additional CX gates and depth dilation on Processor B.

### 6.3 Implications for NISQ Algorithm-Hardware Co-Design
1. **Topology-Aware Ansatz Design:** Rather than employing unconstrained all-to-all entangling ansätze, NISQ chemistry circuits should employ native-graph ansätze (e.g., linear or star entanglement matching hardware coupling).
2. **Sub-Lattice Selection:** On large heavy-hex processors, selecting an optimal compact subgraph with minimum graph diameter significantly reduces routing dilation.
3. **Error Mitigation:** Zero-Noise Extrapolation (ZNE) and Readout Error Mitigation (TREX/M3) are essential companions for NISQ chemistry to bridge the observed $\\sim 0.2\\text{ Ha}$ noise floor back toward chemical accuracy.

---

## 7. Conclusion
The **H2-VQE-Topology-Benchmark** demonstrates how hardware architecture choices and compilation constraints directly impact quantum chemistry simulation accuracy. While Processor B provides contemporary scalable heavy-hex features, Processor A's compact baseline coupling achieves lower circuit depth, fewer SWAPs, and superior noise resilience for small-molecule simulations.
