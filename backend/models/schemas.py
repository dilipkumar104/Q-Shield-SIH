"""Pydantic data models for API requests/responses."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime


class SimulationConfig(BaseModel):
    """Quantum simulation configuration."""

    state: str = Field(description="Quantum state: |0>, |1>, |+>, |->")
    shots: int = Field(default=2000, ge=100, le=100000, description="Number of measurement shots")
    seed: Optional[int] = Field(default=None, ge=0, le=2147483647, description="Random seed for reproducibility")
    measurement_basis: str = Field(default="Z", description="Measurement basis: Z or X")

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Validate quantum state."""
        valid_states = {"|0>", "|1>", "|+>", "|->"}
        if v not in valid_states:
            raise ValueError(f"State must be one of {valid_states}")
        return v

    @field_validator("measurement_basis")
    @classmethod
    def validate_basis(cls, v: str) -> str:
        """Validate measurement basis."""
        if v not in {"Z", "X"}:
            raise ValueError("Measurement basis must be Z or X")
        return v


class AttackConfig(BaseModel):
    """Attack configuration."""

    attack_type: str = Field(description="Attack type: forgery, impersonation, replay, channel")
    intensity: float = Field(default=0.5, ge=0.0, le=1.0, description="Attack intensity")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Attack-specific parameters")

    @field_validator("attack_type")
    @classmethod
    def validate_attack_type(cls, v: str) -> str:
        """Validate attack type."""
        valid_attacks = {"forgery", "impersonation", "replay", "channel"}
        if v not in valid_attacks:
            raise ValueError(f"Attack type must be one of {valid_attacks}")
        return v


class SimulationRunRequest(BaseModel):
    """Request to run a simulation."""

    protocol: str = Field(default="teleportation_qds", description="Protocol type")
    config: SimulationConfig
    attack: Optional[AttackConfig] = None
    detection_threshold: float = Field(default=0.15, ge=0.0, le=1.0)


class SimulationRunResponse(BaseModel):
    """Response from simulation run."""

    run_id: str
    status: str  # "completed", "failed", "cancelled"
    protocol: str
    shots: int
    measurements: Dict[str, float]
    measurement_counts: Dict[str, int]
    theoretical_probs: Dict[str, float]
    fidelity: Optional[float] = None
    circuit_qasm: Optional[str] = None
    execution_time_ms: float
    timestamp: datetime
    error: Optional[str] = None


class DetectionRequest(BaseModel):
    """Request threat detection on simulation results."""

    observed_distribution: Dict[str, float]
    expected_distribution: Dict[str, float]
    sample_size: int = Field(ge=100, le=100000)
    threshold: float = Field(default=0.15, ge=0.0, le=1.0)
    method: str = Field(default="tv_distance", description="Statistical method")


class DetectionResponse(BaseModel):
    """Threat detection response."""

    run_id: str
    decision: str  # "LEGITIMATE", "SUSPICIOUS", "ATTACK"
    attack_type: Optional[str] = None
    statistic_value: float
    threshold: float
    p_value: Optional[float] = None
    confidence_interval: Optional[tuple[float, float]] = None
    forgery_probability: float
    verification_accuracy: float
    false_accept_rate: float
    false_reject_rate: float
    detection_rate: float
    evidence: list[str]
    explanation: str
    confidence: str  # "high", "medium", "low"
    timestamp: datetime


class AttackSimulationRequest(BaseModel):
    """Request to run attack simulation."""

    base_config: SimulationConfig
    attack_config: AttackConfig
    detection_threshold: float = Field(default=0.15)


class RunHistoryEntry(BaseModel):
    """Historical run entry."""

    run_id: str
    timestamp: datetime
    protocol: str
    state: str
    shots: int
    attack_type: Optional[str] = None
    decision: Optional[str] = None
    execution_time_ms: float


class RunHistoryResponse(BaseModel):
    """List of historical runs."""

    runs: list[RunHistoryEntry]
    total: int
    limit: int
    offset: int


class ComparisonRequest(BaseModel):
    """Request to compare two runs."""

    run_id_1: str
    run_id_2: str


class ComparisonResponse(BaseModel):
    """Comparison results."""

    run_id_1: str
    run_id_2: str
    measurements_1: Dict[str, float]
    measurements_2: Dict[str, float]
    tv_distance: float
    decision_1: str
    decision_2: str
    analysis: str


class ExportRequest(BaseModel):
    """Request to export run."""

    run_id: str
    format: str = Field(default="json", description="Export format: json, csv, markdown")


class ExportResponse(BaseModel):
    """Export response."""

    run_id: str
    format: str
    content: str
    filename: str
