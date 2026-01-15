from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime
import shutil
from pathlib import Path

from ..security import Actor, get_actor
from ..models import Envelope, Notebook, Pagination
from ..dependencies import rag_service
from ..config import SOURCE_BASE, PROCESSED_BASE, RAG_TENANT_DEFAULT

router = APIRouter()

@router.get("", response_model=Envelope)
def list_notebooks(
    request: Request,
    actor: Actor = Depends(get_actor),
    include_global: bool = False
):
    try:
        summaries = rag_service.list_notebooks(
            user_id=actor.user_id,
            tenant=actor.tenant_id,
            include_global=include_global,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    
    items = []
    for item in summaries:
        # rag_service returns dicts with notebook_id, updated_at, etc.
        nb_id = item.get("notebook_id")
        ts_val = item.get("updated_at")
        
        # Handle datetime conversion if necessary
        # Assuming ts_val is ISO format string or datetime
        if isinstance(ts_val, str):
            try:
                updated_at = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
            except:
                updated_at = datetime.now()
        else:
            updated_at = ts_val if ts_val else datetime.now()

        items.append(Notebook(
            notebook_id=nb_id,
            name=nb_id, 
            created_at=updated_at, # Fallback as creation time isn't tracked explicitly
            updated_at=updated_at
        ))

    return Envelope(
        request_id=request.state.request_id,
        data={"items": items, "pagination": Pagination(limit=len(items))}
    )

@router.post("", status_code=201, response_model=Envelope)
def create_notebook(
    request: Request,
    payload: Dict[str, Any],
    actor: Actor = Depends(get_actor)
):
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    
    # Create directory
    tenant_dir = SOURCE_BASE / (actor.tenant_id or RAG_TENANT_DEFAULT)
    notebook_dir = tenant_dir / name
    try:
        notebook_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    nb = Notebook(
        notebook_id=name,
        name=name,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    return Envelope(
        request_id=request.state.request_id,
        data={"notebook": nb}
    )

@router.delete("/{notebook_id}", response_model=Envelope)
def delete_notebook(
    request: Request,
    notebook_id: str,
    actor: Actor = Depends(get_actor)
):
    try:
        deleted_rows = rag_service.delete_notebook(
            tenant=actor.tenant_id,
            notebook=notebook_id, 
            user_id=actor.user_id,
            notebook_id=notebook_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    
    notebook_dir_name = notebook_id
    tenant_id = actor.tenant_id or RAG_TENANT_DEFAULT
    source_dir = SOURCE_BASE / tenant_id / notebook_dir_name
    processed_dir = PROCESSED_BASE / tenant_id / notebook_dir_name

    if source_dir.exists():
        shutil.rmtree(source_dir, ignore_errors=True)
    if processed_dir.exists():
        shutil.rmtree(processed_dir, ignore_errors=True)

    return Envelope(
        request_id=request.state.request_id,
        data={"deleted": deleted_rows} 
    )
