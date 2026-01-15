from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from datetime import datetime
from typing import Optional, List

from ..security import Actor, get_actor
from ..models import Envelope, Document
from ..dependencies import rag_service
from ..utils import resolve_source_path
from ..pdf_utils import _extract_highlight_rects, RECTS_IMPL_VERSION
from starlette.concurrency import run_in_threadpool

router = APIRouter()

@router.get("/notebooks/{notebook_id}/documents", response_model=Envelope)
def list_documents(
    notebook_id: str,
    request: Request,
    actor: Actor = Depends(get_actor)
):
    try:
        docs = rag_service.list_documents(
            tenant=actor.tenant_id,
            notebook=notebook_id, 
            user_id=actor.user_id,
            notebook_id=notebook_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    items = []
    for d in docs:
        items.append(Document(
            document_id=d.get("doc_id") or "unknown",
            notebook_id=notebook_id,
            filename=d.get("title") or "unknown",
            content_type=d.get("mime") or "application/octet-stream",
            size_bytes=d.get("size") or 0,
            status="ready", 
            created_at=datetime.now(), 
            updated_at=datetime.now()
        ))
        
    return Envelope(
        request_id=request.state.request_id,
        data={"items": items}
    )

@router.delete("/notebooks/{notebook_id}/documents/{document_id}", response_model=Envelope)
def delete_document(
    notebook_id: str,
    document_id: str,
    request: Request,
    actor: Actor = Depends(get_actor)
):
    try:
         rag_service.delete_document(
            tenant=actor.tenant_id,
            notebook=notebook_id,
            doc_base_id=document_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    
    return Envelope(request_id=request.state.request_id, data={"deleted": True})

@router.get("/documents/{document_id}/pdf") 
def get_pdf(
    document_id: str,
    actor: Actor = Depends(get_actor)
):
    try:
        doc = rag_service.get_document_overview(
            doc_base_id=document_id,
            tenant=actor.tenant_id,
            user_id=actor.user_id,
            notebook_id=None 
        )
    except Exception:
         raise HTTPException(status_code=404, detail="Document not found")

    path = resolve_source_path(doc)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    ascii_name = path.name.encode("ascii", "ignore").decode("ascii") or "document.pdf"
    
    return FileResponse(
        path, 
        media_type="application/pdf", 
        filename=ascii_name
    )

def _resolve_document_path(document_id: str, actor: Actor):
    try:
        doc = rag_service.get_document_overview(
            doc_base_id=document_id,
            tenant=actor.tenant_id,
            user_id=actor.user_id,
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Document not found")

    path = resolve_source_path(doc)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return path


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: str,
    actor: Actor = Depends(get_actor)
):
    path = _resolve_document_path(document_id, actor)
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=path.name
    )

@router.get("/files/{document_id}/download", include_in_schema=False)
def download_file(
    document_id: str,
    actor: Actor = Depends(get_actor)
):
    return download_document(document_id=document_id, actor=actor)


async def _build_rects_payload(
    doc_id: str,
    notebook_id: Optional[str],
    request: Request,
    terms: List[str] = Query(default=[]),
    page: Optional[int] = Query(default=None, ge=1),
    hit_limit: Optional[int] = Query(default=None, ge=0, le=2000),
    max_hits: Optional[int] = Query(default=None, ge=0, le=2000),
    phrase: Optional[str] = Query(default=None),
    debug: int = Query(default=0, ge=0, le=1),
    engine: str = Query(default="chars"),
    include_items: bool = Query(default=False),
    actor: Actor = Depends(get_actor)
):
    try:
        doc = rag_service.get_document_overview(
            doc_base_id=doc_id,
            tenant=actor.tenant_id,
            user_id=actor.user_id,
            notebook_id=notebook_id,
        )
    except Exception:
         raise HTTPException(status_code=404, detail="Document not found")

    path = resolve_source_path(doc)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Call pdf utils
    debug_flag = debug == 1
    capture_items = bool(include_items) or debug_flag
    
    # max_hits resolution
    effective_limit = hit_limit if hit_limit is not None else (max_hits if max_hits is not None else 400)
    
    try:
        # run_in_threadpool because it is CPU bound and sync
        rects, debug_items, rect_mode = await run_in_threadpool(
            _extract_highlight_rects,
            path=path,
            terms=terms,
            max_hits=effective_limit,
            pages=[page] if page else None,
            phrase=phrase,
            debug=debug_flag,
            capture_text=capture_items,
            engine=engine
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"message": "rects_failed", "details": {"error": str(exc)}},
        )

    # Simplified response construction matching v1 expectations
    # Assuming the client handles the structure provided by pdf_utils
    # We might need to map it to JSON response structure http_server used
    
    # http_server.py constructed a detailed payload.
    # We will return what we have from utils roughly.
    
    target_page = page or (rects[0].get("page") if rects else 1)
    
    payload = {
        "doc_id": doc_id,
        "page": target_page,
        "rects": [], # flattened?
        "pages": rects, # The utils return list of page-rect dicts
        "impl": RECTS_IMPL_VERSION,
         "engine": engine
    }
    
    # Flatten rects for the requested page
    flat_rects = []
    for p in rects:
        if p.get("page") == target_page:
            flat_rects = p.get("rects", [])
            break
            
    payload["rects"] = flat_rects
    
    return Envelope(request_id=request.state.request_id, data=payload)


@router.get("/notebooks/{notebook_id}/documents/{document_id}/rects", response_model=Envelope)
async def get_document_rects(
    notebook_id: str,
    document_id: str,
    request: Request,
    terms: List[str] = Query(default=[]),
    page: Optional[int] = Query(default=None, ge=1),
    hit_limit: Optional[int] = Query(default=None, ge=0, le=2000),
    max_hits: Optional[int] = Query(default=None, ge=0, le=2000),
    phrase: Optional[str] = Query(default=None),
    debug: int = Query(default=0, ge=0, le=1),
    engine: str = Query(default="chars"),
    include_items: bool = Query(default=False),
    actor: Actor = Depends(get_actor)
):
    return await _build_rects_payload(
        doc_id=document_id,
        notebook_id=notebook_id,
        request=request,
        terms=terms,
        page=page,
        hit_limit=hit_limit,
        max_hits=max_hits,
        phrase=phrase,
        debug=debug,
        engine=engine,
        include_items=include_items,
        actor=actor,
    )


@router.get("/docs/rects", include_in_schema=False)
async def get_document_rects_legacy(
    doc_id: str,
    request: Request,
    terms: List[str] = Query(default=[]),
    page: Optional[int] = Query(default=None, ge=1),
    hit_limit: Optional[int] = Query(default=None, ge=0, le=2000),
    max_hits: Optional[int] = Query(default=None, ge=0, le=2000),
    phrase: Optional[str] = Query(default=None),
    debug: int = Query(default=0, ge=0, le=1),
    engine: str = Query(default="chars"),
    include_items: bool = Query(default=False),
    actor: Actor = Depends(get_actor)
):
    return await _build_rects_payload(
        doc_id=doc_id,
        notebook_id=None,
        request=request,
        terms=terms,
        page=page,
        hit_limit=hit_limit,
        max_hits=max_hits,
        phrase=phrase,
        debug=debug,
        engine=engine,
        include_items=include_items,
        actor=actor,
    )
