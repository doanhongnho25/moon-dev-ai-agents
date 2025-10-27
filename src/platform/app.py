"""FastAPI application exposing a minimal control plane for Moon Dev agents."""
from __future__ import annotations

from typing import List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .agent_controller import AgentController

app = FastAPI(title="Moon Dev Control Center", version="0.1.0")
controller = AgentController()

templates = Jinja2Templates(directory="src/platform/templates")


class AgentRunRequest(BaseModel):
    tokens: Optional[List[str]] = None


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render dashboard."""
    agents = controller.list_agents()
    return templates.TemplateResponse("index.html", {"request": request, "agents": agents})


@app.get("/agents")
def list_agents():
    """Return metadata for all registered agents."""
    return controller.list_agents()


@app.post("/agents/{name}/run")
def run_agent(name: str, payload: AgentRunRequest, background: BackgroundTasks):
    """Trigger an agent execution in the background."""
    tokens = payload.tokens
    if tokens:
        tokens = [token.strip() for token in tokens if token.strip()]

    try:
        job_id = controller.submit_agent_run(name, tokens=tokens)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    background.add_task(controller.get_job_status, job_id)
    return {"job_id": job_id, "status": "submitted"}


@app.get("/jobs")
def list_jobs():
    """List statuses for all jobs."""
    return controller.list_jobs()


@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    try:
        return controller.get_job_status(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# Serve static assets (if any future additions)
app.mount("/static", StaticFiles(directory="src/platform/static"), name="static")
