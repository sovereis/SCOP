"""Vercel Python function handler shared by two fixed endpoints."""
from http.server import BaseHTTPRequestHandler
import json
from .production import CSP, MAX_BODY, process

class SignupHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def respond(self, code, payload):
        raw = json.dumps(payload).encode()
        self.send_response(code)
        for key, value in {'Content-Type':'application/json', 'Content-Length':str(len(raw)),
                           'Cache-Control':'no-store', 'Content-Security-Policy':CSP,
                           'X-Content-Type-Options':'nosniff', 'Referrer-Policy':'no-referrer'}.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(raw)

    def dispatch(self):
        headers = {}
        for key in self.headers.keys():
            values = self.headers.get_all(key)
            if len(values) != 1:
                return self.respond(400, {'error':'Duplicate header'})
            headers[key.lower()] = values[0]
        body = b''
        if self.command == 'POST':
            length = headers.get('content-length', '')
            if (not length.isascii() or not length.isdigit() or len(length) > 6
                    or 'transfer-encoding' in headers):
                return self.respond(400, {'error':'Invalid request length'})
            if not 0 < int(length) <= MAX_BODY:
                return self.respond(413, {'error':'Request too large or empty'})
            body = self.rfile.read(int(length))
            if len(body) != int(length):
                return self.respond(400, {'error':'Incomplete request'})
        self.respond(*process(self.command, self.path, headers, body))

    do_GET = dispatch
    do_POST = dispatch
