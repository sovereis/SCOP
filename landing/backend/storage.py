"""Durable signup adapter using the configured Supabase PostgREST endpoint."""
import json
import urllib.request
from uuid import uuid4

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

class SupabaseStore:
    def __init__(self, url, key):
        self.url = url
        self.key = key

    def save(self, value):
        identity = str(uuid4())
        row = {**value, 'id': identity, 'consent_version': 'landing-v1'}
        request = urllib.request.Request(
            self.url + '/rest/v1/scop_signups?select=id',
            data=json.dumps(row).encode(), method='POST',
            headers={'apikey': self.key, 'Authorization': 'Bearer ' + self.key,
                     'Content-Type': 'application/json', 'Prefer': 'return=representation'})
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=8) as response:
            raw = response.read(4097)
            if response.status != 201 or len(raw) > 4096:
                raise ValueError('Storage acknowledgement invalid')
            if json.loads(raw) != [{'id': identity}]:
                raise ValueError('Storage acknowledgement invalid')
