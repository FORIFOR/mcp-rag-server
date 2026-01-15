from __future__ import annotations
import logging
import os
from threading import Lock
from .llm_router import LLMRouter

class _LazyRagService:
    """Lazy-load heavy dependencies (embeddings/DB) only when first accessed."""

    def __init__(self) -> None:
        self._service = None
        self._lock = Lock()

    def _get(self):
        if self._service is None:
            with self._lock:
                if self._service is None:
                    from .rag_tools import create_rag_service_from_env
                    self._service = create_rag_service_from_env()
        return self._service

    def __getattr__(self, name: str):
        return getattr(self._get(), name)

rag_service = _LazyRagService()
llm_router = LLMRouter()

_uvicorn_logger = logging.getLogger("uvicorn.error")
if not _uvicorn_logger.handlers:
    logging.basicConfig(level=logging.INFO)
logger = _uvicorn_logger.getChild("mcp.http")
logger.setLevel(logging.INFO)
rects_logger = _uvicorn_logger.getChild("mcp.rects")
rects_logger.setLevel(logging.INFO)
