# H2 VQE Hardware Co-Design Benchmark Summary Table

| Architecture / Metric      |   Qubits |   Coupling Edges | Noise Model                                  |   Transpiled Depth |   Total Gates |   CX Gates |   SWAP Overhead (CX) |   Final Energy (Ha) |   FCI Target (Ha) |   Energy Error (Ha) |   Error (kcal/mol) |
|----------------------------|----------|------------------|----------------------------------------------|--------------------|---------------|------------|----------------------|---------------------|-------------------|---------------------|--------------------|
| Processor A (5Q Baseline)  |        5 |                4 | Official Synthetic (0.1% 1Q, 0.5% CX, 1% RO) |                 48 |            85 |         21 |                    9 |           -0.922449 |            -1.137 |            0.214551 |             134.63 |
| Processor B (9Q Heavy-Hex) |        9 |               12 | Official Synthetic (0.1% 1Q, 0.5% CX, 1% RO) |                 51 |            88 |         24 |                   12 |           -0.934318 |            -1.137 |            0.202682 |             127.18 |
| Ideal Baseline (Noiseless) |        5 |                4 | None (Noiseless 4096 shots)                  |                 48 |            85 |         21 |                    9 |           -1.03269  |            -1.137 |            0.104315 |              65.46 |

*Note: Chemical accuracy threshold is 1 kcal/mol ≈ 0.001594 Hartree. Compilation constraints: optimization_level=1, seed=42, shots=4096.*
