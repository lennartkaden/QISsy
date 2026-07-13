"""
Public authentication helper routes.

These routes intentionally do NOT require a valid API key: clients use them
to find out whether a key the user entered is valid. Brute-forcing keys via
this endpoint is deterred by a constant response time, a per-IP rate limit
and a per-IP limit of one concurrent request (see security.py).
"""
import asyncio
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Security
from fastapi_versioning import version

import security
from logging_config import logger

from .models import ApiKeyStatus, ErrorResponse

router = APIRouter()


@router.get("/check_api_key", response_model=ApiKeyStatus,
            responses={200: {"description": "API key status returned", "model": ApiKeyStatus},
                       429: {"description": "Too many or concurrent checks from this address",
                             "model": ErrorResponse},
                       503: {"description": "API key protection is misconfigured",
                             "model": ErrorResponse}})
@version(1, 0)
async def check_api_key(
        request: Request,
        api_key: Optional[str] = Security(security.api_key_header),
) -> ApiKeyStatus:
    """
    Check whether the presented ``X-API-Key`` is valid.

    Clients use this to tell the user whether the key they entered is
    correct, without triggering a request to the QIS server.

    To deter brute-forcing valid keys, this endpoint always takes
    ``CHECK_API_KEY_DELAY_SECONDS`` (2 seconds) to answer regardless of the
    outcome, allows at most ``CHECK_API_KEY_RATE_LIMIT`` checks per IP and
    rate window, and answers at most one request per IP at a time (429).
    """
    client_ip = request.client.host if request.client else "unknown"

    if not security.register_api_key_check(client_ip):
        logger.warning("Rate limited API key check from %s", client_ip)
        raise HTTPException(
            status_code=429,
            detail="Too many API key checks from this address, try again later",
            headers={"Retry-After": str(int(security.CHECK_API_KEY_RATE_WINDOW_SECONDS))},
        )

    if not security.begin_api_key_check(client_ip):
        logger.warning("Rejected concurrent API key check from %s", client_ip)
        raise HTTPException(
            status_code=429,
            detail="Another API key check from this address is already in progress",
            headers={"Retry-After": str(int(security.CHECK_API_KEY_DELAY_SECONDS))},
        )

    try:
        start = time.monotonic()

        secret = security.get_api_secret_key()
        if secret is None:
            logger.error(
                "API key check requested but API/SECRET_KEY is not configured"
            )
            raise HTTPException(status_code=503, detail="API key protection is misconfigured")

        name = security.verify_api_key(api_key, secret) if api_key else None
        is_valid = name is not None and name not in security.get_api_key_blacklist()

        # Constant response time: never reveal, via timing, how far
        # validation got before failing.
        remaining = security.CHECK_API_KEY_DELAY_SECONDS - (time.monotonic() - start)
        if remaining > 0:
            await asyncio.sleep(remaining)

        if is_valid:
            return ApiKeyStatus(is_valid=True, message="API key is valid")
        return ApiKeyStatus(is_valid=False, message="API key is invalid or has been revoked")
    finally:
        security.end_api_key_check(client_ip)
