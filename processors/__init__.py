"""Processors alias package to support both 'processors' and 'src.processors' imports."""

from src.processors import (
    PROCESSOR_A_EDGES,
    PROCESSOR_B_EDGES,
    P_1Q_DEPOLARIZING,
    P_2Q_DEPOLARIZING,
    P_READOUT_ERROR,
    get_official_noise_model,
    get_processor_a,
    get_processor_b,
    get_noisy_simulator,
    make_bidirectional,
)

__all__ = [
    "PROCESSOR_A_EDGES",
    "PROCESSOR_B_EDGES",
    "P_1Q_DEPOLARIZING",
    "P_2Q_DEPOLARIZING",
    "P_READOUT_ERROR",
    "get_official_noise_model",
    "get_processor_a",
    "get_processor_b",
    "get_noisy_simulator",
    "make_bidirectional",
]
