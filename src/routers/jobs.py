from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime

from ..security import Actor, get_actor
from ..models import Envelope, Job, ErrorResponse
from ..job_store import get_job, update_job

router = APIRouter()

@router.get("/{job_id}", response_model=Envelope)
def get_job_status(
    job_id: str,
    request: Request,
    actor: Actor = Depends(get_actor)
):
    job_data = get_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
        
    error_obj = None
    if job_data.get("error"):
        err = job_data["error"]
        if isinstance(err, dict):
            error_obj = ErrorResponse(code=err.get("code", "unknown"), message=err.get("message", "unknown"))
    
    job_obj = Job(
        job_id=job_data["job_id"],
        type=job_data["type"],
        status=job_data["status"],
        progress=job_data["progress"],
        result=job_data.get("result"),
        error=error_obj,
        created_at=datetime.fromisoformat(job_data["created_at"].replace("Z", "+00:00")),
        updated_at=datetime.fromisoformat(job_data["updated_at"].replace("Z", "+00:00"))
    )
    
    return Envelope(
        request_id=request.state.request_id,
        data={"job": job_obj}
    )

@router.post("/{job_id}:cancel", response_model=Envelope)
def cancel_job(
    job_id: str,
    request: Request,
    actor: Actor = Depends(get_actor)
):
    job_data = get_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    update_job(job_id, status="canceled")
    
    return Envelope(
        request_id=request.state.request_id,
        data={"canceled": True}
    )
