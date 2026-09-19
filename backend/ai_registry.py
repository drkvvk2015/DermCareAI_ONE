from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import require_roles

DB_PATH = Path(os.getenv("AI_GOVERNANCE_DB_PATH", "ai_governance.db"))
router = APIRouter(prefix="/api/v1/ai", tags=["ai-governance"])


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_store() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS model_versions (
              id TEXT PRIMARY KEY,
              model_name TEXT NOT NULL,
              version TEXT NOT NULL,
              artifact_sha256 TEXT NOT NULL,
              research_only INTEGER NOT NULL,
              validated INTEGER NOT NULL,
              status TEXT NOT NULL,
              calibration_method TEXT,
              approval_note TEXT,
              approved_by TEXT,
              approved_at TEXT,
              created_at TEXT NOT NULL,
              UNIQUE(model_name, version)
            );
            CREATE TABLE IF NOT EXISTS evaluation_runs (
              id TEXT PRIMARY KEY,
              model_version_id TEXT NOT NULL,
              dataset_name TEXT NOT NULL,
              dataset_version TEXT NOT NULL,
              split_name TEXT NOT NULL,
              sample_count INTEGER NOT NULL,
              metrics_json TEXT NOT NULL,
              subgroup_metrics_json TEXT NOT NULL,
              external_validation INTEGER NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS model_deployments (
              id TEXT PRIMARY KEY,
              model_version_id TEXT NOT NULL,
              environment TEXT NOT NULL,
              status TEXT NOT NULL,
              activated_at TEXT,
              rolled_back_at TEXT,
              created_at TEXT NOT NULL
            );
            """
        )


class ModelVersionCreate(BaseModel):
    model_name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=80)
    artifact_sha256: str = Field(min_length=64, max_length=64)
    research_only: bool = True
    validated: bool = False
    status: str = "candidate"
    calibration_method: str | None = None


class ModelApproval(BaseModel):
    approval_note: str = Field(min_length=10, max_length=2000)


class EvaluationRunCreate(BaseModel):
    model_version_id: str
    dataset_name: str
    dataset_version: str
    split_name: str
    sample_count: int = Field(ge=1)
    metrics: dict[str, Any]
    subgroup_metrics: dict[str, Any] = {}
    external_validation: bool = False


class DeploymentCreate(BaseModel):
    model_version_id: str
    environment: str = Field(pattern="^(staging|production)$")


@router.get("/registry")
def list_registry(_: dict[str, Any] = Depends(require_roles("admin", "auditor", "doctor"))):
    init_store()
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM model_versions ORDER BY model_name, version").fetchall()
    return [dict(row) for row in rows]


@router.post("/registry")
def register_model(req: ModelVersionCreate, user: dict[str, Any] = Depends(require_roles("admin"))):
    init_store()
    model_id = f"MOD-{uuid.uuid4().hex[:12].upper()}"
    now = _now()
    with _connect() as conn:
        try:
            conn.execute(
                """
                INSERT INTO model_versions(
                  id,model_name,version,artifact_sha256,research_only,validated,status,
                  calibration_method,created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model_id, req.model_name, req.version, req.artifact_sha256,
                    int(req.research_only), int(req.validated), req.status,
                    req.calibration_method, now,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="Model version already registered") from exc
    return {"id": model_id, "created_at": now, **req.model_dump(), "registered_by": user["uid"]}


@router.post("/registry/{model_id}/approve")
def approve_model(model_id: str, req: ModelApproval, user: dict[str, Any] = Depends(require_roles("admin"))):
    init_store()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM model_versions WHERE id = ?", (model_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Model version not found")
        conn.execute(
            """
            UPDATE model_versions
            SET validated = 1, status = 'approved', approval_note = ?, approved_by = ?, approved_at = ?
            WHERE id = ?
            """,
            (req.approval_note, user["uid"], _now(), model_id),
        )
    return {"id": model_id, "status": "approved", "validated": True, "approved_by": user["uid"]}


@router.post("/evaluations")
def register_evaluation(req: EvaluationRunCreate, _: dict[str, Any] = Depends(require_roles("admin"))):
    init_store()
    evaluation_id = f"EVAL-{uuid.uuid4().hex[:12].upper()}"
    with _connect() as conn:
        exists = conn.execute("SELECT 1 FROM model_versions WHERE id = ?", (req.model_version_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Model version not found")
        conn.execute(
            """
            INSERT INTO evaluation_runs(
              id,model_version_id,dataset_name,dataset_version,split_name,sample_count,
              metrics_json,subgroup_metrics_json,external_validation,created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evaluation_id, req.model_version_id, req.dataset_name, req.dataset_version,
                req.split_name, req.sample_count, json.dumps(req.metrics, sort_keys=True),
                json.dumps(req.subgroup_metrics, sort_keys=True), int(req.external_validation), _now(),
            ),
        )
    return {"id": evaluation_id, **req.model_dump()}


@router.get("/registry/{model_id}/evaluations")
def model_evaluations(model_id: str, _: dict[str, Any] = Depends(require_roles("admin", "auditor", "doctor"))):
    init_store()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM evaluation_runs WHERE model_version_id = ? ORDER BY created_at DESC",
            (model_id,),
        ).fetchall()
    return [
        {
            **dict(row),
            "metrics": json.loads(row["metrics_json"]),
            "subgroup_metrics": json.loads(row["subgroup_metrics_json"]),
        }
        for row in rows
    ]


@router.post("/deployments")
def deploy_model(req: DeploymentCreate, user: dict[str, Any] = Depends(require_roles("admin"))):
    init_store()
    with _connect() as conn:
        model = conn.execute("SELECT * FROM model_versions WHERE id = ?", (req.model_version_id,)).fetchone()
        if not model:
            raise HTTPException(status_code=404, detail="Model version not found")

        if req.environment == "production":
            if not int(model["validated"]):
                raise HTTPException(status_code=409, detail="Only validated model versions may deploy to production")
            if int(model["research_only"]):
                raise HTTPException(status_code=409, detail="Research-only model cannot deploy to production")
            if model["status"] not in {"approved", "production"}:
                raise HTTPException(status_code=409, detail="Model version is not approved for production")

        deployment_id = f"DEP-{uuid.uuid4().hex[:12].upper()}"
        now = _now()
        conn.execute(
            "UPDATE model_deployments SET status = 'rolled_back', rolled_back_at = ? WHERE environment = ? AND status = 'active'",
            (now, req.environment),
        )
        conn.execute(
            """
            INSERT INTO model_deployments(
              id,model_version_id,environment,status,activated_at,created_at
            ) VALUES (?, ?, ?, 'active', ?, ?)
            """,
            (deployment_id, req.model_version_id, req.environment, now, now),
        )
    return {
        "id": deployment_id,
        "environment": req.environment,
        "status": "active",
        "model_version_id": req.model_version_id,
        "activated_at": now,
        "deployed_by": user["uid"],
    }
