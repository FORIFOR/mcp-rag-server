from fastapi import APIRouter, Request
from ..models import Envelope
from . import notebooks, documents, search, ingest, jobs, summarize, library

router = APIRouter()

router.include_router(notebooks.router, prefix="/notebooks", tags=["notebooks"])
router.include_router(documents.router, tags=["documents"])
router.include_router(search.router, tags=["search"])
router.include_router(ingest.router, tags=["ingest"])
router.include_router(summarize.router, tags=["summarize"])
router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
router.include_router(library.router, prefix="/library", tags=["library"])

@router.get("/health", tags=["system"], response_model=Envelope)
def health(request: Request):
    return Envelope(
        request_id=request.state.request_id,
        data={"status": "healthy"}
    )
