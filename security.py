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

from config import get_config_value

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
    except (FileNotFoundError, KeyError):
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
    except (FileNotFoundError, KeyError):
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
    except (FileNotFoundError, KeyError):
        return []
    if isinstance(value, str):
        names = value.split(",")
    else:
        names = value
    return [str(name).strip().lower() for name in names if str(name).strip()]
