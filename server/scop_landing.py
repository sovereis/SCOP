"""Local preview and private persistence for the separate SCOP landing page."""
import argparse
from datetime import UTC, datetime
import fcntl
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from itertools import islice
import os
from pathlib import Path
import secrets
from uuid import uuid4

from .scop_measurement import MeasurementError, _open_store, _write

from landing.backend.validation import validate_signup

ASSETS = Path(__file__).resolve().parents[1] / 'landing'
MAX_BODY = 8192
MAX_SIGNUPS = 10_000




def save_signup(directory, value):
    # Reuse the existing descriptor-relative private-store safeguards only.
    # Signup data is kept in its own dedicated directory, never the measurement store.
    with _open_store(directory) as fd:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with os.scandir(fd) as entries:
            if sum(1 for _ in islice(entries, MAX_SIGNUPS)) >= MAX_SIGNUPS:
                raise ValueError('Store full')
        record = {**value, 'submitted_at': datetime.now(UTC).isoformat(), 'consent_version': 'landing-v1'}
        _write(fd, f'{uuid4()}.signup.json', record)


class LandingServer(HTTPServer):
    request_queue_size = 8

    def __init__(self, port=8780, directory=None):
        self.directory = directory
        self.token = secrets.token_urlsafe(32)
        super().__init__(('127.0.0.1', port), Handler)
        self.origin = f'http://127.0.0.1:{self.server_port}'


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *_args):
        pass

    def reply(self, code, payload, mime='application/json'):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(code)
        headers = {
            'Content-Type': mime, 'Content-Length': str(len(body)),
            'Cache-Control': 'no-store', 'Connection': 'close',
            'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
            'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
        }
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def trusted(self, post=False):
        if self.headers.get_all('Host') != [self.server.origin.removeprefix('http://')]:
            return False
        if self.headers.get('Sec-Fetch-Site') not in (None, 'none', 'same-origin'):
            return False
        origins = self.headers.get_all('Origin')
        if origins is not None and origins != [self.server.origin]:
            return False
        return not post or (origins == [self.server.origin] and secrets.compare_digest(
            self.headers.get('X-SCOP-Token', '').encode(), self.server.token.encode()))

    def do_GET(self):
        if not self.trusted():
            return self.reply(403, {'error': 'Local origin required'})
        assets = {'/': ('index.html', 'text/html; charset=utf-8'),
                  '/style.css': ('style.css', 'text/css'), '/app.js': ('app.js', 'text/javascript'),
                  '/assets/hero.webp': ('assets/hero.webp', 'image/webp')}
        if self.path not in assets:
            return self.reply(404, {'error': 'Unknown route'})
        name, mime = assets[self.path]
        raw = (ASSETS / name).read_bytes()
        if name == 'index.html':
            raw = raw.replace(b'__TOKEN__', self.server.token.encode())
            raw = raw.replace(b'__AVAILABLE__', b'true' if self.server.directory else b'false')
        self.reply(200, raw, mime)

    def do_POST(self):
        if not self.trusted(post=True):
            return self.reply(403, {'error': 'Local origin and session token required'})
        if self.path != '/api/signup':
            return self.reply(404, {'error': 'Unknown route'})
        lengths = self.headers.get_all('Content-Length', [])
        if (len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit()
                or len(lengths[0]) > 6 or self.headers.get('Transfer-Encoding') is not None):
            return self.reply(400, {'error': 'Invalid request length'})
        length = int(lengths[0])
        if not 0 < length <= MAX_BODY:
            return self.reply(413, {'error': 'Request too large or empty'})
        if self.headers.get('Content-Type') != 'application/json':
            return self.reply(415, {'error': 'Expected JSON'})
        if self.server.directory is None:
            return self.reply(503, {'error': 'Signups unavailable'})
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError('Incomplete request')
            value = validate_signup(raw)
        except (ValueError, RecursionError):
            return self.reply(400, {'error': 'Check the fields and consent'})
        except OSError:
            return self.reply(408, {'error': 'Request timed out'})
        try:
            save_signup(self.server.directory, value)
        except (OSError, ValueError, MeasurementError):
            return self.reply(503, {'error': 'Could not save the submission'})
        self.reply(201, {'saved': True})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8780)
    parser.add_argument('--signup-dir', type=Path)
    args = parser.parse_args()
    if args.signup_dir:
        with _open_store(args.signup_dir):
            pass
    with LandingServer(args.port, args.signup_dir) as server:
        print(f'SCOP landing preview: {server.origin}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
