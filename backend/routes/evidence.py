"""Evidence routes for detection results and evidence events."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db import get_db
from services.detection_service import DetectionService
from services.investigation_service import InvestigationService
from services.exceptions import (
    InvestigationNotFound,
    ExperimentNotFound,
    DetectionFailed,
)

router = APIRouter()


@router.post("/investigations/{investigation_id}/detect", status_code=200)
async def run_detection(
    investigation_id: str,
    baseline_experiment_id: str = Query(..., description="Baseline experiment ID"),
    attack_experiment_id: str = Query(..., description="Attack experiment ID"),
    threshold: float = Query(0.15, ge=0.0, le=1.0, description="Detection threshold"),
    method: str = Query("tv_distance", description="Detection method: tv_distance, chi_square, entropy, ks_test"),
    db: Session = Depends(get_db),
):
    """Run detection comparing baseline vs attack experiments.

    Args:
        investigation_id: Investigation ID
        baseline_experiment_id: Baseline experiment ID
        attack_experiment_id: Attack experiment ID
        threshold: Detection threshold (0.0-1.0)
        method: Detection method
        db: Database session

    Returns:
        Dictionary with detection result, decision, confidence, and evidence events

    Raises:
        404: If investigation or experiments not found
        400: If invalid configuration
        500: If detection execution fails
    """
    try:
        service = DetectionService(db)
        result = service.run_detection(
            investigation_id=investigation_id,
            baseline_experiment_id=baseline_experiment_id,
            attack_experiment_id=attack_experiment_id,
            threshold=threshold,
            method=method,
        )
        db.commit()
        return result

    except InvestigationNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExperimentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DetectionFailed as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


@router.get("/investigations/{investigation_id}/detection", status_code=200)
async def get_detection_result(
    investigation_id: str,
    db: Session = Depends(get_db),
):
    """Get detection result for an investigation.

    Args:
        investigation_id: Investigation ID
        db: Database session

    Returns:
        Detection result with decision and confidence

    Raises:
        404: If investigation not found or no detection result exists
        500: If database error
    """
    try:
        inv_service = InvestigationService(db)
        # Verify investigation exists
        inv_service.get_investigation(investigation_id)

        det_service = DetectionService(db)
        detection = det_service.get_detection_result(investigation_id)

        if detection is None:
            raise HTTPException(
                status_code=404,
                detail=f"No detection result found for investigation {investigation_id}",
            )

        return {
            "id": detection.id,
            "investigation_id": detection.investigation_id,
            "decision": detection.decision,
            "confidence": detection.confidence,
            "explanation": detection.explanation,
            "created_at": detection.created_at,
        }

    except HTTPException:
        raise
    except InvestigationNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get detection result: {str(e)}")


@router.get("/investigations/{investigation_id}/evidence", status_code=200)
async def get_evidence_events(
    investigation_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """Get all evidence events for an investigation.

    Args:
        investigation_id: Investigation ID
        limit: Number of events to return (1-1000, default 100)
        offset: Offset for pagination (default 0)
        db: Database session

    Returns:
        Dictionary with evidence events and summary

    Raises:
        404: If investigation not found
        500: If database error
    """
    try:
        inv_service = InvestigationService(db)
        # Verify investigation exists
        inv_service.get_investigation(investigation_id)

        det_service = DetectionService(db)
        detection = det_service.get_detection_result(investigation_id)

        if detection is None:
            return {
                "events": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "summary": "No evidence events recorded for this investigation.",
            }

        # Get events (all for now, pagination can be added to repository)
        all_events = det_service.get_evidence_events(detection.id)
        events = all_events[offset : offset + limit]

        # Build summary
        event_types = {}
        verdicts = {"pass": 0, "fail": 0}
        for evt in all_events:
            event_types[evt.signal_type] = event_types.get(evt.signal_type, 0) + 1
            if evt.verdict:
                verdicts[evt.verdict] = verdicts.get(evt.verdict, 0) + 1

        type_summary = ", ".join([f"{count} {type_name}" for type_name, count in event_types.items()])
        summary = (
            f"{len(all_events)} evidence events: {type_summary}. "
            f"Pass: {verdicts['pass']}, Fail: {verdicts['fail']}"
        )

        return {
            "events": [
                {
                    "id": evt.id,
                    "event_type": evt.event_type,
                    "source": evt.source,
                    "signal_type": evt.signal_type,
                    "value": evt.value,
                    "unit": evt.unit,
                    "threshold": evt.threshold,
                    "p_value": evt.p_value,
                    "verdict": evt.verdict,
                    "timestamp": evt.timestamp,
                }
                for evt in events
            ],
            "total": len(all_events),
            "limit": limit,
            "offset": offset,
            "summary": summary,
        }

    except InvestigationNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get evidence events: {str(e)}")


@router.get("/investigations/{investigation_id}/evidence/explanation", status_code=200)
async def get_evidence_explanation(
    investigation_id: str,
    db: Session = Depends(get_db),
):
    """Get human-readable explanation of evidence for an investigation.

    Args:
        investigation_id: Investigation ID
        db: Database session

    Returns:
        Dictionary with explanation text

    Raises:
        404: If investigation not found or no detection result exists
        500: If database error
    """
    try:
        inv_service = InvestigationService(db)
        # Verify investigation exists
        inv_service.get_investigation(investigation_id)

        det_service = DetectionService(db)
        detection = det_service.get_detection_result(investigation_id)

        if detection is None:
            raise HTTPException(
                status_code=404,
                detail=f"No detection result found for investigation {investigation_id}",
            )

        explanation = det_service.get_evidence_explanation(detection.id)

        return {
            "investigation_id": investigation_id,
            "detection_id": detection.id,
            "decision": detection.decision,
            "confidence": detection.confidence,
            "explanation": explanation,
        }

    except HTTPException:
        raise
    except InvestigationNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get evidence explanation: {str(e)}")
