from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException, Request
import uuid
import shutil
import asyncio
from datetime import datetime
from starlette.concurrency import run_in_threadpool

from ..security import Actor, get_actor
from ..models import Envelope, Job
from ..dependencies import rag_service, logger
from ..job_store import create_job, update_job, get_job
from ..config import SOURCE_BASE, RAG_TENANT_DEFAULT

router = APIRouter()

async def _background_ingest(job_id: str, tenant: str, notebook: str, user_id: str):
    try:
        update_job(job_id, status="running", progress=0.1)
        
        target_dir = SOURCE_BASE / (tenant or RAG_TENANT_DEFAULT) / notebook
        
        await run_in_threadpool(
            rag_service.index_documents,
            source_dir=target_dir,
            tenant=tenant or RAG_TENANT_DEFAULT,
            notebook=notebook,
            user_id=user_id,
            notebook_id=notebook,
            include_global=False 
        )
        
        update_job(job_id, status="succeeded", progress=1.0)
    except Exception as e:
        logger.exception(f"Ingest job {job_id} failed")
        update_job(job_id, status="failed", error={"code": "ingest_error", "message": str(e)})

@router.post("/notebooks/{notebook_id}/ingest", status_code=202, response_model=Envelope)
async def ingest_files(
    notebook_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    actor: Actor = Depends(get_actor)
):
    job_id = str(uuid.uuid4())
    create_job(job_id, "ingest")
    
    tenant_id = actor.tenant_id or RAG_TENANT_DEFAULT
    target_dir = SOURCE_BASE / tenant_id / notebook_id
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    for file in files:
        if not file.filename:
            continue
        dest_path = target_dir / file.filename
        try:
            with dest_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        finally:
            file.file.close()

    background_tasks.add_task(_background_ingest, job_id, tenant_id, notebook_id, actor.user_id)
    
    # Return Job used in response
    job_data = get_job(job_id)
    # Convert string dates to datetime objects for Pydantic
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
