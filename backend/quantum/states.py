"""Quantum states and Pauli eigenstates implementation."""
import numpy as np
from typing import Literal

# Pauli matrices
I = np.array([[1, 0], [0, 1]], dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)


class QuantumState:
    """Represents a single-qubit quantum state."""

    def __init__(self, state_vector: np.ndarray, name: str = ""):
        """Initialize quantum state.

        Args:
            state_vector: Complex vector [α, β] where |ψ⟩ = α|0⟩ + β|1⟩
            name: Human-readable name
        """
        self.state_vector = np.array(state_vector, dtype=complex)
        self.name = name

        # Normalize
        norm = np.linalg.norm(self.state_vector)
        if norm > 0:
            self.state_vector = self.state_vector / norm

    def __repr__(self) -> str:
        """String representation."""
        α, β = self.state_vector
        if self.name:
            return f"QuantumState({self.name}): {α:.3f}|0⟩ + {β:.3f}|1⟩"
        return f"QuantumState: {α:.3f}|0⟩ + {β:.3f}|1⟩"

    def measure_z_basis(self) -> int:
        """Measure in computational (Z) basis.

        Returns:
            0 or 1 based on |⟨0|ψ⟩|² and |⟨1|ψ⟩|²
        """
        prob_0 = abs(self.state_vector[0]) ** 2
        return 0 if np.random.random() < prob_0 else 1

    def measure_x_basis(self) -> int:
        """Measure in Hadamard (X) basis.

        Returns:
            0 (corresponds to |+⟩) or 1 (corresponds to |-⟩)
        """
        # |+⟩ = (|0⟩ + |1⟩)/√2
        # |-⟩ = (|0⟩ - |1⟩)/√2
        plus_state = np.array([1, 1], dtype=complex) / np.sqrt(2)
        prob_plus = abs(np.dot(plus_state.conj(), self.state_vector)) ** 2
        return 0 if np.random.random() < prob_plus else 1

    def apply_pauli(self, pauli: Literal["I", "X", "Y", "Z"]) -> "QuantumState":
        """Apply Pauli gate and return new state.

        Args:
            pauli: Which Pauli gate ("I", "X", "Y", "Z")

        Returns:
            New QuantumState after Pauli application
        """
        matrices = {"I": I, "X": X, "Y": Y, "Z": Z}
        matrix = matrices[pauli]
        new_vector = matrix @ self.state_vector
        return QuantumState(new_vector, name=f"{self.name}_after_{pauli}")

    def fidelity(self, other: "QuantumState") -> float:
        """Calculate fidelity with another state.

        Fidelity F = |⟨ψ|φ⟩|²

        Args:
            other: Another QuantumState

        Returns:
            Fidelity (0 to 1)
        """
        overlap = np.dot(self.state_vector.conj(), other.state_vector)
        return abs(overlap) ** 2


# Predefined Pauli eigenstates
def get_pauli_eigenstate(state_name: str) -> QuantumState:
    """Get a standard Pauli eigenstate.

    Args:
        state_name: "|0>", "|1>", "|+>", "|->"

    Returns:
        QuantumState corresponding to the eigenstate
    """
    states = {
        "|0>": QuantumState(np.array([1, 0], dtype=complex), "|0⟩"),
        "|1>": QuantumState(np.array([0, 1], dtype=complex), "|1⟩"),
        "|+>": QuantumState(np.array([1, 1], dtype=complex) / np.sqrt(2), "|+⟩"),
        "|->" : QuantumState(np.array([1, -1], dtype=complex) / np.sqrt(2), "|-⟩"),
    }

    if state_name not in states:
        raise ValueError(f"Unknown state: {state_name}. Choose from {list(states.keys())}")

    return states[state_name]


def measure_distribution(state: QuantumState, basis: Literal["Z", "X"] = "Z", shots: int = 1000) -> dict:
    """Simulate measurement of a state multiple times.

    Args:
        state: QuantumState to measure
        basis: Measurement basis ("Z" or "X")
        shots: Number of measurement repetitions

    Returns:
        Dictionary mapping outcomes to probabilities
    """
    outcomes = []

    for _ in range(shots):
        if basis == "Z":
            outcome = state.measure_z_basis()
        else:  # basis == "X"
            outcome = state.measure_x_basis()
        outcomes.append(outcome)

    # Count outcomes
    counts = {0: outcomes.count(0), 1: outcomes.count(1)}
    probs = {str(k): v / shots for k, v in counts.items()}

    return probs


def get_theoretical_distribution(state: QuantumState, basis: Literal["Z", "X"] = "Z") -> dict:
    """Get theoretical measurement probability distribution.

    Args:
        state: QuantumState to analyze
        basis: Measurement basis ("Z" or "X")

    Returns:
        Dictionary with theoretical probabilities
    """
    α, β = state.state_vector

    if basis == "Z":
        # Probabilities for computational basis
        prob_0 = abs(α) ** 2
        prob_1 = abs(β) ** 2
    else:  # basis == "X"
        # Probabilities for Hadamard basis
        # |+⟩ measurement: prob_plus = |⟨+|ψ⟩|²
        plus = np.array([1, 1], dtype=complex) / np.sqrt(2)
        prob_plus = abs(np.dot(plus.conj(), state.state_vector)) ** 2
        prob_0 = prob_plus
        prob_1 = 1 - prob_plus

    return {"0": prob_0, "1": prob_1}
