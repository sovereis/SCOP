"""Stateless production request boundary. No Workspace or filesystem imports."""
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from urllib.parse import urlsplit

from .storage import SupabaseStore
from .validation import validate_signup

MAX_BODY = 8192
CSP = "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"


def configuration():
    origin = os.getenv('SCOP_PUBLIC_ORIGIN', '')
    parsed = urlsplit(origin)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment or parsed.netloc != parsed.hostname):
        raise ValueError('Invalid public origin')
    url = os.getenv('SCOP_SUPABASE_URL', '')
    if not re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co', url):
        raise ValueError('Invalid storage endpoint')
    key = os.getenv('SCOP_SUPABASE_SERVICE_ROLE_KEY', '')
    secret = os.getenv('SCOP_SIGNUP_SECRET', '')
    if len(key) < 20 or len(secret) < 32:
        raise ValueError('Missing server credentials')
    return origin, url, key, secret


def token(secret, origin):
    message = f'{int(time.time())}.{secrets.token_hex(16)}'
    signature = hmac.new(secret.encode(), (origin + message).encode(), hashlib.sha256).hexdigest()
    return message + '.' + signature


def valid_token(value, secret, origin):
    if not isinstance(value, str) or len(value) > 160:
        return False
    try:
        timestamp, nonce, signature = value.split('.')
        age = time.time() - int(timestamp)
        expected = hmac.new(secret.encode(), (origin + timestamp + '.' + nonce).encode(), hashlib.sha256).hexdigest()
        return 0 <= age <= 3600 and hmac.compare_digest(signature, expected)
    except (ValueError, TypeError):
        return False


def process(method, path, headers, body=b''):
    try:
        origin, url, key, secret = configuration()
    except ValueError:
        return 503, {'error': 'Signups unavailable. Production storage is not configured.'}
    if (headers.get('host') != urlsplit(origin).netloc
            or headers.get('sec-fetch-site') not in (None, 'same-origin', 'none')
            or headers.get('origin') not in (None, origin)):
        return 403, {'error': 'Origin denied'}
    if method == 'GET' and path == '/api/config':
        return 200, {'available': True, 'token': token(secret, origin)}
    if method != 'POST' or path != '/api/signup':
        return 405, {'error': 'Unsupported operation'}
    if headers.get('origin') != origin or not valid_token(headers.get('x-scop-token'), secret, origin):
        return 403, {'error': 'Reload this page before submitting'}
    if headers.get('content-type') != 'application/json':
        return 415, {'error': 'Expected JSON'}
    if not 0 < len(body) <= MAX_BODY:
        return 413, {'error': 'Request too large or empty'}
    try:
        value = validate_signup(body)
    except (ValueError, RecursionError):
        return 400, {'error': 'Check the fields and consent'}
    try:
        SupabaseStore(url, key).save(value)
    except Exception:
        return 503, {'error': 'Could not confirm storage. Please try again later.'}
    return 201, {'saved': True}
