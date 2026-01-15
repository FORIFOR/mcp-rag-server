import os
import logging
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException

from .routers.v1 import router as v1_router
from .legacy_logic import handle_http_exception, handle_unexpected_exception, SWAGGER_UI_PATH, REDOC_PATH, rects_ping as legacy_rects_ping
from .models import Envelope
# Ensure logging is set up
from .dependencies import logger

app = FastAPI(
    title="MCP RAG HTTP API",
    version="1.0.0",
    docs_url=SWAGGER_UI_PATH,
    redoc_url=REDOC_PATH,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(HTTPException, handle_http_exception)
app.add_exception_handler(Exception, handle_unexpected_exception)

# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["x-request-id"] = rid
    return response

# Health Check (Root)
@app.get("/health", response_model=Envelope)
def health(request: Request):
    return Envelope(
        request_id=request.state.request_id,
        data={"status": "healthy"}
    )

@app.get("/__rects_ping")
def rects_ping():
    return legacy_rects_ping()

# V1
app.include_router(v1_router, prefix="/api/v1")

# Legacy Compatibility
# map /api routes to v1
app.include_router(v1_router, prefix="/api", include_in_schema=False)
# Root routes (Legacy support)
app.include_router(v1_router, include_in_schema=False)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
