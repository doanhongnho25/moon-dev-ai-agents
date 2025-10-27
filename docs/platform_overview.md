# Moon Dev Control Center

This document introduces the experimental web platform that wraps the existing agent suite with an accessible user experience.

## What was added

- **FastAPI Control Plane** (`src/platform/app.py`) that exposes REST endpoints and a lightweight dashboard for launching agents.
- **AgentController** (`src/platform/agent_controller.py`) responsible for agent lifecycle management and background execution.
- **Jinja UI** (`src/platform/templates/index.html`) presenting the available agents, token overrides for the strategy agent, and real-time job tracking.
- **Static directory scaffold** (`src/platform/static/`) for future front-end enhancements.

## Running the platform locally

1. Install dependencies (see `requirements.txt` updates):

   ```bash
   pip install -r requirements.txt
   ```

2. Launch the control center with Uvicorn:

   ```bash
   uvicorn src.platform.app:app --reload
   ```

3. Open `http://127.0.0.1:8000` to access the dashboard.

## Workflow overview

1. **Agent discovery** – the dashboard queries `/agents` to list the supported bots along with a description and whether they can accept token overrides.
2. **Execution** – clicking “Run” issues a POST request to `/agents/{name}/run`. The controller spins up (or reuses) the relevant agent instance and executes it in a thread pool so the UI remains responsive.
3. **Monitoring** – background jobs are tracked by ID. The UI polls `/jobs` every five seconds and renders job status pills (`running`, `completed`, or `failed`). Results are retained in memory for quick inspection or to surface errors.

## Next steps

- Add authentication and API key management for safer remote deployment.
- Persist job history (e.g., SQLite) and surface detailed logs in the UI.
- Expand agent coverage beyond the initial core set, including RBI, Swarm, and Polymarket modules.
- Package the front-end as a richer React or Next.js experience while keeping the FastAPI backend as the orchestration layer.
