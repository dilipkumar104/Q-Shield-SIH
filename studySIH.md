# Quantum Kavach study guide

This is a learning map for the SIH26141 project. Quantum Kavach is a local web application that demonstrates how a quantum-communication baseline can be compared with an altered measurement result, then recorded as forensic evidence.

## The big picture

```text
Browser dashboard (Next.js, port 3000)
        |
        | HTTP requests
        v
FastAPI backend (port 8000)
        |
        +--> quantum/       simulate and measure a state
        +--> attacks/       perturb that state
        +--> detection/     compare distributions statistically
        +--> services/      coordinate work and write records
        +--> SQLite         investigations, experiments, results, evidence
```

The normal user journey is:

1. Select a source state, number of measurement shots, and a reproducibility seed.
2. Run a **baseline**. This creates an investigation and stores the expected measurement result.
3. Choose an attack and its intensity.
4. Run the attack test. The backend measures the perturbed state.
5. Run detection. The detector compares baseline and attack distributions, makes a verdict, and writes evidence events.
6. Export the evidence JSON for review.

## How to run it

On Windows, run `run_app.bat` from the repository root. It creates the Python environment, installs packages, and starts both servers.

For manual startup:

```powershell
# terminal 1
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py

# terminal 2
cd frontend
npm install
npm run dev
```

Then open `http://localhost:3000`. Backend API documentation is available at `http://localhost:8000/docs`.

## Folder map

| Location | What it owns |
| --- | --- |
| `frontend/app/page.tsx` | The interactive dashboard and the baseline → attack → detect workflow. |
| `frontend/lib/api.ts` | Typed Axios client. It translates UI requests into FastAPI query parameters. |
| `frontend/app/layout.tsx` | Shared dashboard shell: header and sidebar. |
| `backend/main.py` | FastAPI application setup, middleware, health route, and legacy APIs. |
| `backend/routes/` | HTTP endpoints for investigations, experiments, detection, and evidence. |
| `backend/services/` | Application logic that joins database records, simulation, attack, and detection. |
| `backend/quantum/` | State representations, gates, and teleportation simulation. |
| `backend/attacks/` | Attack implementations registered by attack type. |
| `backend/detection/` | Statistical threat detector and metrics. |
| `backend/models/` | Pydantic request/response schemas and SQLAlchemy database models. |
| `backend/db.py` | SQLite connection/session setup and schema initialization. |
| `quantum_kavach.db` | Local SQLite database; it accumulates investigation history. |

## The data model

An **Investigation** is the parent record for one security analysis. It has many **Experiments**. An experiment is either `baseline` or `attack` and owns one **QuantumResult** (counts, probabilities, fidelity, optional circuit text). A comparison creates a **DetectionResult**, which owns several **EvidenceEvent** entries. The evidence events are the audit-friendly facts behind the final verdict.

```text
Investigation
 ├─ Experiment (baseline) ─ QuantumResult
 ├─ Experiment (attack)   ─ QuantumResult
 └─ DetectionResult
     └─ EvidenceEvent[]
```

## Important concepts

- **Quantum state**: The source state selected in the UI: `|0>`, `|1>`, `|+>`, or `|->`.
- **Shots**: The number of repeated measurements. More shots make the observed distribution less noisy but take longer.
- **Seed**: A fixed random input. Reusing it makes experiments easier to reproduce.
- **Measurement counts**: How many times each outcome appeared. Dividing counts by shots produces probabilities.
- **Fidelity**: A similarity measure. In this project, lower fidelity after an attack signals degradation.
- **Total variation distance**: A measure of how far two probability distributions are apart. The default detector threshold is `0.15`.
- **Evidence event**: One persisted observation, such as baseline fidelity, attack fidelity, fidelity degradation, or the statistical-test result.

## Main API workflow

All investigation routes use the `/api/v1` prefix. Their input values are query parameters, which is why `frontend/lib/api.ts` sends them with Axios `params` rather than a JSON request body.

| Action | Endpoint |
| --- | --- |
| Create investigation | `POST /investigations` |
| Run baseline | `POST /investigations/{id}/experiments/baseline` |
| Run attack | `POST /investigations/{id}/experiments/attack` |
| Detect threat | `POST /investigations/{id}/detect` |
| Read evidence | `GET /investigations/{id}/evidence` |

## What the dashboard controls do

- **Save CFG / Load CFG** save and restore the current UI configuration in the browser's local storage.
- **Export QASM 3.0** downloads the displayed teleportation circuit description.
- **Run Quantum Baseline** creates a backend investigation and executes a real baseline request. Errors are shown in the UI; fake fallback values are not used.
- **Run Attack Lab & Export Evidence** runs the selected attack against the saved baseline, calls the detection route, shows the verdict, and downloads the returned evidence as JSON.

## Where to start reading code

For the fastest learning path, read in this order:

1. `frontend/app/page.tsx` to see the user workflow.
2. `frontend/lib/api.ts` to see every frontend-to-backend request.
3. `backend/routes/experiments.py` and `backend/routes/evidence.py` to see HTTP inputs and outputs.
4. `backend/services/experiment_service.py` and `backend/services/detection_service.py` for the actual orchestration.
5. `backend/quantum/`, `backend/attacks/`, and `backend/detection/` for the domain logic.
6. `backend/models/domain.py` to understand what is persisted.

## Useful checks while developing

```powershell
cd frontend
npm run type-check
npm run build

cd ..\backend
# after activating the backend virtual environment
python -c "from quantum import simulate_teleportation_signature; print(simulate_teleportation_signature('|0>', 100, 42, 'Z'))"
```

## Current boundaries to keep in mind

This is a hackathon prototype and runs locally. The database is SQLite, the legacy simulation endpoints in `backend/main.py` keep some results in memory, and the dashboard's primary workflow is the investigation-scoped route set. The code labels the simulator as a Qiskit/Aer-style quantum workflow, but the experiment service currently records `numpy_custom` as the execution simulator. Keep that distinction clear in a presentation or report.
