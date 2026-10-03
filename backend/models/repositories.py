"""Repository pattern for database access."""
import hashlib
import json
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from models.domain import (
    Investigation, Experiment, QuantumResult, DetectionResult,
    EvidenceEvent, ReproducibilityMetadata, AuditLog
)


class InvestigationRepository:
    """CRUD operations for Investigation."""

    @staticmethod
    def create(db: Session, name: str, description: str, protocol: str = "teleportation_qds", created_by: Optional[str] = None) -> Investigation:
        """Create a new investigation."""
        investigation = Investigation(
            name=name,
            description=description,
            protocol=protocol,
            created_by=created_by,
        )
        db.add(investigation)
        db.commit()
        db.refresh(investigation)
        return investigation

    @staticmethod
    def get_by_id(db: Session, investigation_id: str) -> Optional[Investigation]:
        """Get investigation by ID."""
        return db.query(Investigation).filter(Investigation.id == investigation_id).first()

    @staticmethod
    def get_all(db: Session, limit: int = 50, offset: int = 0) -> tuple[List[Investigation], int]:
        """Get all investigations with pagination."""
        total = db.query(Investigation).count()
        investigations = db.query(Investigation).order_by(Investigation.created_at.desc()).limit(limit).offset(offset).all()
        return investigations, total

    @staticmethod
    def update_status(db: Session, investigation_id: str, status: str) -> Investigation:
        """Update investigation status."""
        investigation = InvestigationRepository.get_by_id(db, investigation_id)
        if investigation:
            investigation.status = status
            investigation.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(investigation)
        return investigation

    @staticmethod
    def delete(db: Session, investigation_id: str) -> bool:
        """Delete an investigation."""
        investigation = InvestigationRepository.get_by_id(db, investigation_id)
        if investigation:
            db.delete(investigation)
            db.commit()
            return True
        return False


class ExperimentRepository:
    """CRUD operations for Experiment."""

    @staticmethod
    def create(db: Session, investigation_id: str, type_: str, config: dict) -> Experiment:
        """Create a new experiment."""
        experiment = Experiment(
            investigation_id=investigation_id,
            type=type_,
            config=config,
        )
        db.add(experiment)
        db.commit()
        db.refresh(experiment)
        return experiment

    @staticmethod
    def get_by_id(db: Session, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID."""
        return db.query(Experiment).filter(Experiment.id == experiment_id).first()

    @staticmethod
    def get_by_investigation(db: Session, investigation_id: str) -> List[Experiment]:
        """Get all experiments for an investigation."""
        return db.query(Experiment).filter(Experiment.investigation_id == investigation_id).order_by(Experiment.created_at).all()

    @staticmethod
    def update_status(db: Session, experiment_id: str, status: str, execution_time_ms: Optional[float] = None, error: Optional[str] = None) -> Experiment:
        """Update experiment status."""
        experiment = ExperimentRepository.get_by_id(db, experiment_id)
        if experiment:
            experiment.status = status
            if execution_time_ms is not None:
                experiment.execution_time_ms = execution_time_ms
            if error:
                experiment.error = error
            experiment.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(experiment)
        return experiment

    @staticmethod
    def delete(db: Session, experiment_id: str) -> bool:
        """Delete an experiment."""
        experiment = ExperimentRepository.get_by_id(db, experiment_id)
        if experiment:
            db.delete(experiment)
            db.commit()
            return True
        return False


class QuantumResultRepository:
    """CRUD operations for QuantumResult."""

    @staticmethod
    def create(db: Session, experiment_id: str, measurement_counts: dict, measurement_probabilities: dict,
               theoretical_probabilities: dict, fidelity: Optional[float] = None, circuit_qasm: Optional[str] = None) -> QuantumResult:
        """Create a quantum result."""
        result = QuantumResult(
            experiment_id=experiment_id,
            measurement_counts=measurement_counts,
            measurement_probabilities=measurement_probabilities,
            theoretical_probabilities=theoretical_probabilities,
            fidelity=fidelity,
            circuit_qasm=circuit_qasm,
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return result

    @staticmethod
    def get_by_experiment(db: Session, experiment_id: str) -> Optional[QuantumResult]:
        """Get quantum result for an experiment."""
        return db.query(QuantumResult).filter(QuantumResult.experiment_id == experiment_id).first()


class DetectionResultRepository:
    """CRUD operations for DetectionResult."""

    @staticmethod
    def create(db: Session, investigation_id: str, baseline_exp_id: Optional[str], attack_exp_id: Optional[str],
               decision: str, confidence: float, explanation: str) -> DetectionResult:
        """Create a detection result."""
        result = DetectionResult(
            investigation_id=investigation_id,
            baseline_experiment_id=baseline_exp_id,
            attack_experiment_id=attack_exp_id,
            decision=decision,
            confidence=confidence,
            explanation=explanation,
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return result

    @staticmethod
    def get_by_investigation(db: Session, investigation_id: str) -> Optional[DetectionResult]:
        """Get latest detection result for an investigation."""
        return db.query(DetectionResult).filter(DetectionResult.investigation_id == investigation_id).order_by(DetectionResult.created_at.desc()).first()


class EvidenceEventRepository:
    """CRUD operations for EvidenceEvent."""

    @staticmethod
    def create(db: Session, detection_id: str, event_type: str, source: str, signal_type: str,
               value: float, unit: str, threshold: Optional[float] = None, p_value: Optional[float] = None,
               test_statistic: Optional[float] = None, verdict: Optional[str] = None, metadata: Optional[dict] = None) -> EvidenceEvent:
        """Create an evidence event."""
        event = EvidenceEvent(
            detection_id=detection_id,
            event_type=event_type,
            source=source,
            signal_type=signal_type,
            value=value,
            unit=unit,
            threshold=threshold,
            p_value=p_value,
            test_statistic=test_statistic,
            verdict=verdict,
            event_data=metadata,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def get_by_detection(db: Session, detection_id: str) -> List[EvidenceEvent]:
        """Get all evidence events for a detection."""
        return db.query(EvidenceEvent).filter(EvidenceEvent.detection_id == detection_id).order_by(EvidenceEvent.timestamp).all()


class ReproducibilityMetadataRepository:
    """CRUD operations for ReproducibilityMetadata."""

    @staticmethod
    def create(db: Session, experiment_id: str, config: dict, seed: Optional[int] = None,
               simulator: str = "numpy_custom", noise_model: Optional[str] = None,
               execution_environment: Optional[str] = None) -> ReproducibilityMetadata:
        """Create reproducibility metadata."""
        config_hash = hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode()).hexdigest()
        metadata = ReproducibilityMetadata(
            experiment_id=experiment_id,
            config_hash=config_hash,
            seed=seed,
            simulator=simulator,
            noise_model=noise_model,
            execution_environment=execution_environment,
        )
        db.add(metadata)
        db.commit()
        db.refresh(metadata)
        return metadata

    @staticmethod
    def get_by_experiment(db: Session, experiment_id: str) -> Optional[ReproducibilityMetadata]:
        """Get reproducibility metadata for an experiment."""
        return db.query(ReproducibilityMetadata).filter(ReproducibilityMetadata.experiment_id == experiment_id).first()

    @staticmethod
    def update_replay(db: Session, metadata_id: str, is_reproducible: bool, replay_result: str) -> ReproducibilityMetadata:
        """Update replay results."""
        metadata = db.query(ReproducibilityMetadata).filter(ReproducibilityMetadata.id == metadata_id).first()
        if metadata:
            metadata.is_reproducible = is_reproducible
            metadata.replay_result = replay_result
            metadata.replay_timestamp = datetime.utcnow()
            db.commit()
            db.refresh(metadata)
        return metadata


class AuditLogRepository:
    """CRUD operations for AuditLog."""

    @staticmethod
    def log(db: Session, action: str, result: str, user_id: Optional[str] = None,
            resource_type: Optional[str] = None, resource_id: Optional[str] = None,
            details: Optional[str] = None) -> AuditLog:
        """Create an audit log entry."""
        log_entry = AuditLog(
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            details=details,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry
