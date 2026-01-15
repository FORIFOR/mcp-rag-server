from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

# Common

class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = {}

class Envelope(BaseModel):
    request_id: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[ErrorResponse] = None

class Pagination(BaseModel):
    next_cursor: Optional[str] = None
    limit: int

# Notebooks

class Notebook(BaseModel):
    notebook_id: str
    name: str
    created_at: datetime
    updated_at: datetime

# Documents

class Document(BaseModel):
    document_id: str
    notebook_id: str
    filename: str
    content_type: str
    size_bytes: int
    status: str
    created_at: datetime
    updated_at: datetime

# Jobs

class Job(BaseModel):
    job_id: str
    type: str  # ingest, summarize, reindex, ai_organize
    status: str # queued, running, succeeded, failed, canceled
    progress: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[ErrorResponse] = None
    created_at: datetime
    updated_at: datetime

# Search

class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    doc_filter: Optional[List[str]] = None
    selected_ids: Optional[List[str]] = None
    retriever: str = "mcp"
    rerank: bool = False
    top_k: Optional[int] = None
    strict_rag: Optional[bool] = True
    with_context: bool = False
    context_size: int = 1

class SearchHit(BaseModel):
    hit_id: str
    document_id: str
    score: float
    chunk_text: str
    meta: Dict[str, Any] = {}
    citations: Optional[List[Dict[str, Any]]] = None

class SearchResponse(BaseModel):
    hits: List[SearchHit]
    search_id: str

class GenerateRequest(BaseModel):
    query: str
    mode: str = "retrieve_generate" # retrieve_generate, generate_only
    hits: Optional[List[SearchHit]] = None
    search_id: Optional[str] = None
    strict_rag: Optional[bool] = True
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    stream: bool = True

class FileLinkPayload(BaseModel):
    tenant: str
    user_id: str
    notebook_id: str
    item_ids: List[str] = Field(default_factory=list)
    include_global: bool = False

class FileDeletePayload(BaseModel):
    tenant: str
    user_id: str
    item_ids: List[str] = Field(default_factory=list)

class FileMovePayload(BaseModel):
    tenant: str
    user_id: str
    item_ids: List[str] = Field(default_factory=list)
    folder_path: str

class FileScopePayload(BaseModel):
    tenant: str
    user_id: str
    item_ids: List[str] = Field(default_factory=list)
    scope: str

class FileAiOrganizePayload(BaseModel):
    tenant: str
    user_id: str
    item_ids: List[str] = Field(default_factory=list)
