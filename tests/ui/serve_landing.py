"""Disposable landing preview for browser tests."""
import os
import tempfile
from server.scop_landing import LandingServer

with tempfile.TemporaryDirectory(prefix='scop-signup-test-') as directory:
    with LandingServer(0, None if os.getenv('SCOP_NO_SIGNUPS') else directory) as server:
        print(server.origin, flush=True)
        server.serve_forever()
