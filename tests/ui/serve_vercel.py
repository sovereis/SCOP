"""Local transport harness for production code. Database writes are test doubles."""
from http.server import HTTPServer
import os
from pathlib import Path
import tempfile
from unittest.mock import patch
from landing.backend.http import SignupHandler
from landing.build import build

class Preview(SignupHandler):
    def do_GET(self):
        if self.path.startswith('/api/'):
            return self.dispatch()
        names = {'/':'index.html','/style.css':'style.css','/app.js':'app.js','/assets/hero.webp':'assets/hero.webp'}
        name = names.get(self.path)
        if name is None:
            self.send_error(404)
            return
        raw = (Path(self.server.assets) / name).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', {'html':'text/html','css':'text/css','js':'text/javascript','webp':'image/webp'}[name.split('.')[-1]])
        self.end_headers()
        self.wfile.write(raw)

    def dispatch(self):
        # Only this test harness translates local browser origin to the configured HTTPS origin.
        for name in ('Host', 'Origin'):
            value = self.headers.get(name)
            if value and value in (f'127.0.0.1:{self.server.server_port}', f'http://127.0.0.1:{self.server.server_port}'):
                self.headers.replace_header(name, 'scop.example.com' if name == 'Host' else 'https://scop.example.com')
        return super().dispatch()

    do_POST = dispatch

os.environ.update(SCOP_PUBLIC_ORIGIN='https://scop.example.com', SCOP_SUPABASE_URL='https://testproject.supabase.co',
                  SCOP_SUPABASE_SERVICE_ROLE_KEY='test-key-'*5, SCOP_SIGNUP_SECRET='test-secret-'*4)
if os.getenv('SCOP_NO_PRODUCTION_STORE'):
    del os.environ['SCOP_SUPABASE_SERVICE_ROLE_KEY']
with tempfile.TemporaryDirectory() as directory:
    build(directory)
    with HTTPServer(('127.0.0.1',0),Preview) as server:
        server.assets = directory
        print(f'http://127.0.0.1:{server.server_port}',flush=True)
        with patch('landing.backend.production.SupabaseStore.save'):
            server.serve_forever()
