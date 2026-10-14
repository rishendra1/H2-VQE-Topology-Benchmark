"""Hardware Topology and Noise Modeling Module.

Defines:
1. Processor A: 5-qubit constrained baseline architecture (linear/branching coupling map).
2. Processor B: 9-qubit heavy-hex-inspired sparse architecture (12 coupling edges).
3. Official synthetic noise model:
   - 1Q depolarizing error: 0.1% (p = 0.001)
   - 2Q CX depolarizing error: 0.5% (p = 0.005)
   - Readout error: 1.0% (p = 0.01)
"""

from typing import List, Tuple, Dict, Any
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error, ReadoutError


# Official synthetic noise parameters
P_1Q_DEPOLARIZING: float = 0.001  # 0.1%
P_2Q_DEPOLARIZING: float = 0.005  # 0.5%
P_READOUT_ERROR: float = 0.010    # 1.0%

# Processor A: 5-qubit baseline coupling topology (branching tree)
# Qubits: 0 - 1 - 2
#             |
#             3 - 4
PROCESSOR_A_EDGES: List[List[int]] = [
    [0, 1], [1, 2], [1, 3], [3, 4]
]

# Processor B: 9-qubit heavy-hex-inspired contemporary sparse topology (12 edges)
# Arranged with hexagonal vertices and connecting bridge qubits:
# Row 0:  0 ---- (1) ---- 2
#         |        |       |
# Row 1: (3) ---- 4 ---- (5)
#         |        |       |
# Row 2:  6 ---- (7) ---- 8
PROCESSOR_B_EDGES: List[List[int]] = [
    [0, 1], [1, 2],
    [0, 3], [2, 5],
    [3, 4], [4, 5],
    [1, 4], [4, 7],
    [3, 6], [5, 8],
    [6, 7], [7, 8]
]


def make_bidirectional(edges: List[List[int]]) -> List[List[int]]:
    """Generates bidirectional coupling map edges from undirected edge list."""
    bi_edges = set()
    for u, v in edges:
        bi_edges.add((u, v))
        bi_edges.add((v, u))
    return sorted([list(e) for e in bi_edges])


def get_official_noise_model(
    p1: float = P_1Q_DEPOLARIZING,
    p2: float = P_2Q_DEPOLARIZING,
    p_ro: float = P_READOUT_ERROR
) -> NoiseModel:
    """Constructs the official synthetic NoiseModel.

    Args:
        p1: 1-qubit depolarizing error rate (default: 0.001).
        p2: 2-qubit CX depolarizing error rate (default: 0.005).
        p_ro: Readout assignment error rate (default: 0.01).

    Returns:
        NoiseModel: Configured Qiskit Aer noise model.
    """
    noise_model = NoiseModel()

    # 1-qubit depolarizing error for single-qubit gates
    err_1q = depolarizing_error(p1, 1)
    noise_model.add_all_qubit_quantum_error(err_1q, ["rz", "sx", "x", "h"])

    # 2-qubit depolarizing error for entangling CX gates
    err_2q = depolarizing_error(p2, 2)
    noise_model.add_all_qubit_quantum_error(err_2q, ["cx", "cz"])

    # Symmetric Readout error: P(0|1) = P(1|0) = p_ro
    ro_matrix = [
        [1.0 - p_ro, p_ro],
        [p_ro, 1.0 - p_ro]
    ]
    readout_err = ReadoutError(ro_matrix)
    noise_model.add_all_qubit_readout_error(readout_err)

    return noise_model


def get_processor_a(seed: int = 42, bidirectional: bool = True) -> GenericBackendV2:
    """Instantiates Processor A (5-qubit baseline architecture).

    Args:
        seed: Random seed for reproducible calibration parameters (default: 42).
        bidirectional: Whether to symmetrize the coupling map (default: True).

    Returns:
        GenericBackendV2: Processor A backend.
    """
    edges = make_bidirectional(PROCESSOR_A_EDGES) if bidirectional else PROCESSOR_A_EDGES
    backend = GenericBackendV2(
        num_qubits=5,
        coupling_map=edges,
        seed=seed
    )
    return backend


def get_processor_b(seed: int = 42, bidirectional: bool = True) -> GenericBackendV2:
    """Instantiates Processor B (9-qubit heavy-hex sparse architecture).

    Args:
        seed: Random seed for reproducible calibration parameters (default: 42).
        bidirectional: Whether to symmetrize the coupling map (default: True).

    Returns:
        GenericBackendV2: Processor B backend.
    """
    edges = make_bidirectional(PROCESSOR_B_EDGES) if bidirectional else PROCESSOR_B_EDGES
    backend = GenericBackendV2(
        num_qubits=9,
        coupling_map=edges,
        seed=seed
    )
    return backend


def get_noisy_simulator(
    backend: GenericBackendV2,
    noise_model: NoiseModel = None
) -> AerSimulator:
    """Creates an AerSimulator mimicking the specified hardware processor under noise.

    Args:
        backend: Target hardware backend.
        noise_model: NoiseModel to apply. If None, uses the official synthetic noise model.

    Returns:
        AerSimulator: Configured noisy simulator with target coupling map and noise.
    """
    if noise_model is None:
        noise_model = get_official_noise_model()

    sim = AerSimulator.from_backend(backend)
    sim.set_options(noise_model=noise_model)
    return sim


def get_realistic_thermal_noise_model(
    t1_us: float = 100.0,
    t2_us: float = 80.0,
    gate_time_1q_ns: float = 35.0,
    gate_time_2q_ns: float = 300.0,
    p_ro: float = P_READOUT_ERROR
) -> NoiseModel:
    """Builds a physics-accurate thermal relaxation and dephasing noise model.

    Models genuine superconducting transmon decoherence (T1 longitudinal relaxation,
    T2 transverse dephasing, and finite pulse duration overheads).

    Args:
        t1_us: Longitudinal relaxation time T1 in microseconds (default: 100.0 us).
        t2_us: Transverse dephasing time T2 in microseconds (default: 80.0 us).
        gate_time_1q_ns: Single-qubit pulse duration in nanoseconds (default: 35.0 ns).
        gate_time_2q_ns: Two-qubit cross-resonance duration in nanoseconds (default: 300.0 ns).
        p_ro: Readout assignment error probability.

    Returns:
        NoiseModel: Calibrated thermal relaxation noise model.
    """
    from qiskit_aer.noise import thermal_relaxation_error

    noise_model = NoiseModel()
    t_1q = gate_time_1q_ns / 1000.0  # to microseconds
    t_2q = gate_time_2q_ns / 1000.0  # to microseconds

    err_1q = thermal_relaxation_error(t1_us, t2_us, t_1q)
    err_2q_single = thermal_relaxation_error(t1_us, t2_us, t_2q)
    err_2q = err_2q_single.tensor(err_2q_single)

    noise_model.add_all_qubit_quantum_error(err_1q, ["rz", "sx", "x", "h"])
    noise_model.add_all_qubit_quantum_error(err_2q, ["cx", "cz"])

    ro_matrix = [[1.0 - p_ro, p_ro], [p_ro, 1.0 - p_ro]]
    noise_model.add_all_qubit_readout_error(ReadoutError(ro_matrix))

    return noise_model


def get_cloud_runtime_backend(token: str = None, backend_name: str = None) -> Tuple[Any, bool]:
    """Connects to real IBM Quantum cloud QPUs via Qiskit Runtime if credentials are available.

    Falls back cleanly to local simulation if no token is provided.

    Args:
        token: Optional IBM Quantum API token (defaults to IBM_QUANTUM_TOKEN env var).
        backend_name: Optional QPU name (e.g. 'ibm_brisbane', 'ibm_kyoto').

    Returns:
        Tuple[Any, bool]: (backend_instance, is_live_cloud_backend)
    """
    import os
    resolved_token = token or os.getenv("IBM_QUANTUM_TOKEN", "").strip()

    if not resolved_token:
        # Default to local Processor A simulation
        return get_processor_a(), False

    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
        service = QiskitRuntimeService(channel="ibm_quantum", token=resolved_token)
        if backend_name:
            backend = service.backend(backend_name)
        else:
            backend = service.least_busy(operational=True, simulator=False)
        return backend, True
    except Exception as exc:
        print(f"[*] Cloud connection notice ({type(exc).__name__}): Defaulting to local calibrated GenericBackendV2.")
        return get_processor_a(), False


if __name__ == "__main__":
    proc_a = get_processor_a()
    proc_b = get_processor_b()
    noise = get_official_noise_model()
    thermal = get_realistic_thermal_noise_model()

    print("=== Processor A (5-Qubit Baseline) ===")
    print(f"Num qubits: {proc_a.num_qubits}")
    print(f"Coupling edges (directed): {len(proc_a.coupling_map.get_edges())}")
    print(f"Base undirected edges: {len(PROCESSOR_A_EDGES)}")

    print("\n=== Processor B (9-Qubit Heavy-Hex) ===")
    print(f"Num qubits: {proc_b.num_qubits}")
    print(f"Coupling edges (directed): {len(proc_b.coupling_map.get_edges())}")
    print(f"Base undirected edges: {len(PROCESSOR_B_EDGES)}")

    print("\n=== Official Synthetic Noise Model ===")
    print(noise)
    print("\n=== Realistic Thermal Decoherence Model (T1=100us, T2=80us) ===")
    print(thermal)
    print("\nProcessor initialization passed successfully!")
