from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from pathlib import Path

from ..security import Actor, get_actor
from ..models import (
    Envelope, 
    FileLinkPayload, 
    FileDeletePayload, 
    FileMovePayload, 
    FileScopePayload, 
    FileAiOrganizePayload
)
from ..legacy_logic import (
    RAG_TENANT_DEFAULT, 
    _normalize_storage_scope, 
    _normalize_folder_path, 
    _ingest_stored_file,
    _auto_tags_from_name,
    file_storage
)

router = APIRouter()

@router.post("/files", response_model=Dict[str, Any])
async def upload_library_file(
    file: UploadFile = File(...),
    tenant: str = Form(...),
    user_id: str = Form(...),
    scope: str = Form("personal"),
    folder_path: str = Form("/"),
    notebook_id: Optional[str] = Form(default=None),
):
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    storage_path = file_storage.store_bytes(payload, suffix=Path(file.filename or "").suffix)
    metadata = file_storage.create_metadata(
        tenant=tenant.strip() or RAG_TENANT_DEFAULT,
        user_id=user_id.strip() or "local",
        scope=_normalize_storage_scope(scope),
        folder_path=_normalize_folder_path(folder_path),
        notebook_id=notebook_id.strip() if notebook_id else None,
        original_name=file.filename or "uploaded-file",
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(payload),
        storage_path=storage_path,
    )
    stored = file_storage.register_file(metadata)
    return stored

@router.get("/files", response_model=Dict[str, Any])
async def list_library_files(
    tenant: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    folder_path: Optional[str] = Query(default=None),
):
    records = file_storage.list_files(tenant=tenant, user_id=user_id, folder_path=folder_path)
    return {"items": records, "count": len(records)}

@router.get("/files/folders", response_model=Dict[str, Any])
async def list_library_folders(
    tenant: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
):
    folders = file_storage.list_folders(tenant=tenant, user_id=user_id)
    return {"folders": folders}

@router.get("/files/{file_id}", response_model=Dict[str, Any])
async def get_library_file(file_id: str):
    record = file_storage.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    return record

@router.get("/files/{file_id}/download")
async def download_library_file(file_id: str):
    record = file_storage.get_file(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    storage_path = Path(record.get("storage_path", ""))
    if not storage_path.exists():
        raise HTTPException(status_code=404, detail="Stored file missing")
    return FileResponse(
        storage_path,
        media_type=record.get("mime_type") or "application/octet-stream",
        filename=record.get("original_name") or "download",
    )

@router.post("/files/link", response_model=Dict[str, Any])
async def link_library_files(payload: FileLinkPayload):
    if not payload.item_ids:
        raise HTTPException(status_code=422, detail="item_ids must not be empty")

    successes: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    for file_id in payload.item_ids:
        record = file_storage.get_file(file_id)
        if not record:
            errors.append({"id": file_id, "error": "not_found"})
            continue
        storage_path = Path(record.get("storage_path", ""))
        if not storage_path.exists():
            errors.append({"id": file_id, "error": "missing_file"})
            continue
        try:
            result = await _ingest_stored_file(
                storage_path,
                original_name=record.get("original_name") or file_id,
                tenant=payload.tenant.strip() or RAG_TENANT_DEFAULT,
                user_id=payload.user_id.strip() or "local",
                notebook_id=payload.notebook_id.strip(),
                include_global=payload.include_global,
            )
            file_storage.update_file(file_id, notebook_id=payload.notebook_id.strip())
            successes.append({"id": file_id, "ingest": result})
        except Exception as exc:
            errors.append({"id": file_id, "error": str(exc)})

    if not successes and errors:
        raise HTTPException(status_code=502, detail={"error": "link_failed", "detail": errors})
    return {"linked": successes, "errors": errors}

@router.post("/files/delete", response_model=Dict[str, Any])
async def delete_library_files(payload: FileDeletePayload):
    if not payload.item_ids:
        raise HTTPException(status_code=422, detail="item_ids must not be empty")
    deleted: List[str] = []
    errors: List[Dict[str, Any]] = []
    for file_id in payload.item_ids:
        success = file_storage.delete_file(file_id)
        if success:
            deleted.append(file_id)
        else:
            errors.append({"id": file_id, "error": "not_found"})
    if not deleted and errors:
        raise HTTPException(status_code=404, detail={"error": "delete_failed", "detail": errors})
    return {"deleted": deleted, "errors": errors}

@router.post("/files/move", response_model=Dict[str, Any])
async def move_library_files(payload: FileMovePayload):
    if not payload.item_ids:
        raise HTTPException(status_code=422, detail="item_ids must not be empty")
    target_folder = _normalize_folder_path(payload.folder_path)
    moved: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    for file_id in payload.item_ids:
        record = file_storage.update_file(file_id, folder_path=target_folder)
        if record:
            moved.append({"id": file_id, "folder_path": target_folder})
        else:
            errors.append({"id": file_id, "error": "not_found"})
    if not moved and errors:
        raise HTTPException(status_code=404, detail={"error": "move_failed", "detail": errors})
    return {"moved": moved, "errors": errors}

@router.post("/files/scope", response_model=Dict[str, Any])
async def change_library_scope(payload: FileScopePayload):
    if not payload.item_ids:
        raise HTTPException(status_code=422, detail="item_ids must not be empty")
    try:
        normalized_scope = _normalize_storage_scope(payload.scope)
    except HTTPException as exc:
        raise HTTPException(status_code=400, detail={"error": "invalid_scope", "detail": exc.detail})

    updated: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    for file_id in payload.item_ids:
        record = file_storage.update_file(file_id, scope=normalized_scope)
        if record:
            updated.append({"id": file_id, "scope": normalized_scope})
        else:
            errors.append({"id": file_id, "error": "not_found"})
    if not updated and errors:
        raise HTTPException(status_code=404, detail={"error": "scope_change_failed", "detail": errors})
    return {"updated": updated, "errors": errors}

@router.post("/files/ai-organize", response_model=Dict[str, Any])
async def ai_organize_library(payload: FileAiOrganizePayload):
    if not payload.item_ids:
        raise HTTPException(status_code=422, detail="item_ids must not be empty")
    updated: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    for file_id in payload.item_ids:
        record = file_storage.get_file(file_id)
        if not record:
            errors.append({"id": file_id, "error": "not_found"})
            continue
        tags = _auto_tags_from_name(record.get("original_name") or record.get("id") or "")
        meta = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
        meta = dict(meta or {})
        meta["tags"] = tags
        stored = file_storage.update_file(file_id, metadata=meta)
        if stored:
            updated.append({"id": file_id, "tags": tags})
        else:
            errors.append({"id": file_id, "error": "update_failed"})
    if not updated and errors:
        raise HTTPException(status_code=404, detail={"error": "ai_organize_failed", "detail": errors})
    return {"updated": updated, "errors": errors}
