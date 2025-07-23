import json
import importlib

import pytest


def reload_config():
    cfg = importlib.import_module('config')
    importlib.reload(cfg)
    return cfg


def test_get_config_value_success(tmp_path, monkeypatch):
    cfg_data = {"QIS": {"BASE_URL": "http://x", "SERVICE_PATH": "/s"}}
    config_file = tmp_path / 'config.json'
    config_file.write_text(json.dumps(cfg_data))
    monkeypatch.chdir(tmp_path)
    cfg = reload_config()
    assert cfg.get_config_value('QIS/BASE_URL') == 'http://x'


def test_get_config_value_missing_file_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('QIS_BASE_URL', 'http://env')
    cfg = reload_config()
    assert cfg.get_config_value('QIS/BASE_URL') == 'http://env'


def test_get_config_value_missing_file_no_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = reload_config()
    with pytest.raises(FileNotFoundError):
        cfg.get_config_value('QIS/BASE_URL')


def test_get_config_value_key_error_env(tmp_path, monkeypatch):
    cfg_data = {"QIS": {}}
    config_file = tmp_path / 'config.json'
    config_file.write_text(json.dumps(cfg_data))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('QIS_BASE_URL', 'http://env')
    cfg = reload_config()
    assert cfg.get_config_value('QIS/BASE_URL') == 'http://env'


def test_get_config_value_key_error_no_env(tmp_path, monkeypatch):
    cfg_data = {"QIS": {}}
    config_file = tmp_path / 'config.json'
    config_file.write_text(json.dumps(cfg_data))
    monkeypatch.chdir(tmp_path)
    cfg = reload_config()
    with pytest.raises(KeyError):
        cfg.get_config_value('QIS/BASE_URL')
