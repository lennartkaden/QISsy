"""
API key derivation and validation for QISsy.

API keys have the form ``qissy_<name>_<signature>`` where ``signature`` is the
hex encoded HMAC-SHA256 of ``name`` keyed with the configured secret
(``API/SECRET_KEY``). Keys are therefore stateless: they can be validated
without storage, individual keys can be revoked via the configured blacklist
(``API/KEY_BLACKLIST``) and all keys at once by changing the secret.
"""
import hashlib
import hmac
import re
from typing import List, Optional, Tuple

from fastapi import HTTPException
from fastapi.security import APIKeyHeader
from fastapi import Security

from config import get_config_value
from logging_config import logger

API_KEY_PREFIX = "qissy"
_NAME_PATTERN = re.compile(r"^[a-z0-9-]+$")


def normalize_key_name(name: str) -> str:
    """
    Normalize and validate an API key name.

    Args:
        name: The human readable key name, e.g. the friend's name.

    Returns: The trimmed, lowercased name.

    Raises:
        ValueError: If the name contains anything but letters, digits or
                    hyphens (underscores are reserved as key separators).
    """
    normalized = name.strip().lower()
    if not _NAME_PATTERN.fullmatch(normalized):
        raise ValueError(
            "API key names may only contain letters, digits and hyphens, "
            f"got: {name!r}"
        )
    return normalized


def generate_api_key(name: str, secret: str) -> str:
    """
    Derive the API key for ``name`` from ``secret``.

    Args:
        name: The human readable key name (validated and normalized).
        secret: The server operator's secret token.

    Returns: The full API key ``qissy_<name>_<signature>``.
    """
    normalized = normalize_key_name(name)
    signature = hmac.new(
        secret.encode("utf-8"), normalized.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"{API_KEY_PREFIX}_{normalized}_{signature}"


def parse_api_key(api_key: str) -> Optional[Tuple[str, str]]:
    """
    Split an API key into its name and signature parts.

    Args:
        api_key: The raw key from the client.

    Returns: ``(name, signature)`` in lowercase, or ``None`` if the key does
             not have the expected ``qissy_<name>_<signature>`` structure.
    """
    parts = api_key.strip().split("_")
    if len(parts) != 3:
        return None
    prefix, name, signature = parts
    if prefix != API_KEY_PREFIX or not name or not signature:
        return None
    return name.lower(), signature.lower()


def verify_api_key(api_key: str, secret: str) -> Optional[str]:
    """
    Check an API key's signature against ``secret``.

    Args:
        api_key: The raw key from the client.
        secret: The configured secret token.

    Returns: The key name if the signature is valid, ``None`` otherwise.
    """
    parsed = parse_api_key(api_key)
    if parsed is None:
        return None
    name, signature = parsed
    if not _NAME_PATTERN.fullmatch(name):
        return None
    expected = hmac.new(
        secret.encode("utf-8"), name.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    return name


def get_api_secret_key() -> Optional[str]:
    """
    Read ``API/SECRET_KEY`` from the configuration.

    Returns: The secret, or ``None`` if it is not configured or blank.
    """
    try:
        value = get_config_value("API/SECRET_KEY")
    except (FileNotFoundError, KeyError, ValueError):
        return None
    secret = str(value).strip()
    return secret or None


def is_api_key_protection_enabled() -> bool:
    """
    Read ``API/KEY_PROTECTION_ENABLED`` from the configuration.

    Returns: The configured value; defaults to ``True`` (protection on) when
             the setting is missing entirely.
    """
    try:
        value = get_config_value("API/KEY_PROTECTION_ENABLED")
    except (FileNotFoundError, KeyError, ValueError):
        return True
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in ("false", "0", "no", "off")


def get_api_key_blacklist() -> List[str]:
    """
    Read ``API/KEY_BLACKLIST`` from the configuration.

    Returns: A list of lowercased, trimmed key names. Accepts a JSON list in
             ``config.json`` or a comma separated string (environment
             variable fallback). Missing setting means an empty list.
    """
    try:
        value = get_config_value("API/KEY_BLACKLIST")
    except (FileNotFoundError, KeyError, ValueError):
        return []
    if isinstance(value, str):
        names = value.split(",")
    else:
        names = value
    return [str(name).strip().lower() for name in names if str(name).strip()]


_api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    scheme_name="APIKeyHeader",
    description="API key of the form qissy_<name>_<signature>, "
                "issued by the server operator.",
)


async def require_api_key(
    api_key: Optional[str] = Security(_api_key_header),
) -> Optional[str]:
    """
    FastAPI dependency that enforces API key protection.

    Runs before any endpoint code, so no request is ever forwarded to the
    QIS server unless the caller presented a valid, non-blacklisted key.

    Returns: The key name of the caller, or ``None`` when protection is
             disabled via ``API/KEY_PROTECTION_ENABLED``.

    Raises:
        HTTPException: 503 when protection is on but no secret is configured
                       (fail closed), 401 for missing or invalid keys and
                       403 for blacklisted keys.
    """
    if not is_api_key_protection_enabled():
        return None

    secret = get_api_secret_key()
    if secret is None:
        logger.error(
            "API key protection is enabled but API/SECRET_KEY is not "
            "configured; rejecting request (fail closed)"
        )
        raise HTTPException(status_code=503, detail="API key protection is misconfigured")

    if api_key is None:
        logger.warning("Rejected request without API key")
        raise HTTPException(status_code=401, detail="Missing API key")

    name = verify_api_key(api_key, secret)
    if name is None:
        logger.warning("Rejected request with invalid API key")
        raise HTTPException(status_code=401, detail="Invalid API key")

    if name in get_api_key_blacklist():
        logger.warning("Rejected request with blacklisted API key name '%s'", name)
        raise HTTPException(status_code=403, detail="API key has been revoked")

    return name
