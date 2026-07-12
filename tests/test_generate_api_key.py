import json

import pytest

import generate_api_key as cli
import security


TEST_SECRET = "cli-test-secret"


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield tmp_path


def write_config(tmp_path, api_section):
    cfg = {"QIS": {"BASE_URL": "http://testserver", "SERVICE_PATH": "/service"}}
    if api_section is not None:
        cfg["API"] = api_section
    (tmp_path / "config.json").write_text(json.dumps(cfg))


def test_new_secret_prints_random_secret(capsys):
    assert cli.main(["--new-secret"]) == 0
    first = capsys.readouterr().out.strip()
    assert cli.main(["--new-secret"]) == 0
    second = capsys.readouterr().out.strip()
    assert len(first) >= 43  # token_urlsafe(48) is 64 chars
    assert first != second


def test_generates_key_for_name(tmp_path, capsys):
    write_config(tmp_path, {"SECRET_KEY": TEST_SECRET})
    assert cli.main(["Alice"]) == 0
    out = capsys.readouterr().out.strip()
    assert out == security.generate_api_key("alice", TEST_SECRET)


def test_missing_secret_prints_error(tmp_path, capsys):
    write_config(tmp_path, None)
    assert cli.main(["alice"]) == 1
    err = capsys.readouterr().err
    assert "SECRET_KEY" in err


def test_invalid_name_prints_error(tmp_path, capsys):
    write_config(tmp_path, {"SECRET_KEY": TEST_SECRET})
    assert cli.main(["al_ice"]) == 1
    err = capsys.readouterr().err
    assert "Error" in err


def test_requires_name_or_new_secret_flag():
    with pytest.raises(SystemExit):
        cli.main([])


def test_new_secret_with_name_is_rejected():
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["alice", "--new-secret"])
    assert exc_info.value.code == 2
