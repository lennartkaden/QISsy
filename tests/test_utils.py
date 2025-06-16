import json
import importlib
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def create_config(tmp_path, monkeypatch):
    config_data = {
        "QIS": {
            "BASE_URL": "http://testserver",
            "SERVICE_PATH": "/service"
        }
    }
    config_file = Path('config.json')
    config_file.write_text(json.dumps(config_data))
    yield
    config_file.unlink()


def test_parse_asi_parameter():
    from versions.v1 import utils
    importlib.reload(utils)
    html = '<a href="page?asi=ABC123">Notenspiegel / Studienverlauf</a>'
    assert utils.parse_asi_parameter(html) == 'ABC123'


def test_parse_asi_parameter_missing_link():
    """Return None if the link is missing."""
    from versions.v1 import utils
    importlib.reload(utils)
    html = '<a href="page?asi=ABC123">Wrong link</a>'
    assert utils.parse_asi_parameter(html) is None


def test_parse_user_display_name():
    from versions.v1 import utils
    importlib.reload(utils)
    spans = ''.join('<span></span>' for _ in range(8))
    html = f'<div class="divloginstatus">{spans}Test User</div>'
    assert utils.parse_user_display_name(html) == 'Test User'


def test_parse_scorecard_ids():
    from versions.v1 import utils
    importlib.reload(utils)
    html = '<a title="Leistungen" href="page?nodeID=NODE1">Name</a>'
    assert utils.parse_scorecard_ids(html) == {'Name': 'NODE1'}


def test_parse_float_int_status():
    from versions.v1 import utils
    importlib.reload(utils)
    assert utils._parse_float('1,3') == 1.3
    assert utils._parse_float('') is None
    assert utils._parse_int('10') == 10
    assert utils._parse_int('') is None
    from versions.v1.models import ScoreStatus
    assert utils._parse_status('bestanden') == ScoreStatus.PASSED
    assert utils._parse_status('') is None


def test_get_grade_point_average():
    from versions.v1 import utils
    from versions.v1.models import Module, Score, ScoreStatus, ScoreType
    importlib.reload(utils)
    module = Module(
        id=1,
        title='Mod',
        semester='WS',
        grade=None,
        status=ScoreStatus.PASSED,
        credits=5,
        issued_on='date',
        scores=[
            Score(id=1, title='Score', type=ScoreType.PL, semester='WS', grade=1.0, status=ScoreStatus.PASSED, issued_on='date', attempt=1, specific_scorecard_id=None)
        ]
    )
    gpa = utils.get_grade_point_average({'Cat': [module]})
    assert gpa == 1.0


def test_get_credit_point_sum():
    from versions.v1 import utils
    from versions.v1.models import Module, Score, ScoreStatus, ScoreType
    importlib.reload(utils)
    module = Module(
        id=1,
        title='Mod',
        semester='WS',
        grade=None,
        status=ScoreStatus.PASSED,
        credits=5,
        issued_on='date',
        scores=[
            Score(id=1, title='Score', type=ScoreType.PL, semester='WS', grade=1.0,
                  status=ScoreStatus.PASSED, issued_on='date', attempt=1,
                  specific_scorecard_id=None)
        ]
    )
    credit_sum = utils.get_credit_point_sum({'Cat': [module]})
    assert credit_sum == 5

def test_parse_scores(monkeypatch):
    from versions.v1 import utils
    from versions.v1.models import TableRow, RowType
    importlib.reload(utils)

    rows = [
        TableRow(id='0', title='Header', type='', semester='', grade='', status='', credits='', issued_on='', attempt='', note='', free_attempt='', row_type=RowType.CATEGORY),
        TableRow(id='1', title='Cat', type='', semester='', grade='', status='', credits='', issued_on='', attempt='', note='', free_attempt='', row_type=RowType.CATEGORY),
        TableRow(id='101', title='Mod', type='PL', semester='WS', grade='', status='bestanden', credits='5', issued_on='2021', attempt='1', note='', free_attempt='', row_type=RowType.MODULE),
        TableRow(id='1011', title='Score', type='PL', semester='WS', grade='1,0', status='bestanden', credits='', issued_on='2021', attempt='1', note='', free_attempt='', row_type=RowType.SCORE)
    ]
    monkeypatch.setattr(utils, '_parse_table_rows', lambda html: rows)
    scores = utils.parse_scores('<html></html>')
    assert 'Cat' in scores
    assert scores['Cat'][0].scores[0].grade == 1.0
