import hashlib
import hmac
import json

import pytest

import security


TEST_SECRET = "test-secret"


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    """Run every test in an empty temp dir so the real config.json is never read."""
    monkeypatch.chdir(tmp_path)
    yield tmp_path


def write_config(tmp_path, api_section):
    cfg = {"QIS": {"BASE_URL": "http://testserver", "SERVICE_PATH": "/service"}}
    if api_section is not None:
        cfg["API"] = api_section
    (tmp_path / "config.json").write_text(json.dumps(cfg))


# --- key generation and verification -------------------------------------

def test_generate_api_key_roundtrip():
    key = security.generate_api_key("Alice", TEST_SECRET)
    assert key.startswith("qissy_alice_")
    assert security.verify_api_key(key, TEST_SECRET) == "alice"


def test_generated_key_uses_hmac_sha256():
    key = security.generate_api_key("alice", TEST_SECRET)
    expected = hmac.new(TEST_SECRET.encode(), b"alice", hashlib.sha256).hexdigest()
    assert key == f"qissy_alice_{expected}"


def test_verify_rejects_tampered_signature():
    key = security.generate_api_key("alice", TEST_SECRET)
    tampered = key[:-1] + ("0" if key[-1] != "0" else "1")
    assert security.verify_api_key(tampered, TEST_SECRET) is None


def test_verify_rejects_key_after_secret_change():
    key = security.generate_api_key("alice", "old-secret")
    assert security.verify_api_key(key, "new-secret") is None


@pytest.mark.parametrize("bad_key", [
    "",
    "qissy",
    "qissy_alice",
    "wrong_alice_abc123",
    "qissy__abc123",
    "qissy_al_ice_abc123",
    "not even a key",
])
def test_verify_rejects_malformed_keys(bad_key):
    assert security.verify_api_key(bad_key, TEST_SECRET) is None


def test_parse_api_key_extracts_name_and_signature():
    key = security.generate_api_key("bob", TEST_SECRET)
    name, signature = security.parse_api_key(key)
    assert name == "bob"
    assert len(signature) == 64


@pytest.mark.parametrize("bad_name", ["", "al_ice", "älice", "a b", "a.b", "a/b"])
def test_generate_rejects_invalid_names(bad_name):
    with pytest.raises(ValueError):
        security.generate_api_key(bad_name, TEST_SECRET)


def test_names_are_normalized_to_lowercase():
    assert security.normalize_key_name("  Bob-2  ") == "bob-2"


# --- configuration helpers ------------------------------------------------

def test_protection_enabled_by_default_without_config():
    assert security.is_api_key_protection_enabled() is True


def test_protection_enabled_by_default_without_api_section(tmp_path):
    write_config(tmp_path, None)
    assert security.is_api_key_protection_enabled() is True


def test_protection_can_be_disabled(tmp_path):
    write_config(tmp_path, {"KEY_PROTECTION_ENABLED": False})
    assert security.is_api_key_protection_enabled() is False


def test_protection_env_string_false(monkeypatch):
    monkeypatch.setenv("API_KEY_PROTECTION_ENABLED", "false")
    assert security.is_api_key_protection_enabled() is False


def test_secret_key_missing_returns_none(tmp_path):
    write_config(tmp_path, {})
    assert security.get_api_secret_key() is None


def test_secret_key_blank_returns_none(tmp_path):
    write_config(tmp_path, {"SECRET_KEY": "   "})
    assert security.get_api_secret_key() is None


def test_secret_key_is_read_from_config(tmp_path):
    write_config(tmp_path, {"SECRET_KEY": TEST_SECRET})
    assert security.get_api_secret_key() == TEST_SECRET


def test_blacklist_missing_returns_empty(tmp_path):
    write_config(tmp_path, {})
    assert security.get_api_key_blacklist() == []


def test_blacklist_from_json_list(tmp_path):
    write_config(tmp_path, {"KEY_BLACKLIST": ["Mallory", " eve "]})
    assert security.get_api_key_blacklist() == ["mallory", "eve"]


def test_blacklist_from_env_string(monkeypatch):
    monkeypatch.setenv("API_KEY_BLACKLIST", "mallory, eve")
    assert security.get_api_key_blacklist() == ["mallory", "eve"]
