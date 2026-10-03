"""Investigation service for managing investigation lifecycle."""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from models.domain import Investigation
from models.repositories import (
    InvestigationRepository,
    AuditLogRepository,
)
from .exceptions import InvestigationNotFound

logger = logging.getLogger(__name__)


class InvestigationService:
    """Service for investigation operations."""

    def __init__(self, db: Session):
        """Initialize service with database session.

        Args:
            db: SQLAlchemy session
        """
        self.db = db
        self.inv_repo = InvestigationRepository()
        self.audit_repo = AuditLogRepository()

    def create_investigation(
        self,
        name: str,
        description: Optional[str] = None,
        protocol: str = "teleportation_qds",
        created_by: Optional[str] = None,
    ) -> Investigation:
        """Create a new investigation.

        Args:
            name: Investigation name
            description: Optional description
            protocol: Protocol type (default: teleportation_qds)
            created_by: User ID who created it

        Returns:
            Investigation object

        Raises:
            ValueError: If name is empty
        """
        if not name or not name.strip():
            raise ValueError("Investigation name cannot be empty")

        try:
            investigation = self.inv_repo.create(
                self.db,
                name=name,
                description=description,
                protocol=protocol,
                created_by=created_by,
            )

            # Audit log
            self.audit_repo.log(
                self.db,
                action="INVESTIGATION_CREATED",
                result="success",
                user_id=created_by,
                resource_type="Investigation",
                resource_id=investigation.id,
                details=f"Created investigation: {name}",
            )

            logger.info(f"Investigation created: {investigation.id}", extra={"investigation_id": investigation.id})
            return investigation

        except Exception as e:
            self.audit_repo.log(
                self.db,
                action="INVESTIGATION_CREATED",
                result="failure",
                user_id=created_by,
                resource_type="Investigation",
                details=f"Failed to create investigation: {str(e)}",
            )
            logger.error(f"Failed to create investigation: {str(e)}", exc_info=True)
            raise

    def get_investigation(self, investigation_id: str) -> Investigation:
        """Get investigation by ID.

        Args:
            investigation_id: Investigation ID

        Returns:
            Investigation object

        Raises:
            InvestigationNotFound: If investigation does not exist
        """
        investigation = self.inv_repo.get_by_id(self.db, investigation_id)
        if investigation is None:
            raise InvestigationNotFound(investigation_id)
        return investigation

    def get_investigation_with_details(self, investigation_id: str) -> Dict[str, Any]:
        """Get investigation with all related data (experiments, detection, evidence).

        Args:
            investigation_id: Investigation ID

        Returns:
            Dictionary with investigation and all related data

        Raises:
            InvestigationNotFound: If investigation does not exist
        """
        investigation = self.get_investigation(investigation_id)

        # Build response with all related data
        return {
            "id": investigation.id,
            "name": investigation.name,
            "description": investigation.description,
            "protocol": investigation.protocol,
            "status": investigation.status,
            "created_at": investigation.created_at,
            "updated_at": investigation.updated_at,
            "created_by": investigation.created_by,
            "experiments": [
                {
                    "id": exp.id,
                    "type": exp.type,
                    "status": exp.status,
                    "execution_time_ms": exp.execution_time_ms,
                    "error": exp.error,
                    "created_at": exp.created_at,
                    "quantum_result": (
                        {
                            "id": exp.quantum_result.id,
                            "fidelity": exp.quantum_result.fidelity,
                            "measurement_counts": exp.quantum_result.measurement_counts,
                            "measurement_probabilities": exp.quantum_result.measurement_probabilities,
                            "theoretical_probabilities": exp.quantum_result.theoretical_probabilities,
                        }
                        if exp.quantum_result
                        else None
                    ),
                }
                for exp in investigation.experiments
            ],
            "detection_results": [
                {
                    "id": det.id,
                    "decision": det.decision,
                    "confidence": det.confidence,
                    "explanation": det.explanation,
                    "created_at": det.created_at,
                    "evidence_count": len(det.evidence_events),
                }
                for det in investigation.detection_results
            ],
        }

    def list_investigations(
        self, limit: int = 50, offset: int = 0
    ) -> tuple[List[Investigation], int]:
        """List all investigations with pagination.

        Args:
            limit: Number of investigations to return
            offset: Offset for pagination

        Returns:
            Tuple of (investigations list, total count)
        """
        investigations, total = self.inv_repo.get_all(self.db, limit=limit, offset=offset)
        return investigations, total

    def update_status(self, investigation_id: str, status: str) -> Investigation:
        """Update investigation status.

        Args:
            investigation_id: Investigation ID
            status: New status (CREATED, RUNNING, COMPLETED, FAILED)

        Returns:
            Updated Investigation object

        Raises:
            InvestigationNotFound: If investigation does not exist
        """
        investigation = self.get_investigation(investigation_id)

        # Validate status
        valid_statuses = {"setup", "baseline_running", "attack_running", "completed", "failed"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")

        updated = self.inv_repo.update_status(self.db, investigation_id, status)

        # Audit log
        self.audit_repo.log(
            self.db,
            action="INVESTIGATION_STATUS_UPDATED",
            result="success",
            resource_type="Investigation",
            resource_id=investigation_id,
            details=f"Status changed to: {status}",
        )

        logger.info(f"Investigation {investigation_id} status updated to {status}")
        return updated

    def delete_investigation(self, investigation_id: str) -> bool:
        """Delete investigation and all related data.

        Args:
            investigation_id: Investigation ID

        Returns:
            True if deleted, False if not found
        """
        result = self.inv_repo.delete(self.db, investigation_id)

        if result:
            self.audit_repo.log(
                self.db,
                action="INVESTIGATION_DELETED",
                result="success",
                resource_type="Investigation",
                resource_id=investigation_id,
                details=f"Investigation and all related data deleted",
            )
            logger.info(f"Investigation {investigation_id} deleted")

        return result
