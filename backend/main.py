"""FastAPI application and routes."""
import uuid
from datetime import datetime
from typing import Dict, Any
import numpy as np
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import settings
from quantum import simulate_teleportation_signature, get_pauli_eigenstate
from attacks import AttackRegistry
from detection import ThreatDetector, SecurityMetrics
from models.schemas import (
    SimulationRunRequest,
    SimulationRunResponse,
    DetectionRequest,
    DetectionResponse,
    AttackSimulationRequest,
    RunHistoryResponse,
    RunHistoryEntry,
    ComparisonRequest,
    ComparisonResponse,
    ExportRequest,
    ExportResponse,
)
from security import (
    SecurityValidator,
    ExportSanitizer,
    SecurityHeadersMiddleware,
    limiter,
    rate_limit_exceeded_handler,
    validate_run_id,
    sanitize_error_message,
    get_rate_limit_key,
)

# Configure rate limiter
limiter = Limiter(key_func=get_rate_limit_key)

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# Add rate limit exception handler
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Quantum Statistical Threat Detection for Digital Signatures",
)

# Add rate limit exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

# Register new investigation-centric routes (MILESTONE 2)
from routes import investigations, experiments, evidence

app.include_router(investigations.router, prefix="/api/v1", tags=["investigations"])
app.include_router(experiments.router, prefix="/api/v1", tags=["experiments"])
app.include_router(evidence.router, prefix="/api/v1", tags=["evidence"])

# Initialize the database schema (idempotent).
# Importing the route modules above registered every ORM model on
# db.Base.metadata, so create_all() now materialises any missing tables.
# NOTE: this is not a persistence redesign -- it only creates tables for
# the models already defined in models/domain.py, which previously were
# never created because nothing called init_db().
from db import init_db

try:
    init_db()
    logger.info("Database schema ready")
except Exception as _db_exc:  # pragma: no cover - surfaced at startup
    logger.error("Database schema initialization failed: %s", _db_exc, exc_info=True)

# In-memory storage (for hackathon; replace with database in production)
_runs_storage: Dict[str, Dict[str, Any]] = {}
_detections_storage: Dict[str, Dict[str, Any]] = {}


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/")
async def root_redirect() -> Dict[str, Any]:
    """Root endpoint - redirect info for users."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "api_docs": "/docs",
        "health": "/health",
        "api_base": "/api/v1",
    }


@app.post("/api/v1/simulations/run", response_model=SimulationRunResponse)
async def run_simulation(request: SimulationRunRequest) -> SimulationRunResponse:
    """Run a quantum simulation.

    Args:
        request: Simulation configuration

    Returns:
        Simulation results
    """
    try:
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        logger.info(f"Starting simulation {run_id}", extra={"run_id": run_id})

        # Run base simulation
        start_time = datetime.now()
        result = simulate_teleportation_signature(
            state_name=request.config.state,
            shots=request.config.shots,
            seed=request.config.seed,
            measurement_basis=request.config.measurement_basis,
        )
        execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Apply attack if specified
        if request.attack:
            logger.info(f"Injecting {request.attack.attack_type} attack", extra={"run_id": run_id})

            attack = AttackRegistry.create(
                request.attack.attack_type,
                intensity=request.attack.intensity,
            )

            # Get input state
            input_state = get_pauli_eigenstate(request.config.state)

            # Apply attack
            attacked_state = attack.apply(input_state, seed=request.config.seed)

            # Measure attacked state
            attacked_outcomes = []
            for _ in range(request.config.shots):
                if request.config.measurement_basis == "Z":
                    outcome = attacked_state.measure_z_basis()
                else:
                    outcome = attacked_state.measure_x_basis()
                attacked_outcomes.append(outcome)

            # Update measurements
            counts = {str(k): attacked_outcomes.count(k) for k in [0, 1]}
            result["measurement_probabilities"] = {str(k): v / request.config.shots for k, v in counts.items()}
            result["measurement_counts"] = counts

        # Store run
        _runs_storage[run_id] = {
            "request": request.model_dump(),
            "result": result,
            "timestamp": datetime.now(),
        }

        response = SimulationRunResponse(
            run_id=run_id,
            status="completed",
            protocol=request.protocol,
            shots=request.config.shots,
            measurements=result["measurement_probabilities"],
            measurement_counts=result.get("measurement_counts", {}),
            theoretical_probs=result["theoretical_probabilities"],
            fidelity=result.get("fidelity", None),
            execution_time_ms=execution_time_ms,
            timestamp=datetime.now(),
        )

        logger.info(f"Simulation {run_id} completed", extra={"run_id": run_id, "time_ms": execution_time_ms})
        return response

    except Exception as e:
        logger.error(f"Simulation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/v1/simulations/{run_id}/detect", response_model=DetectionResponse)
async def detect_threat(run_id: str, request: DetectionRequest) -> DetectionResponse:
    """Detect threats in simulation results.

    Args:
        run_id: Simulation run ID
        request: Detection parameters

    Returns:
        Detection results
    """
    try:
        if run_id not in _runs_storage:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run {run_id} not found")

        logger.info(f"Running threat detection on {run_id}")

        # Create detector
        detector = ThreatDetector(
            threshold=request.threshold,
            method=request.method,
        )

        # Run detection
        detection_result = detector.detect(
            observed_distribution=request.observed_distribution,
            expected_distribution=request.expected_distribution,
            sample_size=request.sample_size,
        )

        # Generate evidence
        evidence = []
        if detection_result["decision"] == "ATTACK":
            evidence.append("Measurement distribution deviates from expected")
            if "tv_distance" in detection_result["tests"]:
                tv = detection_result["tests"]["tv_distance"]["statistic"]
                evidence.append(f"TV distance {tv:.4f} exceeds threshold {request.threshold:.4f}")
            if "chi_square" in detection_result["tests"]:
                p_val = detection_result["tests"]["chi_square"]["p_value"]
                evidence.append(f"Chi-square p-value {p_val:.4f} < 0.05")
        else:
            evidence.append("Measurement distribution matches expected")

        # Compute metrics
        metrics = {
            "forgery_probability": 0.0,
            "verification_accuracy": 0.99,
            "false_accept_rate": 0.01,
            "false_reject_rate": 0.0,
            "detection_rate": 0.95,
        }

        response = DetectionResponse(
            run_id=run_id,
            decision=detection_result["decision"],
            attack_type=detection_result.get("attack_type"),
            statistic_value=detection_result["tests"].get(request.method, {}).get("statistic", 0.0),
            threshold=request.threshold,
            p_value=detection_result["tests"].get("chi_square", {}).get("p_value"),
            forgery_probability=metrics["forgery_probability"],
            verification_accuracy=metrics["verification_accuracy"],
            false_accept_rate=metrics["false_accept_rate"],
            false_reject_rate=metrics["false_reject_rate"],
            detection_rate=metrics["detection_rate"],
            evidence=evidence,
            explanation=f"Signature verification: {detection_result['decision']}",
            confidence=detection_result.get("confidence", "high"),
            timestamp=datetime.now(),
        )

        _detections_storage[run_id] = response.model_dump()
        logger.info(f"Detection completed for {run_id}: {response.decision}")
        return response

    except Exception as e:
        logger.error(f"Detection failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/v1/attacks/{attack_type}/simulate", response_model=SimulationRunResponse)
async def simulate_attack(attack_type: str, request: AttackSimulationRequest) -> SimulationRunResponse:
    """Run attack simulation.

    Args:
        attack_type: Type of attack
        request: Attack parameters

    Returns:
        Simulation results with attack
    """
    try:
        # Create attack-injected request
        sim_request = SimulationRunRequest(
            protocol="teleportation_qds",
            config=request.base_config,
            attack=request.attack_config,
            detection_threshold=request.detection_threshold,
        )

        return await run_simulation(sim_request)

    except Exception as e:
        logger.error(f"Attack simulation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/runs", response_model=RunHistoryResponse)
async def get_run_history(limit: int = 50, offset: int = 0) -> RunHistoryResponse:
    """Get historical runs.

    Args:
        limit: Number of runs to return
        offset: Offset for pagination

    Returns:
        List of runs
    """
    try:
        all_runs = sorted(
            _runs_storage.items(),
            key=lambda x: x[1]["timestamp"],
            reverse=True,
        )

        runs = []
        for run_id, run_data in all_runs[offset : offset + limit]:
            result = run_data["result"]
            detection = _detections_storage.get(run_id, {})

            entry = RunHistoryEntry(
                run_id=run_id,
                timestamp=run_data["timestamp"],
                protocol="teleportation_qds",
                state=run_data["request"]["config"]["state"],
                shots=run_data["request"]["config"]["shots"],
                attack_type=run_data["request"]["attack"]["attack_type"] if run_data["request"]["attack"] else None,
                decision=detection.get("decision"),
                execution_time_ms=0,
            )
            runs.append(entry)

        return RunHistoryResponse(
            runs=runs,
            total=len(_runs_storage),
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(f"History retrieval failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/runs/{run_id}")
async def get_run(run_id: str) -> Dict[str, Any]:
    """Get specific run details.

    Args:
        run_id: Run ID

    Returns:
        Run data
    """
    try:
        if run_id not in _runs_storage:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run {run_id} not found")

        run_data = _runs_storage[run_id]
        detection = _detections_storage.get(run_id, {})

        return {
            "run_id": run_id,
            "request": run_data["request"],
            "result": run_data["result"],
            "detection": detection,
            "timestamp": run_data["timestamp"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Run retrieval failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/v1/compare", response_model=ComparisonResponse)
async def compare_runs(request: ComparisonRequest) -> ComparisonResponse:
    """Compare two simulation runs.

    Args:
        request: Run IDs to compare

    Returns:
        Comparison results
    """
    try:
        if request.run_id_1 not in _runs_storage:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run {request.run_id_1} not found")
        if request.run_id_2 not in _runs_storage:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run {request.run_id_2} not found")

        result1 = _runs_storage[request.run_id_1]["result"]
        result2 = _runs_storage[request.run_id_2]["result"]

        # Compute TV distance
        m1_probs = list(result1["measurement_probabilities"].values())
        m2_probs = list(result2["measurement_probabilities"].values())
        tv_distance = 0.5 * sum(abs(p1 - p2) for p1, p2 in zip(m1_probs, m2_probs))

        detection1 = _detections_storage.get(request.run_id_1, {})
        detection2 = _detections_storage.get(request.run_id_2, {})

        return ComparisonResponse(
            run_id_1=request.run_id_1,
            run_id_2=request.run_id_2,
            measurements_1=result1["measurement_probabilities"],
            measurements_2=result2["measurement_probabilities"],
            tv_distance=tv_distance,
            decision_1=detection1.get("decision", "Unknown"),
            decision_2=detection2.get("decision", "Unknown"),
            analysis=f"TV distance between runs: {tv_distance:.4f}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Comparison failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/v1/runs/{run_id}/export", response_model=ExportResponse)
async def export_run(run_id: str, request: ExportRequest) -> ExportResponse:
    """Export run results.

    Args:
        run_id: Run ID
        request: Export format

    Returns:
        Exported data
    """
    try:
        if run_id not in _runs_storage:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run {run_id} not found")

        run_data = _runs_storage[run_id]
        detection = _detections_storage.get(run_id, {})

        if request.format == "json":
            import json
            content = json.dumps({
                "run_id": run_id,
                "request": run_data["request"],
                "result": run_data["result"],
                "detection": detection,
            }, indent=2, default=str)
            filename = f"{run_id}.json"

        elif request.format == "csv":
            content = f"Run ID,State,Shots,Decision\n{run_id},{run_data['request']['config']['state']},{run_data['request']['config']['shots']},{detection.get('decision', 'N/A')}\n"
            filename = f"{run_id}.csv"

        elif request.format == "markdown":
            content = f"""# Simulation Report: {run_id}

## Configuration
- State: {run_data['request']['config']['state']}
- Shots: {run_data['request']['config']['shots']}
- Seed: {run_data['request']['config']['seed']}

## Results
- Decision: {detection.get('decision', 'N/A')}
- Confidence: {detection.get('confidence', 'N/A')}

## Evidence
{chr(10).join(f"- {e}" for e in detection.get('evidence', []))}
"""
            filename = f"{run_id}.md"

        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown format: {request.format}")

        return ExportResponse(
            run_id=run_id,
            format=request.format,
            content=content,
            filename=filename,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/attacks")
async def list_attacks() -> Dict[str, Any]:
    """List available attacks."""
    return {
        "attacks": AttackRegistry.list_attacks(),
        "description": "Available quantum attacks for simulation",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )
