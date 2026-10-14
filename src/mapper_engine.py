"""Automated Architecture Subgraph Embedding and Optimal Layout Engine.

Solves the optimal physical qubit placement problem:
    min_{pi: V_mol -> V_hw} sum_{(u, v) in E_mol} w_{uv} * dist_{G_hw}(pi(u), pi(v))

Finds the optimal initial layout mapping that minimizes the weighted physical routing
distance and SWAP inflation across arbitrary quantum hardware topologies.
"""

from typing import Dict, Any, List, Tuple
import itertools
import networkx as nx
import numpy as np

from src.processors import PROCESSOR_A_EDGES, PROCESSOR_B_EDGES


def extract_hamiltonian_interaction_graph(pauli_operator) -> nx.Graph:
    """Extracts the molecular two-qubit interaction graph from a SparsePauliOp."""
    G = nx.Graph()
    G.add_nodes_from(range(pauli_operator.num_qubits))

    for pauli_str, coeff in zip(pauli_operator.paulis, pauli_operator.coeffs):
        str_repr = pauli_str.to_label()
        # Non-identity indices (little endian to 0-indexed)
        active_qubits = [i for i, char in enumerate(reversed(str_repr)) if char != "I"]
        if len(active_qubits) == 2:
            u, v = active_qubits
            weight = abs(coeff)
            if G.has_edge(u, v):
                G[u][v]["weight"] += weight
            else:
                G.add_edge(u, v, weight=weight)

    return G


def find_optimal_subgraph_embedding(
    mol_graph: nx.Graph,
    hardware_edges: List[List[int]],
    num_hardware_qubits: int
) -> Tuple[Dict[int, int], float]:
    """Finds the global optimal logical-to-physical qubit embedding pi.

    Args:
        mol_graph: Molecular interaction graph with edge weights.
        hardware_edges: Physical processor coupling edges.
        num_hardware_qubits: Total qubits on the processor.

    Returns:
        Tuple[Dict[int, int], float]: Optimal layout {logical_q: physical_q} and minimum routing cost.
    """
    G_hw = nx.Graph()
    G_hw.add_nodes_from(range(num_hardware_qubits))
    G_hw.add_edges_from(hardware_edges)

    # All-pairs shortest path distance matrix in hardware
    dist_hw = dict(nx.all_pairs_shortest_path_length(G_hw))

    logical_nodes = list(mol_graph.nodes())
    k = len(logical_nodes)

    best_mapping = None
    min_cost = float("inf")

    # Search through permutations of physical qubits of size k
    for phys_subset in itertools.permutations(range(num_hardware_qubits), k):
        mapping = {logical_nodes[i]: phys_subset[i] for i in range(k)}

        # Evaluate weighted routing distance cost
        cost = 0.0
        for u, v, data in mol_graph.edges(data=True):
            p_u = mapping[u]
            p_v = mapping[v]
            w = data.get("weight", 1.0)
            cost += w * dist_hw[p_u][p_v]

        if cost < min_cost:
            min_cost = cost
            best_mapping = mapping

    return best_mapping, min_cost


def benchmark_optimal_embeddings() -> Dict[str, Any]:
    """Solves and compares the optimal layout embedding for H2 on Processor A and B."""
    from src.problem import get_h2_problem
    H, _, _ = get_h2_problem()
    mol_graph = extract_hamiltonian_interaction_graph(H)

    opt_layout_a, cost_a = find_optimal_subgraph_embedding(mol_graph, PROCESSOR_A_EDGES, 5)
    opt_layout_b, cost_b = find_optimal_subgraph_embedding(mol_graph, PROCESSOR_B_EDGES, 9)

    return {
        "processor_a_optimal_layout": opt_layout_a,
        "processor_a_min_routing_cost": cost_a,
        "processor_b_optimal_layout": opt_layout_b,
        "processor_b_min_routing_cost": cost_b,
        "relative_routing_advantage": cost_a / max(1e-5, cost_b),
    }
