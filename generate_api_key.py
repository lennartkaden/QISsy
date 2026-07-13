"""
CLI tool for the QISsy server operator.

Generate an API key for a friend:
    python generate_api_key.py alice

Generate a fresh secret for config.json (API/SECRET_KEY):
    python generate_api_key.py --new-secret

Keys are derived from API/SECRET_KEY via HMAC-SHA256 (see security.py), so
this script needs the same config.json (or API_SECRET_KEY environment
variable) the server uses. Revoke a single key by adding its name to
API/KEY_BLACKLIST; revoke all keys by changing the secret.
"""
import argparse
import secrets
import sys
from typing import List, Optional

from security import generate_api_key, get_api_secret_key

_SECRET_NUM_BYTES = 48


def main(argv: Optional[List[str]] = None) -> int:
    """Run the CLI. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        description="Generate QISsy API keys or a new server secret.",
    )
    parser.add_argument(
        "name",
        nargs="?",
        help="key name, e.g. the friend's name (letters, digits, hyphens)",
    )
    parser.add_argument(
        "--new-secret",
        action="store_true",
        help="print a new random secret for API/SECRET_KEY instead",
    )
    args = parser.parse_args(argv)

    if args.new_secret and args.name:
        parser.error("argument name: not allowed with argument --new-secret")

    if args.new_secret:
        print(secrets.token_urlsafe(_SECRET_NUM_BYTES))
        return 0

    if not args.name:
        parser.error("either a key name or --new-secret is required")

    secret = get_api_secret_key()
    if secret is None:
        print(
            "Error: API/SECRET_KEY is not configured. Add it to config.json "
            "(generate one with --new-secret) or set the API_SECRET_KEY "
            "environment variable.",
            file=sys.stderr,
        )
        return 1

    try:
        print(generate_api_key(args.name, secret))
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
