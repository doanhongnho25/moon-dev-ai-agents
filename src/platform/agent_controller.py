"""Centralized controller for managing agent execution via the web platform."""
from __future__ import annotations

import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from termcolor import cprint

from src.config import MONITORED_TOKENS
from src.agents.copybot_agent import CopyBotAgent
from src.agents.risk_agent import RiskAgent
from src.agents.sentiment_agent import SentimentAgent
from src.agents.strategy_agent import StrategyAgent
from src.agents.trading_agent import TradingAgent


class AgentExecutionError(Exception):
    """Raised when an agent fails to execute successfully."""


class AgentController:
    """Manages agent lifecycle and background execution for the platform."""

    def __init__(self, max_workers: int = 4) -> None:
        self._instances: Dict[str, Any] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

        # Registry describing available agents and their behaviors
        self._registry: Dict[str, Dict[str, Any]] = {
            "trading": {
                "factory": TradingAgent,
                "description": "LLM-driven discretionary trading pipeline.",
                "supports_tokens": False,
            },
            "risk": {
                "factory": RiskAgent,
                "description": "Risk management guardrails and limit monitoring.",
                "supports_tokens": False,
            },
            "strategy": {
                "factory": StrategyAgent,
                "description": "Aggregates custom strategies and validates with LLMs.",
                "supports_tokens": True,
            },
            "copybot": {
                "factory": CopyBotAgent,
                "description": "Mirrors trades from curated on-chain wallets.",
                "supports_tokens": False,
            },
            "sentiment": {
                "factory": SentimentAgent,
                "description": "Collects social data and scores market sentiment.",
                "supports_tokens": False,
            },
        }

    # ------------------------------------------------------------------
    # Registry helpers
    # ------------------------------------------------------------------
    def list_agents(self) -> List[Dict[str, Any]]:
        """Return metadata about all available agents."""
        agents: List[Dict[str, Any]] = []
        for name, meta in self._registry.items():
            agents.append(
                {
                    "name": name,
                    "description": meta["description"],
                    "supports_tokens": meta["supports_tokens"],
                    "warm": name in self._instances,
                }
            )
        return agents

    # ------------------------------------------------------------------
    # Job management
    # ------------------------------------------------------------------
    def submit_agent_run(self, name: str, tokens: Optional[List[str]] = None) -> str:
        """Schedule an agent execution and return a tracking job id."""
        if name not in self._registry:
            raise KeyError(f"Unknown agent '{name}'")

        job_id = str(uuid.uuid4())
        submitted_at = datetime.utcnow()
        future = self._executor.submit(self._execute_agent, name, tokens)

        with self._lock:
            self._jobs[job_id] = {
                "future": future,
                "agent": name,
                "submitted_at": submitted_at,
            }

        return job_id

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Return structured information about a submitted job."""
        with self._lock:
            job = self._jobs.get(job_id)

        if not job:
            raise KeyError(f"Job '{job_id}' not found")

        future: Future = job["future"]
        status = "running"
        result: Any = None
        error: Optional[str] = None

        if future.done():
            try:
                result = future.result()
                status = "completed"
            except Exception as exc:  # pragma: no cover - defensive logging
                status = "failed"
                error = str(exc)

        return {
            "job_id": job_id,
            "agent": job["agent"],
            "submitted_at": job["submitted_at"].isoformat() + "Z",
            "status": status,
            "result": result,
            "error": error,
        }

    def list_jobs(self) -> List[Dict[str, Any]]:
        """Return all known jobs sorted by submission time (newest first)."""
        with self._lock:
            job_ids = list(self._jobs.keys())

        statuses = [self.get_job_status(job_id) for job_id in job_ids]
        return sorted(statuses, key=lambda job: job["submitted_at"], reverse=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_or_create_agent(self, name: str) -> Any:
        if name in self._instances:
            return self._instances[name]

        cprint(f"🚀 Initializing {name.title()} agent for web run...", "cyan")
        factory = self._registry[name]["factory"]
        instance = factory()
        self._instances[name] = instance
        return instance

    def _execute_agent(self, name: str, tokens: Optional[List[str]]) -> Dict[str, Any]:
        agent = self._get_or_create_agent(name)
        if name == "strategy":
            return self._run_strategy_agent(agent, tokens)
        if name == "copybot":
            agent.run_analysis_cycle()
            return {"message": "CopyBot analysis cycle complete"}
        if name == "trading":
            agent.run()
            return {"message": "Trading cycle complete"}
        if name == "risk":
            agent.run()
            return {"message": "Risk review complete"}
        if name == "sentiment":
            agent.run()
            return {"message": "Sentiment scan complete"}

        raise AgentExecutionError(f"No execution handler for agent '{name}'")

    def _run_strategy_agent(self, agent: StrategyAgent, tokens: Optional[List[str]]) -> Dict[str, Any]:
        # Fallback to monitored tokens if none provided
        token_list = [token for token in (tokens or MONITORED_TOKENS) if token]

        if not token_list:
            return {
                "message": "No tokens provided and MONITORED_TOKENS is empty.",
                "approved_signals": {},
            }

        approved: Dict[str, Any] = {}
        for token in token_list:
            approved[token] = agent.get_signals(token)

        return {
            "message": f"Evaluated {len(token_list)} token(s).",
            "approved_signals": approved,
        }


__all__ = ["AgentController", "AgentExecutionError"]
