"""Experiment service for managing baseline and attack experiments."""
import logging
import hashlib
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from models.domain import Experiment, QuantumResult, ReproducibilityMetadata
from models.repositories import (
    ExperimentRepository,
    QuantumResultRepository,
    ReproducibilityMetadataRepository,
    AuditLogRepository,
)
from quantum import simulate_teleportation_signature, get_pauli_eigenstate
from attacks import AttackRegistry
from .exceptions import (
    ExperimentNotFound,
    QuantumExecutionFailed,
    InvalidConfiguration,
    InvestigationNotFound,
)
from .investigation_service import InvestigationService

logger = logging.getLogger(__name__)


class ExperimentService:
    """Service for experiment operations (baseline and attack)."""

    def __init__(self, db: Session):
        """Initialize service with database session.

        Args:
            db: SQLAlchemy session
        """
        self.db = db
        self.exp_repo = ExperimentRepository()
        self.quantum_repo = QuantumResultRepository()
        self.reproducibility_repo = ReproducibilityMetadataRepository()
        self.audit_repo = AuditLogRepository()
        self.investigation_service = InvestigationService(db)

    def run_baseline_experiment(
        self,
        investigation_id: str,
        state: str,
        shots: int,
        seed: Optional[int] = None,
        measurement_basis: str = "Z",
    ) -> Dict[str, Any]:
        """Run a baseline quantum experiment.

        Args:
            investigation_id: Investigation ID
            state: Quantum state (|0>, |1>, |+>, |->)
            shots: Number of measurement shots
            seed: Random seed for reproducibility
            measurement_basis: Measurement basis (Z or X)

        Returns:
            Dictionary with experiment and quantum result

        Raises:
            InvestigationNotFound: If investigation does not exist
            InvalidConfiguration: If parameters are invalid
            QuantumExecutionFailed: If quantum simulation fails
        """
        # Verify investigation exists
        investigation = self.investigation_service.get_investigation(investigation_id)

        # Validate parameters
        self._validate_experiment_config(state, shots, measurement_basis)

        try:
            # Create experiment record
            config = {
                "state": state,
                "shots": shots,
                "seed": seed,
                "measurement_basis": measurement_basis,
            }
            experiment = self.exp_repo.create(
                self.db,
                investigation_id=investigation_id,
                type_="baseline",
                config=config,
            )

            logger.info(
                f"Baseline experiment started: {experiment.id}",
                extra={"experiment_id": experiment.id, "investigation_id": investigation_id},
            )

            # Mark investigation as running
            self.investigation_service.update_status(investigation_id, "baseline_running")

            # Execute quantum simulation
            start_time = datetime.now()
            try:
                result = simulate_teleportation_signature(
                    state_name=state,
                    shots=shots,
                    seed=seed,
                    measurement_basis=measurement_basis,
                )
            except Exception as e:
                raise QuantumExecutionFailed(f"simulate_teleportation_signature failed: {str(e)}")

            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Extract quantum result
            quantum_result = self.quantum_repo.create(
                self.db,
                experiment_id=experiment.id,
                measurement_counts=result.get("measurement_counts", {}),
                measurement_probabilities=result.get("measurement_probabilities", {}),
                theoretical_probabilities=result.get("theoretical_probabilities", {}),
                fidelity=result.get("fidelity"),
                circuit_qasm=result.get("circuit_qasm"),
            )

            # Store reproducibility metadata
            config_hash = hashlib.sha256(
                json.dumps(config, sort_keys=True, default=str).encode()
            ).hexdigest()
            reproducibility = self.reproducibility_repo.create(
                self.db,
                experiment_id=experiment.id,
                config=config,
                seed=seed,
                simulator="numpy_custom",
                noise_model=None,
                execution_environment=None,
            )

            # Update experiment status
            self.exp_repo.update_status(
                self.db, experiment.id, "completed", execution_time_ms=execution_time_ms
            )

            # Audit log
            self.audit_repo.log(
                self.db,
                action="BASELINE_EXPERIMENT_COMPLETED",
                result="success",
                resource_type="Experiment",
                resource_id=experiment.id,
                details=f"Baseline experiment completed. Fidelity: {quantum_result.fidelity:.4f}",
            )

            logger.info(
                f"Baseline experiment completed: {experiment.id}",
                extra={
                    "experiment_id": experiment.id,
                    "fidelity": quantum_result.fidelity,
                    "execution_time_ms": execution_time_ms,
                },
            )

            return {
                "experiment_id": experiment.id,
                "status": "completed",
                "execution_time_ms": execution_time_ms,
                "quantum_result": {
                    "id": quantum_result.id,
                    "fidelity": quantum_result.fidelity,
                    "measurement_counts": quantum_result.measurement_counts,
                    "measurement_probabilities": quantum_result.measurement_probabilities,
                    "theoretical_probabilities": quantum_result.theoretical_probabilities,
                },
            }

        except QuantumExecutionFailed:
            raise
        except Exception as e:
            logger.error(
                f"Baseline experiment failed: {str(e)}",
                extra={"experiment_id": experiment.id if "experiment" in locals() else None},
                exc_info=True,
            )
            if "experiment" in locals():
                self.exp_repo.update_status(self.db, experiment.id, "failed", error=str(e))
                self.audit_repo.log(
                    self.db,
                    action="BASELINE_EXPERIMENT_FAILED",
                    result="failure",
                    resource_type="Experiment",
                    resource_id=experiment.id,
                    details=f"Error: {str(e)}",
                )
            raise QuantumExecutionFailed(f"Baseline experiment failed: {str(e)}")

    def run_attack_experiment(
        self,
        investigation_id: str,
        baseline_experiment_id: str,
        state: str,
        shots: int,
        attack_type: str,
        attack_intensity: float = 0.5,
        seed: Optional[int] = None,
        measurement_basis: str = "Z",
    ) -> Dict[str, Any]:
        """Run an attack experiment.

        Args:
            investigation_id: Investigation ID
            baseline_experiment_id: Baseline experiment ID for comparison
            state: Quantum state
            shots: Number of shots
            attack_type: Type of attack
            attack_intensity: Attack intensity (0.0-1.0)
            seed: Random seed
            measurement_basis: Measurement basis

        Returns:
            Dictionary with experiment, quantum result, and detection result

        Raises:
            InvestigationNotFound: If investigation does not exist
            InvalidConfiguration: If parameters are invalid
            QuantumExecutionFailed: If quantum execution fails
        """
        # Verify investigation and baseline experiment exist
        investigation = self.investigation_service.get_investigation(investigation_id)
        baseline_exp = self.exp_repo.get_by_id(self.db, baseline_experiment_id)
        if baseline_exp is None:
            raise ExperimentNotFound(baseline_experiment_id)

        # Validate parameters
        self._validate_experiment_config(state, shots, measurement_basis)
        self._validate_attack_config(attack_type, attack_intensity)

        try:
            # Create experiment record
            config = {
                "state": state,
                "shots": shots,
                "seed": seed,
                "measurement_basis": measurement_basis,
                "attack_type": attack_type,
                "attack_intensity": attack_intensity,
            }
            experiment = self.exp_repo.create(
                self.db,
                investigation_id=investigation_id,
                type_="attack",
                config=config,
            )

            logger.info(
                f"Attack experiment started: {experiment.id}",
                extra={
                    "experiment_id": experiment.id,
                    "attack_type": attack_type,
                    "investigation_id": investigation_id,
                },
            )

            # Mark investigation as running
            self.investigation_service.update_status(investigation_id, "attack_running")

            # Execute quantum simulation with attack
            start_time = datetime.now()
            try:
                # Run baseline simulation
                input_state = get_pauli_eigenstate(state)

                # Create attack
                attack = AttackRegistry.create(attack_type, intensity=attack_intensity)

                # Apply attack
                attacked_state = attack.apply(input_state, seed=seed)

                # Measure attacked state
                attacked_outcomes = []
                for _ in range(shots):
                    if measurement_basis == "Z":
                        outcome = attacked_state.measure_z_basis()
                    else:
                        outcome = attacked_state.measure_x_basis()
                    attacked_outcomes.append(outcome)

                # Compute statistics
                counts = {str(k): attacked_outcomes.count(k) for k in [0, 1]}
                probs = {str(k): v / shots for k, v in counts.items()}

                # Get theoretical probabilities (same as baseline)
                baseline_result = baseline_exp.quantum_result
                if baseline_result is None:
                    raise QuantumExecutionFailed("Baseline experiment has no quantum result")

                # Compute fidelity (simplified: inner product)
                import numpy as np

                attacked_vec = np.array([probs.get("0", 0), probs.get("1", 0)])
                baseline_vec = np.array(
                    [
                        baseline_result.theoretical_probabilities.get("0", 0),
                        baseline_result.theoretical_probabilities.get("1", 0),
                    ]
                )
                fidelity = float(np.dot(attacked_vec, baseline_vec))

            except Exception as e:
                raise QuantumExecutionFailed(f"Attack execution failed: {str(e)}")

            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Store quantum result
            quantum_result = self.quantum_repo.create(
                self.db,
                experiment_id=experiment.id,
                measurement_counts=counts,
                measurement_probabilities=probs,
                theoretical_probabilities=baseline_result.theoretical_probabilities,
                fidelity=fidelity,
                circuit_qasm=None,
            )

            # Store reproducibility metadata
            reproducibility = self.reproducibility_repo.create(
                self.db,
                experiment_id=experiment.id,
                config=config,
                seed=seed,
                simulator="numpy_custom",
                noise_model=None,
                execution_environment=None,
            )

            # Update experiment status
            self.exp_repo.update_status(
                self.db, experiment.id, "completed", execution_time_ms=execution_time_ms
            )

            # Audit log
            self.audit_repo.log(
                self.db,
                action="ATTACK_EXPERIMENT_COMPLETED",
                result="success",
                resource_type="Experiment",
                resource_id=experiment.id,
                details=f"Attack experiment completed. Fidelity: {fidelity:.4f}, Attack: {attack_type}",
            )

            logger.info(
                f"Attack experiment completed: {experiment.id}",
                extra={
                    "experiment_id": experiment.id,
                    "attack_type": attack_type,
                    "fidelity": fidelity,
                    "execution_time_ms": execution_time_ms,
                },
            )

            return {
                "experiment_id": experiment.id,
                "status": "completed",
                "execution_time_ms": execution_time_ms,
                "quantum_result": {
                    "id": quantum_result.id,
                    "fidelity": fidelity,
                    "measurement_counts": counts,
                    "measurement_probabilities": probs,
                    "theoretical_probabilities": baseline_result.theoretical_probabilities,
                },
            }

        except QuantumExecutionFailed:
            raise
        except Exception as e:
            logger.error(f"Attack experiment failed: {str(e)}", exc_info=True)
            if "experiment" in locals():
                self.exp_repo.update_status(self.db, experiment.id, "failed", error=str(e))
                self.audit_repo.log(
                    self.db,
                    action="ATTACK_EXPERIMENT_FAILED",
                    result="failure",
                    resource_type="Experiment",
                    resource_id=experiment.id,
                    details=f"Error: {str(e)}",
                )
            raise QuantumExecutionFailed(f"Attack experiment failed: {str(e)}")

    def get_experiment(self, experiment_id: str) -> Experiment:
        """Get experiment by ID.

        Args:
            experiment_id: Experiment ID

        Returns:
            Experiment object

        Raises:
            ExperimentNotFound: If experiment does not exist
        """
        experiment = self.exp_repo.get_by_id(self.db, experiment_id)
        if experiment is None:
            raise ExperimentNotFound(experiment_id)
        return experiment

    def get_experiments_by_investigation(self, investigation_id: str) -> List[Experiment]:
        """Get all experiments for an investigation.

        Args:
            investigation_id: Investigation ID

        Returns:
            List of experiments
        """
        return self.exp_repo.get_by_investigation(self.db, investigation_id)

    @staticmethod
    def _validate_experiment_config(
        state: str, shots: int, measurement_basis: str
    ) -> None:
        """Validate experiment configuration.

        Args:
            state: Quantum state
            shots: Number of shots
            measurement_basis: Measurement basis

        Raises:
            InvalidConfiguration: If configuration is invalid
        """
        valid_states = {"|0>", "|1>", "|+>", "|->"}
        if state not in valid_states:
            raise InvalidConfiguration(f"State must be one of {valid_states}, got {state}")

        if not (100 <= shots <= 100000):
            raise InvalidConfiguration(f"Shots must be between 100 and 100,000, got {shots}")

        if measurement_basis not in {"Z", "X"}:
            raise InvalidConfiguration(f"Measurement basis must be Z or X, got {measurement_basis}")

    @staticmethod
    def _validate_attack_config(attack_type: str, attack_intensity: float) -> None:
        """Validate attack configuration.

        Args:
            attack_type: Type of attack
            attack_intensity: Attack intensity

        Raises:
            InvalidConfiguration: If configuration is invalid
        """
        valid_attacks = {"forgery", "impersonation", "replay", "channel"}
        if attack_type not in valid_attacks:
            raise InvalidConfiguration(
                f"Attack type must be one of {valid_attacks}, got {attack_type}"
            )

        if not (0.0 <= attack_intensity <= 1.0):
            raise InvalidConfiguration(
                f"Attack intensity must be between 0.0 and 1.0, got {attack_intensity}"
            )
