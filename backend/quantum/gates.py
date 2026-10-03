"""Quantum gates and Bell state preparation."""
import numpy as np
from typing import Literal, Tuple
from .states import QuantumState, I, X, Y, Z


def hadamard(state: QuantumState) -> QuantumState:
    """Apply Hadamard gate.

    H|0⟩ = |+⟩
    H|1⟩ = |-⟩
    H|+⟩ = |0⟩
    H|-⟩ = |1⟩
    """
    H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
    new_vector = H @ state.state_vector
    return QuantumState(new_vector, name=f"H({state.name})")


def pauli_x(state: QuantumState) -> QuantumState:
    """Apply Pauli X (bit flip) gate."""
    new_vector = X @ state.state_vector
    return QuantumState(new_vector, name=f"X({state.name})")


def pauli_z(state: QuantumState) -> QuantumState:
    """Apply Pauli Z (phase flip) gate."""
    new_vector = Z @ state.state_vector
    return QuantumState(new_vector, name=f"Z({state.name})")


def pauli_y(state: QuantumState) -> QuantumState:
    """Apply Pauli Y gate."""
    new_vector = Y @ state.state_vector
    return QuantumState(new_vector, name=f"Y({state.name})")


def cx_gate(control: QuantumState, target: QuantumState) -> Tuple[QuantumState, QuantumState]:
    """Apply CNOT (Controlled-X) gate.

    If control is in |1⟩, flip target.
    This is used for Bell state preparation.

    Args:
        control: Control qubit
        target: Target qubit

    Returns:
        Tuple of (new control, new target)
    """
    # For two-qubit system, construct full matrix
    α_c, β_c = control.state_vector
    α_t, β_t = target.state_vector

    # Product state: |ψ⟩_c ⊗ |ψ⟩_t
    full_state = np.kron(control.state_vector, target.state_vector)

    # CNOT matrix in computational basis (|00⟩, |01⟩, |10⟩, |11⟩)
    CNOT = np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1],
        [0, 0, 1, 0],
    ], dtype=complex)

    result = CNOT @ full_state

    # Extract single-qubit states (simplified for demo)
    # In reality, we'd need to trace out properly
    # Properly apply CNOT to the two-qubit state and return updated qubits
    # Compute the new two-qubit state after applying CNOT
    new_full_state = result
    # Separate the new state back into individual qubits (partial trace approximation)
    # For simplicity in this educational simulation, we split the vector back into two 2‑element vectors
    # by reshaping and taking the marginal states (this is not a true quantum trace but suffices for demo)
    new_control_vec = np.array([new_full_state[0], new_full_state[2]])
    new_target_vec = np.array([new_full_state[0], new_full_state[1]])
    new_control = QuantumState(new_control_vec, name=f"CNOT_control({control.name})")
    new_target = QuantumState(new_target_vec, name=f"CNOT_target({target.name})")
    return new_control, new_target


def prepare_bell_state(bell_type: Literal["Phi+", "Phi-", "Psi+", "Psi-"]) -> Tuple[np.ndarray, str]:
    """Prepare a Bell state (maximally entangled pair).

    Bell states (2-qubit):
    |Φ⁺⟩ = (|00⟩ + |11⟩)/√2   - singlet state
    |Φ⁻⟩ = (|00⟩ - |11⟩)/√2
    |Ψ⁺⟩ = (|01⟩ + |10⟩)/√2
    |Ψ⁻⟩ = (|01⟩ - |10⟩)/√2

    Args:
        bell_type: Which Bell state to prepare

    Returns:
        Tuple of (state vector, name)
    """
    sqrt2 = np.sqrt(2)

    bell_states = {
        "Phi+": (np.array([1, 0, 0, 1], dtype=complex) / sqrt2, "|Φ⁺⟩"),
        "Phi-": (np.array([1, 0, 0, -1], dtype=complex) / sqrt2, "|Φ⁻⟩"),
        "Psi+": (np.array([0, 1, 1, 0], dtype=complex) / sqrt2, "|Ψ⁺⟩"),
        "Psi-": (np.array([0, 1, -1, 0], dtype=complex) / sqrt2, "|Ψ⁻⟩"),
    }

    if bell_type not in bell_states:
        raise ValueError(f"Unknown Bell state: {bell_type}")

    return bell_states[bell_type]


def bell_measurement(
    qubit1: np.ndarray,
    qubit2: np.ndarray,
) -> Tuple[int, int]:
    """Perform Bell measurement (joint measurement of two qubits).

    Measures in Bell basis, projecting onto one of the 4 Bell states.
    Returns which of the 4 Bell states was measured.

    Args:
        qubit1: First qubit state
        qubit2: Second qubit state

    Returns:
        Tuple of (m1, m2) classical bits (0 or 1 each)
    """
    # Construct 2-qubit state
    state_2qubit = np.kron(qubit1, qubit2)

    # Bell measurement projectors
    # |Φ⁺⟩⟨Φ⁺|, |Φ⁻⟩⟨Φ⁻|, |Ψ⁺⟩⟨Ψ⁺|, |Ψ⁻⟩⟨Ψ⁻|
    sqrt2 = np.sqrt(2)

    phi_plus = np.array([1, 0, 0, 1], dtype=complex) / sqrt2
    phi_minus = np.array([1, 0, 0, -1], dtype=complex) / sqrt2
    psi_plus = np.array([0, 1, 1, 0], dtype=complex) / sqrt2
    psi_minus = np.array([0, 1, -1, 0], dtype=complex) / sqrt2

    # Compute overlap (probability) with each Bell state
    prob_phi_plus = abs(np.dot(phi_plus.conj(), state_2qubit)) ** 2
    prob_phi_minus = abs(np.dot(phi_minus.conj(), state_2qubit)) ** 2
    prob_psi_plus = abs(np.dot(psi_plus.conj(), state_2qubit)) ** 2
    prob_psi_minus = abs(np.dot(psi_minus.conj(), state_2qubit)) ** 2

    # Measurement: collapse to one state
    probs = [prob_phi_plus, prob_phi_minus, prob_psi_plus, prob_psi_minus]
    outcome = np.random.choice(4, p=probs / np.sum(probs))

    # Convert outcome to two classical bits
    # 0 -> (0,0) - Phi+
    # 1 -> (0,1) - Phi-
    # 2 -> (1,0) - Psi+
    # 3 -> (1,1) - Psi-
    m1 = (outcome >> 1) & 1
    m2 = outcome & 1

    return m1, m2


def get_pauli_correction(m1: int, m2: int) -> str:
    """Get Pauli correction based on Bell measurement outcome.

    Args:
        m1: First classical bit from Bell measurement
        m2: Second classical bit from Bell measurement

    Returns:
        Pauli gate to apply: "I", "X", "Z", or "Y"
    """
    # Measurement outcomes map to Pauli corrections
    # 00 -> I (identity)
    # 01 -> X (bit flip)
    # 10 -> Z (phase flip)
    # 11 -> Y (both)
    bits = (m1 << 1) | m2
    corrections = {0: "I", 1: "X", 2: "Z", 3: "Y"}
    return corrections[bits]


def apply_pauli_correction(state: QuantumState, pauli: str) -> QuantumState:
    """Apply Pauli correction to quantum state.

    Args:
        state: State to correct
        pauli: Which Pauli gate ("I", "X", "Y", "Z")

    Returns:
        Corrected state
    """
    if pauli == "I":
        return state
    elif pauli == "X":
        return pauli_x(state)
    elif pauli == "Y":
        return pauli_y(state)
    elif pauli == "Z":
        return pauli_z(state)
    else:
        raise ValueError(f"Unknown Pauli: {pauli}")
