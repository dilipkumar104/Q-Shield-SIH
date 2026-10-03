"""Investigation routes for CRUD operations."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db import get_db
from models.response_schemas import (
    InvestigationResponse,
    SystemStatusResponse,
)
from services.investigation_service import InvestigationService
from services.exceptions import InvestigationNotFound

router = APIRouter()


@router.post("/investigations", response_model=InvestigationResponse, status_code=201)
async def create_investigation(
    name: str,
    description: str = None,
    protocol: str = "teleportation_qds",
    db: Session = Depends(get_db),
):
    """Create a new investigation.

    Args:
        name: Investigation name
        description: Optional description
        protocol: Protocol type (default: teleportation_qds)
        db: Database session

    Returns:
        InvestigationResponse

    Raises:
        400: If name is empty
        500: If database error
    """
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Investigation name cannot be empty")

    try:
        service = InvestigationService(db)
        investigation = service.create_investigation(
            name=name,
            description=description,
            protocol=protocol,
            created_by="api_user",
        )
        db.commit()

        return InvestigationResponse(
            id=investigation.id,
            name=investigation.name,
            description=investigation.description,
            protocol=investigation.protocol,
            status=investigation.status,
            created_at=investigation.created_at,
            updated_at=investigation.updated_at,
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create investigation: {str(e)}")


@router.get("/investigations", response_model=dict)
async def list_investigations(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List all investigations with pagination.

    Args:
        limit: Number of investigations to return (1-1000, default 50)
        offset: Offset for pagination (default 0)
        db: Database session

    Returns:
        Dictionary with investigations list, total count, limit, offset

    Raises:
        500: If database error
    """
    try:
        service = InvestigationService(db)
        investigations, total = service.list_investigations(limit=limit, offset=offset)

        return {
            "investigations": [
                InvestigationResponse(
                    id=inv.id,
                    name=inv.name,
                    description=inv.description,
                    protocol=inv.protocol,
                    status=inv.status,
                    created_at=inv.created_at,
                    updated_at=inv.updated_at,
                )
                for inv in investigations
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list investigations: {str(e)}")


@router.get("/investigations/{investigation_id}", response_model=dict)
async def get_investigation(
    investigation_id: str,
    db: Session = Depends(get_db),
):
    """Get investigation with all related data.

    Args:
        investigation_id: Investigation ID
        db: Database session

    Returns:
        Investigation with experiments, detection results, evidence

    Raises:
        404: If investigation not found
        500: If database error
    """
    try:
        service = InvestigationService(db)
        investigation_data = service.get_investigation_with_details(investigation_id)
        return investigation_data
    except InvestigationNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get investigation: {str(e)}")


@router.put("/investigations/{investigation_id}/status", response_model=InvestigationResponse)
async def update_investigation_status(
    investigation_id: str,
    status: str,
    db: Session = Depends(get_db),
):
    """Update investigation status.

    Args:
        investigation_id: Investigation ID
        status: New status (setup, baseline_running, attack_running, completed, failed)
        db: Database session

    Returns:
        Updated InvestigationResponse

    Raises:
        404: If investigation not found
        400: If invalid status
        500: If database error
    """
    valid_statuses = {"setup", "baseline_running", "attack_running", "completed", "failed"}
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of {valid_statuses}",
        )

    try:
        service = InvestigationService(db)
        investigation = service.update_status(investigation_id, status)
        db.commit()

        return InvestigationResponse(
            id=investigation.id,
            name=investigation.name,
            description=investigation.description,
            protocol=investigation.protocol,
            status=investigation.status,
            created_at=investigation.created_at,
            updated_at=investigation.updated_at,
        )
    except InvestigationNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update investigation: {str(e)}")


@router.delete("/investigations/{investigation_id}", status_code=204)
async def delete_investigation(
    investigation_id: str,
    db: Session = Depends(get_db),
):
    """Delete investigation and all related data.

    Args:
        investigation_id: Investigation ID
        db: Database session

    Raises:
        404: If investigation not found
        500: If database error
    """
    try:
        service = InvestigationService(db)
        result = service.delete_investigation(investigation_id)
        db.commit()

        if not result:
            raise HTTPException(status_code=404, detail=f"Investigation {investigation_id} not found")

        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete investigation: {str(e)}")
