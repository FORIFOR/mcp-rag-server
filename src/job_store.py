from typing import Dict, Any, Optional
from datetime import datetime

# In-memory store
JOB_STORE: Dict[str, Dict[str, Any]] = {}

def create_job(job_id: str, type: str) -> Dict[str, Any]:
    job = {
        "job_id": job_id,
        "type": type,
        "status": "queued",
        "progress": 0.0,
        "result": None,
        "error": None,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }
    JOB_STORE[job_id] = job
    return job

def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    return JOB_STORE.get(job_id)

def update_job(job_id: str, **kwargs):
    job = JOB_STORE.get(job_id)
    if job:
        job.update(kwargs)
        job["updated_at"] = datetime.utcnow().isoformat() + "Z"
