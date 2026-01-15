import os
from pathlib import Path

SOURCE_DIR_ENV = os.environ.get("SOURCE_DIR", "data/source")
PROCESSED_DIR_ENV = os.environ.get("PROCESSED_DIR", "data/processed")

SOURCE_BASE = Path(SOURCE_DIR_ENV)
PROCESSED_BASE = Path(PROCESSED_DIR_ENV)
CONVERSATION_BASE = Path(os.environ.get("CONVERSATION_DIR", "data/conversations"))

RAG_TENANT_DEFAULT = os.environ.get("RAG_DEFAULT_TENANT", "default")
RAG_DEFAULT_USER_ID = os.environ.get("RAG_DEFAULT_USER_ID", "shared")
RAG_DEFAULT_NOTEBOOK_ID = os.environ.get("RAG_DEFAULT_NOTEBOOK_ID", "shared")
