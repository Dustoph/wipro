import os, sys, json, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_client import RESTClient, load_config

def before_all(context):
    context.cfg = load_config()
    context.request_log = []

    def factory(kind):
        spec = context.cfg[kind]
        client = RESTClient(spec["base_url"],
                            timeout=context.cfg.get("timeout_seconds", 20))

        _orig = client.request

        def _logged(method, path, **kw):
            resp = _orig(method, path, **kw)
            context.request_log.append({
                "kind": kind, "method": method, "path": path,
                "status": resp.status_code, "timestamp": time.time(),
            })
            return resp

        client.request = _logged
        return client

    context.client_factory = factory

def after_all(context):
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "request_log.json")
    with open(out, "w") as f:
        json.dump(context.request_log, f, indent=2)
    print(f"[env] logged {len(context.request_log)} request(s) -> request_log.json")
