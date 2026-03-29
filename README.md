# RCA Copilot (Hybrid Architecture)

This repository implements a **Hybrid RCA Copilot** system using a high-performance Python-based analytical engine and a .NET-based production control plane.

## Architecture Overview

1.  **Python Analytical Engine (`api.py`)**: FastAPI service that executes the core RCA pipeline, AOGC adaptation, and Continuous Epistemic Falsification (CEF).
2.  **NET Control Plane (`services/control-plane/`)**: Production orchestrator that polls a shared telemetry folder and delegates analysis to the Python API.
3.  **Streamlit Dashboard (`app.py`)**: UI for visualizing RCA results, health claims, contradictions, and the falsification ledger.
4.  **Shared Run Folder**: A common staging area for telemetry bundles (alerts, logs, metrics).

---

## Getting Started

### 1. Prerequisites
- Python 3.9+
- .NET 8 SDK
- Streamlit

### 2. Startup Order (Local Development)

1.  **Start Python Analytical Engine**:
    ```bash
    pip install -r requirements.txt
    PYTHONPATH=. python api.py
    ```
    API will be available at `http://localhost:8000`.

2.  **Start .NET Control Plane**:
    ```bash
    dotnet run --project services/control-plane/ControlPlane.csproj
    ```
    Control Plane will be available at `http://localhost:5000`.

3.  **Start Streamlit Dashboard**:
    ```bash
    streamlit run app.py
    ```
    UI will be available at `http://localhost:8501`.

---

## Testing & Verification

### 1. Python Unit & Integration Tests
Run the comprehensive suite covering schemas, orchestrator, and history:
```bash
PYTHONPATH=. pytest tests/
```

### 2. .NET Unit & Integration Tests
Run the control plane tests covering ledger persistence and polling logic:
```bash
dotnet test services/control-plane/ControlPlane.Tests/ControlPlane.Tests.csproj
```

### 3. Smoke Verification (Analytical Path Only)
Verify the core Python analytical path directly:
```bash
python tests/reproduce_smoke.py
```

### 4. Hybrid Flow Verification (Full Proof)
Verify the full end-to-end lifecycle (Polling -> Analysis -> Persistence -> API):
1. Ensure both the Python API and .NET Control Plane are running.
2. Run the verification script:
   ```bash
   python tests/verify_hybrid.py
   ```

---

## Key Endpoints
- **Python**: `http://localhost:8000/health`, `/analyze/run`
- **.NET**: `http://localhost:5000/api/Health`, `/api/Cef/latest-analysis`, `/api/Cef/claims`, `/api/Cef/contradictions`, `/api/Cef/ledger`

## Known Limitations
- The system is a prototype and assumes a local shared folder for demo purposes.
- Persistence uses local JSON files (`ledger_data.json`, `rca_history.jsonl`, `reliability_graph.json`).
- .NET Control Plane polling interval is 2 seconds.
