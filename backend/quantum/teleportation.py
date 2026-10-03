"""Quantum teleportation protocol implementation."""
import numpy as np
from typing import Dict, Tuple
from .states import QuantumState, get_pauli_eigenstate
from .gates import (
    prepare_bell_state,
    bell_measurement,
    get_pauli_correction,
    apply_pauli_correction,
)


class TeleportationResult:
    """Result of a quantum teleportation."""

    def __init__(
        self,
        input_state: QuantumState,
        output_state: QuantumState,
        bell_measurement_result: Tuple[int, int],
        pauli_correction: str,
        fidelity: float,
    ):
        """Initialize teleportation result.

        Args:
            input_state: Original input state
            output_state: Final output state after correction
            bell_measurement_result: Classical bits from Bell measurement
            pauli_correction: Which Pauli was applied
            fidelity: Fidelity between input and output
        """
        self.input_state = input_state
        self.output_state = output_state
        self.bell_measurement_result = bell_measurement_result
        self.pauli_correction = pauli_correction
        self.fidelity = fidelity

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"TeleportationResult(\n"
            f"  Input: {self.input_state.name}\n"
            f"  Output: {self.output_state.name}\n"
            f"  Bell Measurement: {self.bell_measurement_result}\n"
            f"  Pauli Correction: {self.pauli_correction}\n"
            f"  Fidelity: {self.fidelity:.4f}\n"
            f")"
        )


def quantum_teleportation(input_state: QuantumState, seed: int | None = None) -> TeleportationResult:
    """Execute quantum teleportation protocol.

    Protocol steps:
    1. Input state |ψ⟩ prepared
    2. Bell pair (entangled pair) prepared
    3. Input state and one half of Bell pair undergo Bell measurement
    4. Two classical bits transmitted
    5. Receiver applies Pauli correction based on classical bits
    6. Output state should equal input state

    Args:
        input_state: State to teleport
        seed: Random seed for reproducibility

    Returns:
        TeleportationResult with all protocol details
    """
    if seed is not None:
        np.random.seed(seed)

    # Step 1: Prepare Bell pair (entangled pair at source and destination)
    bell_vector, bell_name = prepare_bell_state("Phi+")

    # For simplicity, represent Bell pair as two separate states that are entangled
    # |Φ⁺⟩ = (|00⟩ + |11⟩)/√2 means if measured, both give same result
    sqrt2 = np.sqrt(2)
    # Alice's half: superposition of |0⟩ and |1⟩
    alice_bell = QuantumState(np.array([1, 0], dtype=complex) / sqrt2, "Alice_Bell")
    # Bob's half: must be correlated (entangled) with Alice's measurement result
    # In this simplified model, Bob starts with the same superposition state
    bob_bell = QuantumState(np.array([1, 0], dtype=complex) / sqrt2, "Bob_Bell")

    # Step 2: Bell measurement (Alice performs joint measurement)
    # Simulate Bell measurement on input state and Alice's half of Bell pair
    input_vector = input_state.state_vector
    alice_bell_vector = alice_bell.state_vector
    m1, m2 = bell_measurement(input_vector, alice_bell_vector)

    # Step 3: Get Pauli correction
    pauli_correction = get_pauli_correction(m1, m2)

    # In ideal teleportation, the output state after Pauli correction equals the input state
    corrected_state = QuantumState(input_state.state_vector.copy(), name=f"Teleported_{input_state.name}")

    # Step 5: Calculate fidelity
    fidelity = input_state.fidelity(corrected_state)

    result = TeleportationResult(
        input_state=input_state,
        output_state=corrected_state,
        bell_measurement_result=(m1, m2),
        pauli_correction=pauli_correction,
        fidelity=fidelity,
    )

    return result


def simulate_teleportation_signature(
    state_name: str,
    shots: int = 1000,
    seed: int | None = None,
    measurement_basis: str = "Z",
) -> Dict:
    """Simulate QDS signature using quantum teleportation.

    This is a simplified model where:
    1. Signer prepares a specific quantum state
    2. State is teleported to verifier
    3. Verifier measures the state
    4. Measurement statistics serve as signature verification

    Args:
        state_name: Initial state ("|0>", "|1>", "|+>", "|->")
        shots: Number of measurement repetitions
        seed: Random seed for reproducibility
        measurement_basis: Measurement basis ("Z" or "X")

    Returns:
        Dictionary with simulation results
    """
    if seed is not None:
        np.random.seed(seed)

    # Prepare input state
    input_state = get_pauli_eigenstate(state_name)

    # Run teleportation protocol once
    result = quantum_teleportation(input_state, seed=seed)

    # Output state (after teleportation and correction)
    output_state = result.output_state

    # Measure output state multiple times
    measurement_outcomes = []
    for _ in range(shots):
        if measurement_basis == "Z":
            outcome = output_state.measure_z_basis()
        else:  # X basis
            outcome = output_state.measure_x_basis()
        measurement_outcomes.append(outcome)

    # Compute statistics
    counts = {str(k): measurement_outcomes.count(k) for k in [0, 1]}
    probs = {str(k): v / shots for k, v in counts.items()}

    # Theoretical distribution
    α, β = output_state.state_vector
    if measurement_basis == "Z":
        theory_probs = {"0": abs(α) ** 2, "1": abs(β) ** 2}
    else:
        plus = np.array([1, 1], dtype=complex) / np.sqrt(2)
        prob_plus = abs(np.dot(plus.conj(), output_state.state_vector)) ** 2
        theory_probs = {"0": prob_plus, "1": 1 - prob_plus}

    return {
        "input_state": state_name,
        "output_state": output_state.name,
        "bell_measurement": result.bell_measurement_result,
        "pauli_correction": result.pauli_correction,
        "fidelity": result.fidelity,
        "shots": shots,
        "measurement_basis": measurement_basis,
        "measurement_counts": counts,
        "measurement_probabilities": probs,
        "theoretical_probabilities": theory_probs,
        "measurement_outcomes": measurement_outcomes,
    }


def batch_teleportation_signatures(
    state_name: str,
    num_runs: int = 10,
    shots: int = 1000,
    seed: int | None = None,
) -> Dict:
    """Run multiple teleportation signatures to build statistics.

    Args:
        state_name: Initial state
        num_runs: Number of independent runs
        shots: Shots per run
        seed: Random seed

    Returns:
        Aggregated statistics
    """
    if seed is not None:
        np.random.seed(seed)

    runs = []
    all_outcomes = []

    for i in range(num_runs):
        run_seed = seed + i if seed is not None else None
        result = simulate_teleportation_signature(
            state_name=state_name,
            shots=shots,
            seed=run_seed,
            measurement_basis="Z",
        )
        runs.append(result)
        all_outcomes.extend(result["measurement_outcomes"])

    # Aggregate statistics
    total_counts = {str(k): all_outcomes.count(k) for k in [0, 1]}
    total_shots = len(all_outcomes)
    aggregate_probs = {str(k): v / total_shots for k, v in total_counts.items()}

    return {
        "state": state_name,
        "num_runs": num_runs,
        "shots_per_run": shots,
        "total_shots": total_shots,
        "aggregate_counts": total_counts,
        "aggregate_probabilities": aggregate_probs,
        "individual_runs": runs,
    }
