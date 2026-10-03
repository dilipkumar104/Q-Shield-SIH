"""Detection service for running threat detection and generating evidence."""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from models.domain import DetectionResult, EvidenceEvent
from models.repositories import (
    DetectionResultRepository,
    EvidenceEventRepository,
    AuditLogRepository,
    ExperimentRepository,
)
from detection import ThreatDetector
from .exceptions import (
    DetectionFailed,
    ExperimentNotFound,
    InvestigationNotFound,
)
from .investigation_service import InvestigationService

logger = logging.getLogger(__name__)


class DetectionService:
    """Service for detection operations."""

    def __init__(self, db: Session):
        """Initialize service with database session.

        Args:
            db: SQLAlchemy session
        """
        self.db = db
        self.detection_repo = DetectionResultRepository()
        self.evidence_repo = EvidenceEventRepository()
        self.audit_repo = AuditLogRepository()
        self.experiment_repo = ExperimentRepository()
        self.investigation_service = InvestigationService(db)
        self.detector = ThreatDetector()

    def run_detection(
        self,
        investigation_id: str,
        baseline_experiment_id: str,
        attack_experiment_id: str,
        threshold: float = 0.15,
        method: str = "tv_distance",
    ) -> Dict[str, Any]:
        """Run detection comparing baseline vs attack experiments.

        Args:
            investigation_id: Investigation ID
            baseline_experiment_id: Baseline experiment ID
            attack_experiment_id: Attack experiment ID
            threshold: Detection threshold
            method: Detection method (tv_distance, chi_square, entropy, ks_test)

        Returns:
            Dictionary with detection result and evidence

        Raises:
            InvestigationNotFound: If investigation does not exist
            ExperimentNotFound: If experiments do not exist
            DetectionFailed: If detection execution fails
        """
        # Verify investigation exists
        investigation = self.investigation_service.get_investigation(investigation_id)

        # Get experiments
        baseline_exp = self.experiment_repo.get_by_id(self.db, baseline_experiment_id)
        if baseline_exp is None:
            raise ExperimentNotFound(baseline_experiment_id)

        attack_exp = self.experiment_repo.get_by_id(self.db, attack_experiment_id)
        if attack_exp is None:
            raise ExperimentNotFound(attack_experiment_id)

        # Verify experiments have quantum results
        if baseline_exp.quantum_result is None:
            raise DetectionFailed(f"Baseline experiment {baseline_experiment_id} has no quantum result")
        if attack_exp.quantum_result is None:
            raise DetectionFailed(f"Attack experiment {attack_experiment_id} has no quantum result")

        try:
            # Extract measurement distributions
            baseline_probs = baseline_exp.quantum_result.measurement_probabilities
            attack_probs = attack_exp.quantum_result.measurement_probabilities

            logger.info(
                f"Running detection: baseline_fidelity={baseline_exp.quantum_result.fidelity:.4f}, "
                f"attack_fidelity={attack_exp.quantum_result.fidelity:.4f}",
                extra={
                    "investigation_id": investigation_id,
                    "baseline_experiment_id": baseline_experiment_id,
                    "attack_experiment_id": attack_experiment_id,
                    "method": method,
                },
            )

            # Run detection. ThreatDetector is configured per-run from the
            # caller's threshold/method (the instance built in __init__ uses
            # the defaults).
            supported = ("chi_square", "tv_distance", "both")
            detector = ThreatDetector(
                threshold=threshold,
                method=method if method in supported else "tv_distance",
            )

            # Sample size for the statistical tests: total shots in the
            # baseline run (falls back to the config default).
            sample_size = 1000
            counts = getattr(baseline_exp.quantum_result, "measurement_counts", None)
            if isinstance(counts, dict) and counts:
                try:
                    sample_size = int(sum(int(v) for v in counts.values()))
                except (TypeError, ValueError):
                    sample_size = 1000

            raw_result = detector.detect(
                observed_distribution=attack_probs,
                expected_distribution=baseline_probs,
                sample_size=sample_size,
            )

            # ThreatDetector.detect() returns:
            #   {decision, attack_type, confidence (str), tests: {...}}
            tests = raw_result.get("tests", {}) or {}
            tv_test = tests.get("tv_distance", {}) or {}
            chi_test = tests.get("chi_square", {}) or {}

            decision = raw_result.get("decision", "LEGITIMATE")
            conf_raw = raw_result.get("confidence", "high")
            confidence = (
                {"high": 0.9, "medium": 0.6, "low": 0.3}.get(conf_raw, 0.75)
                if isinstance(conf_raw, str)
                else float(conf_raw)
            )

            explanation = (
                f"{decision} by {detector.method}: "
                f"TV distance={tv_test.get('statistic')}, "
                f"chi-square p={chi_test.get('p_value')}, "
                f"sample_size={sample_size}."
            )

            # Normalised detection output, shared with evidence generation.
            detection_result = {
                "decision": decision,
                "method": detector.method,
                "confidence": confidence,
                "tests": tests,
                "explanation": explanation,
            }

            # Create detection result record. DetectionResult has only:
            # id, investigation_id, baseline_experiment_id,
            # attack_experiment_id, decision, confidence, explanation,
            # created_at -- there are no threshold/method/statistics columns.
            detection = self.detection_repo.create(
                self.db,
                investigation_id=investigation_id,
                baseline_exp_id=baseline_experiment_id,
                attack_exp_id=attack_experiment_id,
                decision=decision,
                confidence=confidence,
                explanation=explanation,
            )

            # Generate evidence events
            evidence_events = self._generate_evidence_events(
                detection.id,
                baseline_exp.quantum_result,
                attack_exp.quantum_result,
                detection_result,
                threshold,
            )

            logger.info(
                f"Detection completed: decision={decision}, confidence={confidence:.4f}, "
                f"evidence_count={len(evidence_events)}",
                extra={
                    "investigation_id": investigation_id,
                    "detection_id": detection.id,
                    "decision": decision,
                    "confidence": confidence,
                },
            )

            # Audit log
            self.audit_repo.log(
                self.db,
                action="DETECTION_COMPLETED",
                result="success",
                resource_type="DetectionResult",
                resource_id=detection.id,
                details=f"Detection: {decision}. Confidence: {confidence:.4f}. Evidence events: {len(evidence_events)}",
            )

            return {
                "detection_id": detection.id,
                "decision": decision,
                "confidence": confidence,
                "threshold": threshold,
                "method": method,
                "explanation": detection_result.get("explanation", ""),
                "evidence_count": len(evidence_events),
                "evidence_events": [
                    {
                        "id": evt.id,
                        "event_type": evt.event_type,
                        "signal_type": evt.signal_type,
                        "value": evt.value,
                        "unit": evt.unit,
                        "verdict": evt.verdict,
                        "timestamp": evt.timestamp,
                    }
                    for evt in evidence_events
                ],
            }

        except DetectionFailed:
            raise
        except Exception as e:
            logger.error(f"Detection failed: {str(e)}", exc_info=True)
            self.audit_repo.log(
                self.db,
                action="DETECTION_FAILED",
                result="failure",
                resource_type="DetectionResult",
                resource_id=investigation_id,
                details=f"Error: {str(e)}",
            )
            raise DetectionFailed(f"Detection execution failed: {str(e)}")

    def get_detection_result(self, investigation_id: str) -> Optional[DetectionResult]:
        """Get detection result for an investigation.

        Args:
            investigation_id: Investigation ID

        Returns:
            DetectionResult or None if not found
        """
        return self.detection_repo.get_by_investigation(self.db, investigation_id)

    def get_evidence_events(self, detection_id: str) -> List[EvidenceEvent]:
        """Get all evidence events for a detection.

        Args:
            detection_id: Detection result ID

        Returns:
            List of evidence events
        """
        return self.evidence_repo.get_by_detection(self.db, detection_id)

    def get_evidence_explanation(self, detection_id: str) -> str:
        """Get human-readable explanation of evidence.

        Args:
            detection_id: Detection result ID

        Returns:
            Explanation text
        """
        events = self.get_evidence_events(detection_id)
        if not events:
            return "No evidence events recorded."

        # Build explanation from events
        lines = []
        for evt in events:
            if evt.event_type == "measurement":
                lines.append(
                    f"• {evt.signal_type.replace('_', ' ').title()}: {evt.value:.4f} {evt.unit} "
                    f"({'PASS' if evt.verdict == 'pass' else 'FAIL'})"
                )
            elif evt.event_type == "test_result":
                lines.append(
                    f"• {evt.signal_type.replace('_', ' ').title()}: {evt.value:.4f} {evt.unit} "
                    f"(threshold: {evt.threshold}, p-value: {evt.p_value}) "
                    f"({'PASS' if evt.verdict == 'pass' else 'FAIL'})"
                )

        return "\n".join(lines) if lines else "No evidence details available."

    def _generate_evidence_events(
        self,
        detection_id: str,
        baseline_result: Any,
        attack_result: Any,
        detection_result: Dict[str, Any],
        threshold: float,
    ) -> List[EvidenceEvent]:
        """Generate and persist evidence events from a detection result.

        Args:
            detection_id: Detection result ID
            baseline_result: Baseline QuantumResult
            attack_result: Attack QuantumResult
            detection_result: Normalised detection output
            threshold: Detection threshold

        Returns:
            The persisted EvidenceEvent rows.
        """
        events: List[EvidenceEvent] = []

        def _add(**kwargs: Any) -> None:
            events.append(self.evidence_repo.create(self.db, detection_id=detection_id, **kwargs))

        baseline_fidelity = float(getattr(baseline_result, "fidelity", 0.0) or 0.0)
        attack_fidelity = float(getattr(attack_result, "fidelity", 0.0) or 0.0)
        fidelity_delta = baseline_fidelity - attack_fidelity

        tests = detection_result.get("tests", {}) or {}
        tv_test = tests.get("tv_distance", {}) or {}
        chi_test = tests.get("chi_square", {}) or {}
        statistic_value = tv_test.get("statistic", chi_test.get("statistic"))
        p_value = chi_test.get("p_value")

        # Event 1: Baseline measurement
        _add(
            event_type="measurement",
            source="baseline",
            signal_type="measurement_baseline",
            value=baseline_fidelity,
            unit="fidelity",
            verdict="pass",
        )

        # Event 2: Attack measurement
        _add(
            event_type="measurement",
            source="attack",
            signal_type="measurement_attack",
            value=attack_fidelity,
            unit="fidelity",
            verdict="pass" if attack_fidelity >= 0.5 else "fail",
        )

        # Event 3: Fidelity degradation
        _add(
            event_type="test_result",
            source="comparison",
            signal_type="fidelity_degradation",
            value=fidelity_delta,
            unit="fidelity_delta",
            threshold=0.1,
            verdict="fail" if fidelity_delta > 0.1 else "pass",
        )

        # Event 4: Statistical test result
        if statistic_value is not None:
            _add(
                event_type="test_result",
                source="statistical_test",
                signal_type=f"{detection_result.get('method', 'tv_distance')}_test",
                value=float(statistic_value),
                unit="test_statistic",
                threshold=threshold,
                p_value=float(p_value) if p_value is not None else None,
                test_statistic=float(statistic_value),
                verdict="fail" if detection_result.get("decision") == "ATTACK" else "pass",
            )

        return events
