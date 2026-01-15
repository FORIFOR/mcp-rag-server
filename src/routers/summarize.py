from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Request
import uuid
from typing import Dict, Any
from datetime import datetime

from ..security import Actor, get_actor
from ..models import Envelope, Job
from ..job_store import create_job, get_job
from ..legacy_logic import _run_summarize_job

router = APIRouter()

@router.post("/notebooks/{notebook_id}/summarize", status_code=202, response_model=Envelope)
async def summarize_notebook(
    notebook_id: str,
    request: Request,
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    actor: Actor = Depends(get_actor)
):
    job_id = str(uuid.uuid4())
    create_job(job_id, "summarize")
    
    job_payload = payload.copy()
    # Enforce scope from actor
    job_payload["tenant"] = actor.tenant_id
    job_payload["user_id"] = actor.user_id
    job_payload["notebook_id"] = notebook_id
    # Legacy logic often checks 'notebook' too
    if "notebook" not in job_payload:
        job_payload["notebook"] = notebook_id

    background_tasks.add_task(_run_summarize_job, job_id, job_payload)

    job_data = get_job(job_id)
    job_obj = Job(
        job_id=job_data["job_id"],
        type=job_data["type"],
        status=job_data["status"],
        progress=job_data["progress"],
        created_at=datetime.fromisoformat(job_data["created_at"].replace("Z", "+00:00")),
        updated_at=datetime.fromisoformat(job_data["updated_at"].replace("Z", "+00:00"))
    )

    return Envelope(
        request_id=request.state.request_id,
        data={"job": job_obj}
    )
