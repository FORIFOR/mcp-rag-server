from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
import uuid
import json

from ..security import Actor, get_actor
from ..models import Envelope, SearchRequest, GenerateRequest, SearchHit
from ..dependencies import rag_service, llm_router
from ..utils import build_citations

router = APIRouter()

@router.post("/notebooks/{notebook_id}/search", response_model=Envelope)
def search_documents(
    notebook_id: str,
    request: Request,
    payload: SearchRequest,
    actor: Actor = Depends(get_actor)
):
    try:
        results = rag_service.search(
            payload.query,
            limit=payload.limit,
            with_context=payload.with_context,
            context_size=payload.context_size,
            full_document=False, # default
            tenant=actor.tenant_id,
            notebook=notebook_id,
            doc_filter=payload.doc_filter or payload.selected_ids,
            user_id=actor.user_id,
            notebook_id=notebook_id,
            include_global=False # or payload option if we add it
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    
    hits = []
    for r in results:
        hits.append(SearchHit(
            hit_id=str(uuid.uuid4()), # Service doesn't return hit_id?
            document_id=r.get("doc_base_id") or "unknown",
            score=r.get("similarity") or 0.0,
            chunk_text=r.get("content") or "",
            meta=r.get("metadata") or {},
            citations=None # Populated in generate?
        ))
        
    return Envelope(
        request_id=request.state.request_id,
        data={"hits": hits, "search_id": str(uuid.uuid4())}
    )

def _sse_event(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

@router.post("/notebooks/{notebook_id}/generate")
async def generate(
    notebook_id: str,
    request: Request,
    payload: GenerateRequest,
    actor: Actor = Depends(get_actor)
):
    # 1. Retrieve if needed
    contexts = []
    citation_data = []
    
    if payload.mode == "retrieve_generate":
        # Do search
        try:
            results = rag_service.search(
                payload.query,
                limit=10, # default or from payload?
                tenant=actor.tenant_id,
                notebook=notebook_id,
                user_id=actor.user_id,
                notebook_id=notebook_id,
            )
            # contexts for LLM
            # http_server.py _prepare_context_chunks logic?
            # Simplified for now:
            for r in results:
                contexts.append({
                    "title": r.get("title"),
                    "content": r.get("content"),
                    "metadata": r.get("metadata")
                })
            citation_data = build_citations(results)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    elif payload.mode == "generate_only":
        if not payload.hits:
            raise HTTPException(status_code=400, detail="hits is required for generate_only mode")
        results = []
        for hit in payload.hits:
            meta = hit.meta or {}
            contexts.append(
                {
                    "title": meta.get("title") or meta.get("file_name") or hit.document_id,
                    "content": hit.chunk_text,
                    "metadata": meta,
                }
            )
            results.append(
                {
                    "doc_base_id": hit.document_id,
                    "content": hit.chunk_text,
                    "metadata": meta,
                }
            )
        citation_data = build_citations(results)
    else:
        raise HTTPException(status_code=400, detail="Unsupported generate mode")

    request_id = request.state.request_id

    search_id = payload.search_id
    if payload.stream:
        async def event_generator():
            meta = {"request_id": request_id}
            if search_id:
                meta["search_id"] = search_id
            yield _sse_event("meta", meta)
            
            answer_text = ""
            
            async for chunk in llm_router.stream_chat(
                query=payload.query,
                contexts=contexts,
                provider=payload.provider,
                model=payload.model,
                temperature=payload.temperature,
                max_tokens=payload.max_tokens,
            ):
                ctype = chunk.get("type")
                if ctype == "token":
                    token = chunk.get("token", "")
                    answer_text += token
                    yield _sse_event("delta", {"text": token})
                elif ctype == "meta":
                    # llm usage info etc
                    pass

            yield _sse_event("done", {"answer": answer_text, "citations": citation_data})

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
        # Non-streaming
        # We need to consume the stream or use non-streaming method
        # llm_router only has stream_chat?
        # We can consume stream.
        
        answer_text = ""
        async for chunk in llm_router.stream_chat(
            query=payload.query,
            contexts=contexts,
            provider=payload.provider,
            model=payload.model,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
        ):
            if chunk.get("type") == "token":
                answer_text += chunk.get("token", "")
        
        return Envelope(
            request_id=request_id,
            data={"answer": answer_text, "citations": citation_data}
        )
