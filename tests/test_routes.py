import json
import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
import responses


@pytest.fixture(autouse=True)
def config_and_client(tmp_path):
    cfg = {"QIS": {"BASE_URL": "http://testserver", "SERVICE_PATH": "/service"}}
    config_file = Path('config.json')
    config_file.write_text(json.dumps(cfg))

    import config as cfg_module
    import versions.v1.utils as utils
    import versions.v1.user_routes as routes
    import main

    importlib.reload(cfg_module)
    importlib.reload(utils)
    importlib.reload(routes)
    importlib.reload(main)

    client = TestClient(main.app)
    yield client
    config_file.unlink()


@responses.activate
def test_signin_success(config_and_client):
    client = config_and_client
    from versions.v1.user_routes import SIGNIN_URL, STUDY_POS_URL
    login_html = '<div class="divloginstatus">' + ''.join('<span></span>' for _ in range(8)) + 'User</div>'
    responses.add(responses.POST, SIGNIN_URL, body=login_html, status=200,
                  headers={'Set-Cookie': 'JSESSIONID=ABC; Path=/; HttpOnly'})
    study_html = (
        '<div class="divloginstatus">' + ''.join('<span></span>' for _ in range(8)) + 'User</div>'
        '<a href="page?asi=ASI123">Notenspiegel / Studienverlauf</a>'
    )
    responses.add(responses.GET, STUDY_POS_URL, body=study_html, status=200)

    resp = client.post('/v1.0/signin', json={'username': 'u', 'password': 'p'})
    assert resp.status_code == 200
    data = resp.json()
    assert data['session_cookie'] == 'ABC'
    assert data['asi'] == 'ASI123'
    assert data['user_display_name'] == 'User'


@responses.activate
def test_check_session_validity(config_and_client):
    client = config_and_client
    from versions.v1.user_routes import SERVICE_BASE_URL
    check_url = f"{SERVICE_BASE_URL}?state=user&type=0&application=lsf"
    responses.add(responses.GET, check_url, body='OK', status=200)
    resp = client.get('/v1.0/check_session', headers={'session-cookie': 'ABC'})
    assert resp.status_code == 200
    assert resp.json()['is_valid'] is True
