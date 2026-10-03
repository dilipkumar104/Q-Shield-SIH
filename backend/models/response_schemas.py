"""Pydantic API response schemas (to complement domain models)."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# Investigation Schemas
class InvestigationCreateRequest(BaseModel):
    """Request to create investigation."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    protocol: str = Field(default="teleportation_qds")


class InvestigationResponse(BaseModel):
    """Investigation response."""
    id: str
    name: str
    description: Optional[str]
    protocol: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Experiment Schemas
class ExperimentResponse(BaseModel):
    """Experiment response."""
    id: str
    investigation_id: str
    type: str
    config: Dict[str, Any]
    status: str
    execution_time_ms: Optional[float]
    error: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Quantum Result Schemas
class QuantumResultResponse(BaseModel):
    """Quantum result response."""
    id: str
    experiment_id: str
    measurement_counts: Dict[str, int]
    measurement_probabilities: Dict[str, float]
    theoretical_probabilities: Dict[str, float]
    fidelity: Optional[float]
    circuit_qasm: Optional[str]

    class Config:
        from_attributes = True


# Detection Signal Schema
class DetectionSignalResponse(BaseModel):
    """Detection signal response."""
    signal_type: str
    expected_range: Optional[tuple[float, float]]
    observed_value: float
    threshold: Optional[float]
    verdict: Optional[str]
    p_value: Optional[float]
    test_statistic: Optional[float]
    confidence: float


# Evidence Event Schema
class EvidenceEventResponse(BaseModel):
    """Evidence event response."""
    id: str
    detection_id: str
    timestamp: datetime
    event_type: str
    source: str
    signal_type: str
    value: float
    threshold: Optional[float]
    unit: str
    p_value: Optional[float]
    test_statistic: Optional[float]
    verdict: Optional[str]
    metadata: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


# Detection Result Schema
class DetectionResultResponse(BaseModel):
    """Detection result response."""
    id: str
    investigation_id: str
    baseline_experiment_id: Optional[str]
    attack_experiment_id: Optional[str]
    decision: str
    confidence: float
    explanation: Optional[str]
    evidence_events: List[EvidenceEventResponse]
    created_at: datetime

    class Config:
        from_attributes = True


# Reproducibility Metadata Schema
class ReproducibilityMetadataResponse(BaseModel):
    """Reproducibility metadata response."""
    id: str
    experiment_id: str
    config_hash: str
    seed: Optional[int]
    simulator: str
    simulator_version: Optional[str]
    noise_model: Optional[str]
    is_reproducible: bool
    replay_timestamp: Optional[datetime]
    replay_result: Optional[str]

    class Config:
        from_attributes = True


# Full Investigation Detail Schema
class InvestigationDetailResponse(BaseModel):
    """Full investigation with all related data."""
    id: str
    name: str
    description: Optional[str]
    protocol: str
    status: str
    created_at: datetime
    experiments: List[ExperimentResponse]
    detection_results: List[DetectionResultResponse]

    class Config:
        from_attributes = True


# Comparison Response
class ComparisonResponse(BaseModel):
    """Comparison between two experiments."""
    baseline_id: str
    attack_id: str
    baseline_measurements: Dict[str, float]
    attack_measurements: Dict[str, float]
    tv_distance: float
    fidelity_delta: float
    baseline_verdict: Optional[str]
    attack_verdict: Optional[str]
    signals_triggered: List[str]


# System Status Response
class SystemStatusResponse(BaseModel):
    """System health and status."""
    backend: str  # online, offline
    database: str  # connected, disconnected
    queue_depth: int
    uptime_seconds: float
    last_sync: datetime
    version: str
