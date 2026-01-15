from dataclasses import dataclass
import base64
import hashlib
import hmac
import json
import os
from fastapi import HTTPException, Request

@dataclass
class Actor:
    tenant_id: str
    user_id: str

def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)

def _decode_jwt(token: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid bearer token format")

    header_raw, payload_raw, signature_raw = parts
    try:
        header = json.loads(_b64url_decode(header_raw))
        payload = json.loads(_b64url_decode(payload_raw))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid bearer token payload") from exc

    secret = os.getenv("JWT_SECRET")
    if secret:
        if header.get("alg") != "HS256":
            raise HTTPException(status_code=401, detail="Unsupported JWT alg")
        signing_input = f"{header_raw}.{payload_raw}".encode("utf-8")
        expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual = _b64url_decode(signature_raw)
        if not hmac.compare_digest(expected, actual):
            raise HTTPException(status_code=401, detail="Invalid JWT signature")

    return payload

def _extract_actor_from_headers(request: Request) -> Actor | None:
    tenant_id = (request.headers.get("x-tenant") or "").strip()
    user_id = (request.headers.get("x-user-id") or "").strip()
    if tenant_id and user_id:
        return Actor(tenant_id=tenant_id, user_id=user_id)
    return None

def _extract_actor_from_query(request: Request) -> Actor | None:
    """Legacy fallback: extract tenant/user_id from query parameters."""
    tenant_id = (request.query_params.get("tenant") or "").strip()
    user_id = (request.query_params.get("user_id") or "").strip()
    if tenant_id and user_id:
        return Actor(tenant_id=tenant_id, user_id=user_id)
    return None

def get_actor(request: Request) -> Actor:
    # 1. Bearer token (preferred)
    auth_header = (request.headers.get("authorization") or "").strip()
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        payload = _decode_jwt(token)
        tenant_id = payload.get("tenant") or payload.get("tenant_id")
        user_id = payload.get("sub") or payload.get("user_id")
        if not tenant_id or not user_id:
            raise HTTPException(status_code=401, detail="Token missing tenant or user id")
        return Actor(tenant_id=str(tenant_id), user_id=str(user_id))

    # 2. Headers (x-tenant, x-user-id)
    header_actor = _extract_actor_from_headers(request)
    if header_actor:
        return header_actor

    # 3. Query parameters (legacy fallback)
    query_actor = _extract_actor_from_query(request)
    if query_actor:
        return query_actor

    raise HTTPException(status_code=401, detail="Authorization required")
