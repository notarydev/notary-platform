"""Authentication and org scoping for the Notary Platform.

Phase 1 uses a simple static bearer-token / API-key model. When
``NOTARY_API_AUTH_TOKEN`` is unset, auth is disabled so local demos and tests
run without credentials. Production deployments MUST set the token (sourced
from AWS Secrets Manager).
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from notary_platform.config import SETTINGS

_bearer = HTTPBearer(auto_error=False)

# Header used to pass the acting org id. Defaults to the configured org.
ORG_HEADER = "X-Notary-Org"


def _extract_token(creds: Optional[HTTPAuthorizationCredentials], request: Request) -> Optional[str]:
    if creds and creds.credentials:
        return creds.credentials
    # Accept ?api_key= or x-api-key header as an alternative API-key form.
    api_key = request.headers.get("x-api-key")
    if api_key:
        return api_key
    api_key_q = request.query_params.get("api_key")
    if api_key_q:
        return api_key_q
    return None


def require_auth(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> str:
    """Return the acting org id, raising 401 when auth fails.

    When auth is disabled (no token configured) this returns the default org.
    """
    if not SETTINGS.auth_enabled:
        return request.headers.get(ORG_HEADER, SETTINGS.default_org_id)

    token = _extract_token(creds, request)
    if not token or token != SETTINGS.api_auth_token:
        raise HTTPException(status_code=401, detail="invalid or missing API token")
    return request.headers.get(ORG_HEADER, SETTINGS.default_org_id)


def get_optional_org(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> str:
    """Like require_auth but never raises — used for health/readiness."""
    if not SETTINGS.auth_enabled:
        return request.headers.get(ORG_HEADER, SETTINGS.default_org_id)
    token = _extract_token(creds, request)
    if not token or token != SETTINGS.api_auth_token:
        return ""
    return request.headers.get(ORG_HEADER, SETTINGS.default_org_id)
