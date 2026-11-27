import asyncio
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import get_db

router = APIRouter()

PROCESS_STARTED_AT = datetime.now(timezone.utc)
CACHE_TTL_SECONDS = 60
_cache: dict[str, Any] = {"expires_at": 0.0, "payload": None}


def _get_process_memory_mb() -> float | None:
    """Lê o uso real de RAM (RSS) do processo Python no Linux (Render). Seguro no Windows."""
    try:
        with open("/proc/self/status", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    kb = int(line.split()[1])
                    return round(kb / 1024, 2)
    except OSError:
        pass

    try:
        import resource

        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return round(rss / 1024, 2) if rss > 0 else None
    except Exception:
        return None


def _collect_postgres_metrics(db: Session) -> dict[str, Any]:
    """Consulta armazenamento real, conexões e contagem de linhas direto no Postgres/Neon."""
    started = time.perf_counter()
    db_size_bytes = db.execute(text("SELECT pg_database_size(current_database())")).scalar() or 0
    active_connections = (
        db.execute(
            text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
        ).scalar()
        or 0
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 1)

    table_names = [
        "transactions",
        "categories",
        "payment_methods",
        "contexts",
        "goals",
        "recurring_bills",
    ]
    tables: dict[str, int] = {}
    for tbl in table_names:
        try:
            count = db.execute(text(f'SELECT count(*) FROM "{tbl}"')).scalar() or 0
            tables[tbl] = int(count)
        except Exception:
            db.rollback()

    return {
        "database_size_mb": round(db_size_bytes / (1024 * 1024), 2),
        "active_connections": int(active_connections),
        "latency_ms": latency_ms,
        "tables": tables,
        "total_rows": sum(tables.values()),
    }


async def _fetch_neon_api(client: httpx.AsyncClient) -> dict[str, Any]:
    api_key = os.getenv("NEON_API_KEY", "").strip()
    project_id = os.getenv("NEON_PROJECT_ID", "").strip()
    storage_limit_mb = float(os.getenv("NEON_STORAGE_LIMIT_MB", "512"))
    compute_limit_hours = float(os.getenv("NEON_COMPUTE_LIMIT_HOURS", "100"))

    if not api_key or not project_id:
        return {
            "configured": False,
            "storage_limit_mb": storage_limit_mb,
            "compute_limit_hours": compute_limit_hours,
        }

    try:
        res = await client.get(
            f"https://console.neon.tech/api/v2/projects/{project_id}",
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        )
        res.raise_for_status()
        project = res.json().get("project", {})

        compute_seconds = project.get("compute_time_seconds") or 0
        active_seconds = project.get("active_time_seconds") or 0
        synthetic_bytes = project.get("synthetic_storage_size") or 0
        transfer_bytes = project.get("data_transfer_bytes") or 0

        return {
            "configured": True,
            "error": None,
            "project_name": project.get("name"),
            "region": project.get("region_id"),
            "pg_version": project.get("pg_version"),
            "compute_hours_used": round(compute_seconds / 3600, 2),
            "compute_limit_hours": compute_limit_hours,
            "active_hours_used": round(active_seconds / 3600, 2),
            "synthetic_storage_mb": round(synthetic_bytes / (1024 * 1024), 2),
            "storage_limit_mb": storage_limit_mb,
            "data_transfer_mb": round(transfer_bytes / (1024 * 1024), 2),
            "quota_reset_at": project.get("quota_reset_at"),
        }
    except Exception as exc:
        return {
            "configured": True,
            "error": str(exc),
            "storage_limit_mb": storage_limit_mb,
            "compute_limit_hours": compute_limit_hours,
        }


def _extract_series_values(payload: Any) -> list[float]:
    values: list[float] = []
    if not isinstance(payload, list):
        return values
    for series in payload:
        if not isinstance(series, dict):
            continue
        for point in series.get("values", []) or []:
            if isinstance(point, dict) and isinstance(point.get("value"), (int, float)):
                values.append(float(point["value"]))
    return values


async def _safe_render_get(
    client: httpx.AsyncClient,
    path: str,
    headers: dict[str, str],
    params: dict[str, str] | None = None,
) -> Any:
    try:
        res = await client.get(
            f"https://api.render.com/v1{path}",
            headers=headers,
            params=params,
        )
        if res.status_code != 200:
            return None
        return res.json()
    except Exception:
        return None


async def _fetch_render_api(client: httpx.AsyncClient) -> dict[str, Any]:
    api_key = os.getenv("RENDER_API_KEY", "").strip()
    service_id = os.getenv("RENDER_SERVICE_ID", "").strip()
    memory_limit_mb = float(os.getenv("RENDER_MEMORY_LIMIT_MB", "512"))

    if not api_key or not service_id:
        return {
            "configured": False,
            "memory_limit_mb": memory_limit_mb,
        }

    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    now = datetime.now(timezone.utc)
    start_1h = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    start_24h = (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_now = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        service_data, deploys_data, cpu_data, mem_data, req_data = await asyncio.gather(
            _safe_render_get(client, f"/services/{service_id}", headers),
            _safe_render_get(client, f"/services/{service_id}/deploys", headers, {"limit": "1"}),
            _safe_render_get(
                client,
                "/metrics/cpu",
                headers,
                {"resource": service_id, "startTime": start_1h, "endTime": end_now},
            ),
            _safe_render_get(
                client,
                "/metrics/memory",
                headers,
                {"resource": service_id, "startTime": start_1h, "endTime": end_now},
            ),
            _safe_render_get(
                client,
                "/metrics/http-requests",
                headers,
                {"resource": service_id, "startTime": start_24h, "endTime": end_now},
            ),
        )

        if not service_data:
            return {
                "configured": True,
                "error": "Unable to fetch Render service details.",
                "memory_limit_mb": memory_limit_mb,
            }

        service = service_data.get("service", service_data)
        details = service.get("serviceDetails", {}) or {}

        latest_deploy = None
        if isinstance(deploys_data, list) and len(deploys_data) > 0:
            raw_deploy = deploys_data[0].get("deploy", deploys_data[0])
            commit = raw_deploy.get("commit") or {}
            latest_deploy = {
                "status": raw_deploy.get("status"),
                "created_at": raw_deploy.get("createdAt"),
                "finished_at": raw_deploy.get("finishedAt"),
                "commit_message": (commit.get("message") or "").splitlines()[0][:80]
                if commit.get("message")
                else None,
            }

        cpu_vals = _extract_series_values(cpu_data)
        mem_vals = _extract_series_values(mem_data)
        req_vals = _extract_series_values(req_data)

        cpu_latest = round(cpu_vals[-1] * 100, 1) if cpu_vals else None
        mem_latest_mb = round(mem_vals[-1] / (1024 * 1024), 1) if mem_vals else None
        requests_24h = int(round(sum(req_vals))) if req_vals else None

        return {
            "configured": True,
            "error": None,
            "service_name": service.get("name"),
            "plan": details.get("plan"),
            "region": details.get("region"),
            "suspended": service.get("suspended") == "suspended",
            "cpu_pct": cpu_latest,
            "memory_mb": mem_latest_mb,
            "memory_limit_mb": memory_limit_mb,
            "requests_24h": requests_24h,
            "latest_deploy": latest_deploy,
        }
    except Exception as exc:
        return {
            "configured": True,
            "error": str(exc),
            "memory_limit_mb": memory_limit_mb,
        }


@router.get("/metrics")
async def get_system_metrics(
    force: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    now_ts = time.time()
    if not force and _cache["payload"] is not None and now_ts < _cache["expires_at"]:
        return {**_cache["payload"], "cached": True}

    pg_metrics = _collect_postgres_metrics(db)

    async with httpx.AsyncClient(timeout=8.0) as client:
        neon_metrics, render_metrics = await asyncio.gather(
            _fetch_neon_api(client),
            _fetch_render_api(client),
        )

    uptime_seconds = int((datetime.now(timezone.utc) - PROCESS_STARTED_AT).total_seconds())

    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "cached": False,
        "runtime": {
            "uptime_seconds": uptime_seconds,
            "process_memory_mb": _get_process_memory_mb(),
        },
        "postgres": pg_metrics,
        "neon": neon_metrics,
        "render": render_metrics,
    }

    _cache["payload"] = payload
    _cache["expires_at"] = now_ts + CACHE_TTL_SECONDS
    return payload