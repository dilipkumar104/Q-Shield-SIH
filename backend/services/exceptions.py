"""Domain-specific exceptions for Q-SHIELD services."""


class QShieldException(Exception):
    """Base exception for Q-SHIELD domain errors."""
    pass


class InvestigationNotFound(QShieldException):
    """Investigation does not exist."""
    def __init__(self, investigation_id: str):
        self.investigation_id = investigation_id
        super().__init__(f"Investigation {investigation_id} not found")


class ExperimentNotFound(QShieldException):
    """Experiment does not exist."""
    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        super().__init__(f"Experiment {experiment_id} not found")


class QuantumExecutionFailed(QShieldException):
    """Quantum simulation execution failed."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Quantum execution failed: {reason}")


class DetectionFailed(QShieldException):
    """Detection engine execution failed."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Detection failed: {reason}")


class ReproducibilityFailed(QShieldException):
    """Experiment replay/reproducibility check failed."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Reproducibility check failed: {reason}")


class InvalidConfiguration(QShieldException):
    """Invalid configuration provided."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Invalid configuration: {reason}")
