from typing import Dict, Any, Optional, List
from pathlib import Path
from .config import SOURCE_BASE
from . import file_storage

def resolve_source_path(meta: Dict[str, Any]) -> Optional[Path]:
    """
    Meta info to PDF path.
    """
    path_candidates: List[Path] = []
    for key in ("source_file_path", "source_uri"):
        raw = meta.get(key)
        if raw:
            path_candidates.append(Path(str(raw)))

    for candidate in path_candidates:
        if candidate.exists():
            return candidate

    names: List[str] = []
    for val in (
        meta.get("source_file_path"),
        meta.get("source_uri"),
        meta.get("title"),
        (meta.get("doc_id") or "").split(":")[-1],
    ):
        if not val:
            continue
        names.append(Path(str(val)).name)

    seen = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        for found in SOURCE_BASE.rglob(name):
            return found

    # Library fallback
    try:
        for record in file_storage.list_files():
            original = (record.get("original_name") or "").strip()
            storage_path = record.get("storage_path")
            if not storage_path:
                continue
            if original and original in names:
                candidate = Path(storage_path)
                if candidate.exists():
                    return candidate
    except Exception:
        pass


    return None

import re

def build_citations(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    citations = []
    for idx, res in enumerate(results, start=1):
        meta = res.get("metadata") or {}
        raw_anchor = res.get("_raw_content") or res.get("content") or meta.get("snippet") or ""
        anchor_phrase = raw_anchor.strip()
        if anchor_phrase and len(anchor_phrase) > 1600:
            anchor_phrase = anchor_phrase[:1600].rstrip()
        snippet_source = res.get("content") or meta.get("snippet") or anchor_phrase
        snippet = (snippet_source or "").strip()
        snippet = re.sub(r"\s+", " ", snippet) if snippet else ""
        if snippet and len(snippet) > 240:
            snippet = snippet[:240].rstrip() + "…"
        offsets = meta.get("offsets")
        anchor_start: Optional[int] = None
        anchor_end: Optional[int] = None
        if isinstance(offsets, (list, tuple)) and len(offsets) >= 2:
            try:
                anchor_start = int(offsets[0]) if offsets[0] is not None else None
                anchor_end = int(offsets[1]) if offsets[1] is not None else None
            except (TypeError, ValueError):
                anchor_start = None
                anchor_end = None
        citations.append(
            {
                "id": idx,
                "doc_id": res.get("doc_base_id"),
                "title": res.get("title") or meta.get("file_name") or res.get("doc_base_id"),
                "uri": meta.get("source_file_path", ""),
                "page": meta.get("page"),
                "snippet": snippet,
                "anchor_phrase": anchor_phrase or None,
                "anchor_char_start": anchor_start,
                "anchor_char_end": anchor_end,
            }
        )
    return citations
