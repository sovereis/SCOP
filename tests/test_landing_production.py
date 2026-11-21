import json
from unittest.mock import patch, MagicMock
import pytest
from landing.backend.production import process, token, CSP
from landing.backend.storage import SupabaseStore
from landing.build import build

ENV = {'SCOP_PUBLIC_ORIGIN':'https://scop.example.com', 'SCOP_SUPABASE_URL':'https://testproject.supabase.co',
       'SCOP_SUPABASE_SERVICE_ROLE_KEY':'test-key-' * 5, 'SCOP_SIGNUP_SECRET':'test-secret-' * 4}
VALUE = {'email':'test@example.com', 'tool':'test tool', 'problem':'test challenge', 'consent':True}

@pytest.fixture
def configured(monkeypatch):
    for key, value in ENV.items():
        monkeypatch.setenv(key, value)
    return {'host':'scop.example.com', 'origin':ENV['SCOP_PUBLIC_ORIGIN'], 'content-type':'application/json',
            'x-scop-token':token(ENV['SCOP_SIGNUP_SECRET'], ENV['SCOP_PUBLIC_ORIGIN'])}


def test_missing_configuration_never_dispatches(monkeypatch):
    for name in ENV:
        monkeypatch.delenv(name, raising=False)
    with patch('landing.backend.production.SupabaseStore') as store:
        assert process('GET', '/api/config', {})[0] == 503
        assert process('POST', '/api/signup', {}, b'{}')[0] == 503
        store.assert_not_called()


def test_config_and_success(configured):
    code, result = process('GET', '/api/config', configured)
    assert code == 200 and result['available'] and result['token']
    assert ENV['SCOP_SUPABASE_SERVICE_ROLE_KEY'] not in json.dumps(result)
    with patch('landing.backend.production.SupabaseStore') as store:
        assert process('POST', '/api/signup', configured, json.dumps(VALUE).encode()) == (201, {'saved':True})
        store.return_value.save.assert_called_once_with(VALUE)


@pytest.mark.parametrize('change', [{'host':'evil.example'}, {'origin':'https://evil.example'},
                                   {'x-scop-token':'invalid'}, {'sec-fetch-site':'cross-site'}])
def test_cross_origin_and_token_denial(configured, change):
    with patch('landing.backend.production.SupabaseStore') as store:
        assert process('POST','/api/signup',{**configured,**change},json.dumps(VALUE).encode())[0] == 403
        store.assert_not_called()


def test_expired_token(configured):
    with patch('landing.backend.production.time.time', return_value=1):
        configured['x-scop-token'] = token(ENV['SCOP_SIGNUP_SECRET'], ENV['SCOP_PUBLIC_ORIGIN'])
    assert process('POST','/api/signup',configured,b'{}')[0] == 403


@pytest.mark.parametrize('body', [b'', b'\xff', b'[]', b'{"email":1,"email":2}', b' ' * 8193,
                                json.dumps({**VALUE,'consent':False}).encode()])
def test_invalid_payload_never_stores(configured, body):
    with patch('landing.backend.production.SupabaseStore') as store:
        assert process('POST','/api/signup',configured,body)[0] in (400,413)
        store.assert_not_called()


def test_storage_failure_redacted(configured):
    with patch('landing.backend.production.SupabaseStore.save',side_effect=RuntimeError('SECRET')):
        status, result = process('POST','/api/signup',configured,json.dumps(VALUE).encode())
        assert status == 503 and 'SECRET' not in str(result) and not result.get('saved')


def test_rest_adapter_verifies_acknowledgement():
    response = MagicMock()
    response.status = 201
    response.read.return_value = b'[{"id":"test-id"}]'
    opener = MagicMock()
    opener.open.return_value.__enter__.return_value = response
    with patch('landing.backend.storage.urllib.request.build_opener',return_value=opener), patch('landing.backend.storage.uuid4',return_value='test-id'):
        store = SupabaseStore(ENV['SCOP_SUPABASE_URL'], ENV['SCOP_SUPABASE_SERVICE_ROLE_KEY'])
        store.save(VALUE)
        request = opener.open.call_args.args[0]
        assert request.full_url.endswith('/rest/v1/scop_signups?select=id')
        assert opener.open.call_args.kwargs['timeout'] == 8
        assert json.loads(request.data)['consent'] is True
        response.read.return_value = b'[]'
        with pytest.raises(ValueError):
            store.save(VALUE)


def test_public_build_contains_only_landing(tmp_path):
    (tmp_path / "stale-private.txt").write_text("must not ship")
    build(tmp_path)
    assert sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob('*') if p.is_file()) == [
        'app.js','assets/hero.webp','index.html','style.css']
    assert 'frame-ancestors' in CSP and "connect-src 'self'" in CSP
