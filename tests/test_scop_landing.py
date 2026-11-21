"""Landing HTTP and persistence tests using synthetic contact data."""
import http.client
import json
from pathlib import Path
import threading
from unittest.mock import patch

import pytest
from server.scop_landing import LandingServer, save_signup, validate_signup

VALID = {'email': 'tester@example.com', 'tool': 'Test tool', 'problem': 'Review takes time.', 'consent': True}


@pytest.fixture
def landing(tmp_path):
    tmp_path.chmod(0o700)
    server = LandingServer(0, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, tmp_path
    server.shutdown()
    server.server_close()
    thread.join()


def post(server, payload=VALID, headers=None, raw=None):
    connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
    request_headers = {'Origin': server.origin, 'X-SCOP-Token': server.token, 'Content-Type': 'application/json'}
    request_headers.update(headers or {})
    connection.request('POST', '/api/signup', json.dumps(payload).encode() if raw is None else raw, request_headers)
    response = connection.getresponse()
    result = response.status, json.loads(response.read())
    connection.close()
    return result


def test_persists_only_after_valid_consent(landing):
    server, directory = landing
    assert post(server, {**VALID, 'consent': False})[0] == 400
    assert list(directory.iterdir()) == []
    assert post(server) == (201, {'saved': True})
    record = next(directory.iterdir())
    data = json.loads(record.read_text())
    assert data['email'] == VALID['email'] and data['consent'] is True
    assert data['consent_version'] == 'landing-v1'
    assert record.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize('raw', [b'', b'\xff', b'[]', b'{}', b'{"email":1,"email":2}', b' ' * 8193])
def test_bad_transport_never_saves(landing, raw):
    server, directory = landing
    assert post(server, raw=raw)[0] in (400, 413)
    assert list(directory.iterdir()) == []


@pytest.mark.parametrize('update', [{'email':'bad'}, {'email':'a@b.com\nBcc: x'}, {'tool':' '},
                                    {'problem':'x' * 2001}, {'consent':'true'}, {'extra':'field'}])
def test_bad_fields(update):
    with pytest.raises(ValueError):
        validate_signup(json.dumps({**VALID, **update}).encode())


def test_origin_token_and_host(landing):
    server, directory = landing
    for headers in [{'Origin':'https://evil.example'}, {'Host':'evil.example'},
                    {'X-SCOP-Token':'wrong'}, {'Sec-Fetch-Site':'cross-site'}]:
        assert post(server, headers=headers)[0] == 403
    assert list(directory.iterdir()) == []


def test_unavailable_and_storage_failure_are_not_success(landing):
    server, directory = landing
    with patch('server.scop_landing.save_signup', side_effect=OSError('secret path')):
        code, body = post(server)
        assert code == 503 and 'secret' not in str(body)
    server.directory = None
    assert post(server)[0] == 503
    assert list(directory.iterdir()) == []


def test_private_store_rejects_symlink_and_repo(tmp_path):
    target = tmp_path / 'store'
    target.mkdir(mode=0o700)
    link = tmp_path / 'link'
    link.symlink_to(target)
    with pytest.raises(OSError):
        save_signup(link, VALID)
    with pytest.raises(ValueError):
        save_signup(Path(__file__).parents[1], VALID)
