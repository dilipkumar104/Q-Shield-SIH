# Q-SHIELD — Quantum Threat Detection Dashboard

> **SIH26141** · Smart India Hackathon 2026 · Egreen Quanta  
> Blockchain & Cybersecurity Domain

## Quick Start

**Double-click `run_app.bat`** — that's it.

The launcher will:
1. Check that Python 3.10+ and Node.js 18+ are installed
2. Create a Python virtual environment and install backend dependencies (first run only)
3. Install frontend npm packages (first run only)
4. Start the FastAPI backend on `http://localhost:8000`
5. Start the Next.js frontend on `http://localhost:3000`
6. Open the dashboard in your browser

## What is Q-SHIELD?

Q-SHIELD is a **quantum statistical threat detection** system for digital signatures. It uses quantum teleportation protocols simulated via **Qiskit Aer** to establish baselines, then detects eavesdropping attacks through statistical analysis of measurement distributions.

### Key Features

- **Simulation Lab** — Configure and run quantum teleportation experiments (3-qubit, Bennett et al.)
- **Attack Lab** — Inject eavesdropping vectors (Intercept-Resend, Photon Number Splitting, Entanglement Swapping)
- **Statistical Detection** — Chi-squared tests, Total Variation distance, QBER analysis
- **Evidence Forensics** — Tamper-proof evidence chain with SHA-256 ledger
- **Circuit Visualization** — Interactive quantum circuit diagrams (Alice → Fiber → Bob)

### Supported Protocols

| Protocol | Description |
|----------|-------------|
| Teleportation | 3-Qubit Full State Transfer (Bennett et al.) |
| BB84 QKD | Polarization Key Exchange |
| E91 Entangled | CHSH Bell-State Test |
| QDS (Signatures) | Non-Repudiation Triad |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 18, Tailwind CSS |
| Backend | FastAPI, Uvicorn, Pydantic |
| Quantum | Qiskit 1.x, Qiskit Aer 0.13+ |
| Database | SQLite (via SQLAlchemy) |
| Detection | NumPy, SciPy (chi-squared, TV distance) |

## Project Structure

```
SIH26141/
├── backend/           # FastAPI server
│   ├── main.py        # App entry point
│   ├── quantum/       # Qiskit simulation core
│   ├── attacks/       # Attack injection engine
│   ├── detection/     # Statistical threat detection
│   ├── routes/        # API route handlers
│   ├── models/        # Pydantic schemas + ORM
│   └── services/      # Business logic layer
├── frontend/          # Next.js dashboard
│   ├── app/           # Pages and layout
│   ├── components/    # UI components
│   └── lib/           # API client + utilities
├── docs/stitch/       # UI design reference
├── run_app.bat        # One-click launcher
└── README.md
```

## Requirements
- **Python** 3.10 or later
- **Node.js** 18 or later
- **Windows** (for the `.bat` launcher)
