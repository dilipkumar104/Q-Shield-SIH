"""SQLAlchemy ORM domain models."""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from db import Base


class Investigation(Base):
    """Investigation entity - user-facing unit of work."""
    __tablename__ = "investigations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(String(2000), nullable=True)
    protocol = Column(String(50), nullable=False, default="teleportation_qds")
    status = Column(String(50), nullable=False, default="setup")  # setup, baseline_running, attack_running, completed, failed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=True)

    # Relationships
    experiments = relationship("Experiment", back_populates="investigation", cascade="all, delete-orphan")
    detection_results = relationship("DetectionResult", back_populates="investigation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Investigation {self.id}: {self.name}>"


class Experiment(Base):
    """Experiment entity - baseline or attack execution."""
    __tablename__ = "experiments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    investigation_id = Column(String(36), ForeignKey("investigations.id"), nullable=False)
    type = Column(String(20), nullable=False)  # "baseline" or "attack"
    config = Column(JSON, nullable=False)  # Serialized ExperimentConfig
    status = Column(String(50), nullable=False, default="pending")  # pending, running, completed, failed
    execution_time_ms = Column(Float, nullable=True)
    error = Column(String(2000), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    investigation = relationship("Investigation", back_populates="experiments")
    quantum_result = relationship("QuantumResult", back_populates="experiment", uselist=False, cascade="all, delete-orphan")
    reproducibility_metadata = relationship("ReproducibilityMetadata", back_populates="experiment", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Experiment {self.id}: {self.type}>"


class QuantumResult(Base):
    """Quantum simulation result."""
    __tablename__ = "quantum_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id = Column(String(36), ForeignKey("experiments.id"), nullable=False)
    measurement_counts = Column(JSON, nullable=False)  # {"0": 1000, "1": 1000}
    measurement_probabilities = Column(JSON, nullable=False)  # {"0": 0.5, "1": 0.5}
    theoretical_probabilities = Column(JSON, nullable=False)
    fidelity = Column(Float, nullable=True)
    circuit_qasm = Column(String(5000), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    experiment = relationship("Experiment", back_populates="quantum_result")

    def __repr__(self):
        return f"<QuantumResult {self.id}: fidelity={self.fidelity}>"


class DetectionResult(Base):
    """Detection/verdict result."""
    __tablename__ = "detection_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    investigation_id = Column(String(36), ForeignKey("investigations.id"), nullable=False)
    baseline_experiment_id = Column(String(36), ForeignKey("experiments.id"), nullable=True)
    attack_experiment_id = Column(String(36), ForeignKey("experiments.id"), nullable=True)
    decision = Column(String(20), nullable=False)  # LEGITIMATE, SUSPICIOUS, ATTACK
    confidence = Column(Float, nullable=False)
    explanation = Column(String(2000), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    investigation = relationship("Investigation", back_populates="detection_results")
    evidence_events = relationship("EvidenceEvent", back_populates="detection_result", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DetectionResult {self.id}: {self.decision}>"


class EvidenceEvent(Base):
    """Structured evidence event in detection audit trail."""
    __tablename__ = "evidence_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    detection_id = Column(String(36), ForeignKey("detection_results.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    event_type = Column(String(50), nullable=False)  # measurement, test_result, extraction, verdict
    source = Column(String(50), nullable=False)  # baseline, attack, comparison
    signal_type = Column(String(100), nullable=False)  # fidelity_degradation, measurement_shift, chi_square, etc.
    value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=True)
    unit = Column(String(50), nullable=False)  # fidelity, probability, statistic, etc.
    p_value = Column(Float, nullable=True)
    test_statistic = Column(Float, nullable=True)
    verdict = Column(String(20), nullable=True)  # pass, fail
    event_data = Column(JSON, nullable=True)

    # Relationships
    detection_result = relationship("DetectionResult", back_populates="evidence_events")

    def __repr__(self):
        return f"<EvidenceEvent {self.id}: {self.signal_type}>"


class ReproducibilityMetadata(Base):
    """Metadata for experiment reproducibility and replay."""
    __tablename__ = "reproducibility_metadata"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id = Column(String(36), ForeignKey("experiments.id"), nullable=False)
    config_hash = Column(String(64), nullable=False)  # SHA256 of config
    seed = Column(Integer, nullable=True)
    simulator = Column(String(100), nullable=False, default="numpy_custom")
    simulator_version = Column(String(20), nullable=True)
    noise_model = Column(String(100), nullable=True)
    execution_environment = Column(String(500), nullable=True)
    is_reproducible = Column(Boolean, nullable=False, default=False)
    replay_timestamp = Column(DateTime, nullable=True)
    replay_result = Column(String(20), nullable=True)  # match, differ, error
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    experiment = relationship("Experiment", back_populates="reproducibility_metadata")

    def __repr__(self):
        return f"<ReproducibilityMetadata {self.id}>"


class AuditLog(Base):
    """Audit trail for security and compliance."""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    action = Column(String(255), nullable=False)
    user_id = Column(String(255), nullable=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(36), nullable=True)
    result = Column(String(20), nullable=False)  # success, failure
    details = Column(String(2000), nullable=True)

    def __repr__(self):
        return f"<AuditLog {self.id}: {self.action}>"
