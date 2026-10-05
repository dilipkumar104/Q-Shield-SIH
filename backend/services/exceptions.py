"""Domain-specific exceptions for Quantum Kavach services."""


class QuantumKavachException(Exception):
    """Base exception for Quantum Kavach domain errors."""
    pass


class InvestigationNotFound(QuantumKavachException):
    """Investigation does not exist."""
    def __init__(self, investigation_id: str):
        self.investigation_id = investigation_id
        super().__init__(f"Investigation {investigation_id} not found")


class ExperimentNotFound(QuantumKavachException):
    """Experiment does not exist."""
    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        super().__init__(f"Experiment {experiment_id} not found")


class QuantumExecutionFailed(QuantumKavachException):
    """Quantum simulation execution failed."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Quantum execution failed: {reason}")


class DetectionFailed(QuantumKavachException):
    """Detection engine execution failed."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Detection failed: {reason}")


class ReproducibilityFailed(QuantumKavachException):
    """Experiment replay/reproducibility check failed."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Reproducibility check failed: {reason}")


class InvalidConfiguration(QuantumKavachException):
    """Invalid configuration provided."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Invalid configuration: {reason}")
