"""Experiment routes for baseline and attack experiments."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db import get_db
from services.experiment_service import ExperimentService
from services.exceptions import (
    InvestigationNotFound,
    ExperimentNotFound,
    InvalidConfiguration,
    QuantumExecutionFailed,
)

router = APIRouter()


@router.post("/investigations/{investigation_id}/experiments/baseline", status_code=200)
async def run_baseline_experiment(
    investigation_id: str,
    state: str = Query(..., description="Quantum state: |0>, |1>, |+>, |->"),
    shots: int = Query(..., ge=100, le=100000, description="Number of measurement shots"),
    seed: int = Query(None, description="Random seed for reproducibility"),
    measurement_basis: str = Query("Z", description="Measurement basis: Z or X"),
    db: Session = Depends(get_db),
):
    """Run a baseline quantum experiment.

    Args:
        investigation_id: Investigation ID
        state: Quantum state
        shots: Number of measurement shots
        seed: Random seed (optional)
        measurement_basis: Measurement basis (Z or X)
        db: Database session

    Returns:
        Dictionary with experiment ID, status, execution time, and quantum result

    Raises:
        404: If investigation not found
        400: If invalid configuration
        500: If quantum execution fails
    """
    try:
        service = ExperimentService(db)
        result = service.run_baseline_experiment(
            investigation_id=investigation_id,
            state=state,
            shots=shots,
            seed=seed,
            measurement_basis=measurement_basis,
        )
        db.commit()
        return result

    except InvestigationNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidConfiguration as e:
        raise HTTPException(status_code=400, detail=str(e))
    except QuantumExecutionFailed as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Baseline experiment failed: {str(e)}")


@router.post("/investigations/{investigation_id}/experiments/attack", status_code=200)
async def run_attack_experiment(
    investigation_id: str,
    baseline_experiment_id: str = Query(..., description="Baseline experiment ID"),
    state: str = Query(..., description="Quantum state: |0>, |1>, |+>, |->"),
    shots: int = Query(..., ge=100, le=100000, description="Number of measurement shots"),
    attack_type: str = Query(..., description="Attack type: forgery, impersonation, replay, channel"),
    attack_intensity: float = Query(0.5, ge=0.0, le=1.0, description="Attack intensity (0.0-1.0)"),
    seed: int = Query(None, description="Random seed (optional)"),
    measurement_basis: str = Query("Z", description="Measurement basis: Z or X"),
    db: Session = Depends(get_db),
):
    """Run an attack experiment.

    Args:
        investigation_id: Investigation ID
        baseline_experiment_id: Baseline experiment ID for comparison
        state: Quantum state
        shots: Number of measurement shots
        attack_type: Type of attack
        attack_intensity: Attack intensity (0.0-1.0)
        seed: Random seed (optional)
        measurement_basis: Measurement basis (Z or X)
        db: Database session

    Returns:
        Dictionary with experiment ID, status, execution time, quantum result, and detection result

    Raises:
        404: If investigation or baseline experiment not found
        400: If invalid configuration
        500: If quantum execution fails
    """
    try:
        service = ExperimentService(db)
        result = service.run_attack_experiment(
            investigation_id=investigation_id,
            baseline_experiment_id=baseline_experiment_id,
            state=state,
            shots=shots,
            attack_type=attack_type,
            attack_intensity=attack_intensity,
            seed=seed,
            measurement_basis=measurement_basis,
        )
        db.commit()
        return result

    except InvestigationNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExperimentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidConfiguration as e:
        raise HTTPException(status_code=400, detail=str(e))
    except QuantumExecutionFailed as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Attack experiment failed: {str(e)}")


@router.get("/investigations/{investigation_id}/experiments", status_code=200)
async def list_experiments(
    investigation_id: str,
    db: Session = Depends(get_db),
):
    """List all experiments for an investigation.

    Args:
        investigation_id: Investigation ID
        db: Database session

    Returns:
        Dictionary with list of experiments

    Raises:
        404: If investigation not found
        500: If database error
    """
    try:
        service = ExperimentService(db)
        # Verify investigation exists
        service.investigation_service.get_investigation(investigation_id)

        experiments = service.get_experiments_by_investigation(investigation_id)

        return {
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
                for exp in experiments
            ]
        }

    except InvestigationNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list experiments: {str(e)}")


@router.get("/investigations/{investigation_id}/experiments/{experiment_id}", status_code=200)
async def get_experiment(
    investigation_id: str,
    experiment_id: str,
    db: Session = Depends(get_db),
):
    """Get a specific experiment.

    Args:
        investigation_id: Investigation ID
        experiment_id: Experiment ID
        db: Database session

    Returns:
        Experiment details

    Raises:
        404: If investigation or experiment not found
        500: If database error
    """
    try:
        service = ExperimentService(db)
        # Verify investigation exists
        service.investigation_service.get_investigation(investigation_id)

        experiment = service.get_experiment(experiment_id)

        return {
            "id": experiment.id,
            "type": experiment.type,
            "status": experiment.status,
            "execution_time_ms": experiment.execution_time_ms,
            "error": experiment.error,
            "created_at": experiment.created_at,
            "config": experiment.config,
            "quantum_result": (
                {
                    "id": experiment.quantum_result.id,
                    "fidelity": experiment.quantum_result.fidelity,
                    "measurement_counts": experiment.quantum_result.measurement_counts,
                    "measurement_probabilities": experiment.quantum_result.measurement_probabilities,
                    "theoretical_probabilities": experiment.quantum_result.theoretical_probabilities,
                    "circuit_qasm": experiment.quantum_result.circuit_qasm,
                }
                if experiment.quantum_result
                else None
            ),
        }

    except InvestigationNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ExperimentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get experiment: {str(e)}")
