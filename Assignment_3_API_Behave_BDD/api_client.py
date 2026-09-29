import json, os
import requests

class RESTClient:
    def __init__(self, base_url, timeout=20, session=None):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = session or requests.Session()
        self.last_request = None

    def _url(self, path):
        return f"{self.base_url}/{path.lstrip('/')}"

    def request(self, method, path, json_body=None, headers=None, auth=None):
        self.last_request = {"method": method, "url": self._url(path)}
        return self.session.request(
            method, self._url(path), json=json_body,
            headers=headers, auth=auth, timeout=self.timeout)

    def get(self, path, **kw):      return self.request('GET', path, **kw)
    def post(self, path, **kw):     return self.request('POST', path, **kw)
    def put(self, path, **kw):      return self.request('PUT', path, **kw)
    def patch(self, path, **kw):    return self.request('PATCH', path, **kw)
    def delete(self, path, **kw):   return self.request('DELETE', path, **kw)

def load_config(path=None):
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    if not os.path.exists(path):
        raise FileNotFoundError(f"config.json not found at {path}")
    with open(path, encoding='utf-8') as f:
        return json.load(f)
