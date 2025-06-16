import json
from pathlib import Path
import importlib
import pytest


def test_get_config_value_success(tmp_path, monkeypatch):
    cfg = {"QIS": {"BASE_URL": "http://x", "SERVICE_PATH": "/s"}}
    config_file = tmp_path / 'config.json'
    config_file.write_text(json.dumps(cfg))
    monkeypatch.chdir(tmp_path)
    config = importlib.import_module('config')
    importlib.reload(config)
    assert config.get_config_value('QIS/BASE_URL') == 'http://x'


def test_get_config_value_missing_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = importlib.import_module('config')
    importlib.reload(config)
    with pytest.raises(FileNotFoundError):
        config.get_config_value('QIS/BASE_URL')


def test_get_config_value_key_error(tmp_path, monkeypatch):
    cfg = {"QIS": {}}
    config_file = tmp_path / 'config.json'
    config_file.write_text(json.dumps(cfg))
    monkeypatch.chdir(tmp_path)
    config = importlib.import_module('config')
    importlib.reload(config)
    with pytest.raises(KeyError):
        config.get_config_value('QIS/BASE_URL')
