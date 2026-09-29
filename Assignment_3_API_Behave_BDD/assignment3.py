import json, os, re, sys, time, html, shutil, subprocess
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
JSON_RESULTS = os.path.join(RESULTS_DIR, "behave_results.json")
ALLURE_RESULTS_DIR = os.path.join(RESULTS_DIR, "allure_results")
REPORT_HTML = os.path.join(HERE, "api_report.html")

FEATURE_FILES = {
    "features/user_management.feature": """\
@api @user_management @crud
Feature: User Management API
  As an API test engineer
  I want to exercise the CRUD operations of the user management REST API
  So that data integrity is verified automatically.

  Background:
    Given I am connected to the user management API

  @smoke
  Scenario: Fetch an existing user
    When I fetch the user with id 1
    Then the user name should be "Leanne Graham"
    And the user username should be "Bret"
    And the response should contain an email field

  Scenario: Create a new user
    When I create a user with name "Wipro Bot" and email "bot@wipro.test"
    Then the create response should be successful
    And a new user id should be assigned

  @update
  Scenario: Update a user
    When I update user 1's email to "updated@wipro.test"
    Then the update response should be successful

  Scenario: Delete a user
    When I delete the user with id 1
    Then the delete response should be successful
""",

    "features/auth.feature": """\
@api @authentication
Feature: API Authentication

  Background:
    Given I have API clients ready

  @bearer
  Scenario: Bearer token is required
    When I request the bearer endpoint without a token
    Then the request should be rejected with status 401

  Scenario: Valid bearer token authenticates the request
    When I request the bearer endpoint with the token "testtoken"
    Then the request should be authenticated
    And the echoed token should be "testtoken"

  @basic
  Scenario: Basic authentication succeeds for known credentials
    When I request basic auth for user "alice" with password "secret"
    Then the request should be authenticated
    And the authenticated user should be "alice"

  Scenario: Basic authentication fails for wrong password
    When I request basic auth for user "alice" with password "wrong"
    Then the request should be rejected with status 401
""",

    "features/environment.py": """\
import os, sys, json, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_client import RESTClient, load_config

def before_all(context):
    context.cfg = load_config()
    context.request_log = []

    def factory(kind):
        spec = context.cfg[kind]
        client = RESTClient(spec[\"base_url\"],
                            timeout=context.cfg.get(\"timeout_seconds\", 20))

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
""",

    "features/steps/__init__.py": "",

    "features/steps/steps.py": """\
from behave import given, when, then

@given('I am connected to the user management API')
def step_connected(context):
    context.user_client = context.client_factory('user_api')
    context.auth_client = context.client_factory('auth_api')
    context.last_response = None

@given('I have API clients ready')
def step_clients_ready(context):
    context.user_client = context.client_factory('user_api')
    context.auth_client = context.client_factory('auth_api')
    context.last_response = None

@when('I fetch the user with id {uid}')
def step_fetch(context, uid):
    r = context.user_client.get(f'users/{uid}')
    context.last_response = r
    context.last_user = r.json()

@then('the user name should be "{name}"')
def step_name(context, name):
    assert context.last_user.get('name') == name, \\
        f"expected name {name!r}, got {context.last_user.get('name')!r}"

@then('the user username should be "{username}"')
def step_username(context, username):
    assert context.last_user.get('username') == username, \\
        f"expected username {username!r}, got {context.last_user.get('username')!r}"

@then('the response should contain an email field')
def step_has_email(context):
    assert 'email' in context.last_user, "user payload has no email field"

@when('I create a user with name "{name}" and email "{email}"')
def step_create(context, name, email):
    r = context.user_client.post('users', json_body={'name': name, 'email': email})
    context.last_response = r
    context.created_user = r.json()

@then('the create response should be successful')
def step_create_ok(context):
    assert 200 <= context.last_response.status_code < 300, \\
        f"create failed with status {context.last_response.status_code}"

@then('a new user id should be assigned')
def step_created_id(context):
    uid = context.created_user.get('id')
    assert isinstance(uid, int) and uid > 0, f"no id assigned in {context.created_user!r}"
    context.last_created_id = uid

@when('I update user {uid}\\'s email to "{email}"')
def step_update(context, uid, email):
    r = context.user_client.put(f'users/{uid}', json_body={'email': email})
    context.last_response = r

@then('the update response should be successful')
def step_update_ok(context):
    assert context.last_response.status_code == 200, \\
        f"update failed with status {context.last_response.status_code}"

@when('I delete the user with id {uid}')
def step_delete(context, uid):
    r = context.user_client.delete(f'users/{uid}')
    context.last_response = r

@then('the delete response should be successful')
def step_delete_ok(context):
    assert context.last_response.status_code == 200, \\
        f"delete failed with status {context.last_response.status_code}"

@when('I request the bearer endpoint without a token')
def step_bearer_no_token(context):
    context.last_response = context.auth_client.get('bearer')

@when('I request the bearer endpoint with the token "{token}"')
def step_bearer_token(context, token):
    context.last_response = context.auth_client.get(
        'bearer', headers={'Authorization': f'Bearer {token}'})

@when('I request basic auth for user "{user}" with password "{password}"')
def step_basic(context, user, password):
    auth = (user, password) if password == 'secret' else None
    context.last_response = context.auth_client.get(
        f'basic-auth/{user}/{password}', auth=auth)

@then('the request should be rejected with status {code:d}')
def step_rejected(context, code):
    assert context.last_response.status_code == code, \\
        f"expected {code}, got {context.last_response.status_code}"

@then('the request should be authenticated')
def step_authenticated(context):
    body = context.last_response.json()
    assert body.get('authenticated') is True, f"not authenticated: {body!r}"

@then('the echoed token should be "{token}"')
def step_echoed_token(context, token):
    assert context.last_response.json().get('token') == token

@then('the authenticated user should be "{user}"')
def step_authed_user(context, user):
    assert context.last_response.json().get('user') == user
""",

    "api_client.py": """\
import json, os
import requests

class RESTClient:
    def __init__(self, base_url, timeout=20, session=None):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = session or requests.Session()
        self.last_request = None

    def _url(self, path):
        return f\"{self.base_url}/{path.lstrip('/')}\"

    def request(self, method, path, json_body=None, headers=None, auth=None):
        self.last_request = {\"method\": method, \"url\": self._url(path)}
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
        raise FileNotFoundError(f\"config.json not found at {path}\")
    with open(path, encoding='utf-8') as f:
        return json.load(f)
""",

    "config.json": json.dumps({
        "user_api": {"base_url": "https://jsonplaceholder.typicode.com"},
        "auth_api": {"base_url": "https://httpbin.org"},
        "timeout_seconds": 30,
    }, indent=2),
}

def write_artifacts():
    written = []
    for rel, content in FEATURE_FILES.items():
        path = os.path.join(HERE, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        written.append(rel)
    return written

def find_cli(name):
    exe = shutil.which(name)
    if exe:
        return [exe]
    return [sys.executable, "-m", name]

def run_behave():
    os.makedirs(ALLURE_RESULTS_DIR, exist_ok=True)
    cmd = find_cli("behave") + [
        os.path.join(HERE, "features"),
        "--format=json", "--outfile", JSON_RESULTS,
        "--format=allure_behave.formatter:AllureFormatter",
        "--outfile", ALLURE_RESULTS_DIR,
    ]
    p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
    print(p.stdout[-4000:] if len(p.stdout) > 4000 else p.stdout)
    if p.returncode != 0:
        print(p.stderr[-3000:] if p.stderr else "")
    return p.returncode

def parse_results():
    if not os.path.exists(JSON_RESULTS):
        return []
    with open(JSON_RESULTS, encoding="utf-8") as f:
        features = json.load(f)
    out = []
    for feat in features:
        ftags = feat.get("tags", [])
        for el in feat.get("elements", []):
            if el.get("keyword") not in ("Scenario", "Scenario Outline"):
                continue
            sc_tags = el.get("tags") or ftags
            out.append({
                "feature": feat.get("name", "?"),
                "scenario": el.get("name", "?"),
                "status": el.get("status", "?"),
                "tags": ",".join(sc_tags),
                "steps": [
                    {"line": s.get("line", ""), "text": s.get("text", ""),
                     "status": s.get("status", "")}
                    for s in el.get("steps", [])
                ],
            })
    return out

def try_allure_cli():
    allure = shutil.which("allure")
    if not allure:
        return None
    out_dir = os.path.join(HERE, "allure-report")
    p = subprocess.run([allure, "generate", ALLURE_RESULTS_DIR,
                        "-o", out_dir, "--clean"],
                       capture_output=True, text=True)
    return out_dir if p.returncode == 0 else None

def write_html_report(scenarios, json_rc, allure_ok):
    total = len(scenarios)
    passed = sum(1 for s in scenarios if s["status"] == "passed")
    ok = total > 0 and passed == total and json_rc == 0
    color = "#1a7f37" if ok else "#cf222e"
    rows = []
    for s in scenarios:
        c = {"passed": "#1a7f37", "failed": "#cf222e"}.get(s["status"], "#9a6700")
        step_rows = "".join(
            f'<td style="color:#57606a;font-size:11px;white-space:nowrap">{st["line"]}</td>'
            f'<td>{html.escape(st["text"])}</td>'
            f'<td style="color:#57606a">{st["status"]}</td>'
            for st in s["steps"]
        )
        rows.append(f"""
        <tr style="border-top:1px solid #eaecef">
          <td style="padding:8px 10px"><b>{html.escape(s['scenario'])}</b><br>
          <span style="font-size:11px;color:#57606a">Feature: {html.escape(s['feature'])}
          | Tags: {html.escape(s['tags'] or '-')}</span></td>
          <td style="padding:8px 10px;width:80px;color:{c};font-weight:700;text-transform:uppercase">
              {s['status']}</td>
        </tr>
        <tr><td colspan="2" style="padding:0 10px 8px">{step_rows}</td></tr>""")
    doc = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Assignment 3 - API BDD Report</title>
<style>body{{font-family:Segoe UI,Arial;background:#f6f8fa;margin:0;color:#1f2328}}
.wrap{{max-width:900px;margin:24px auto;background:#fff;border:1px solid #d0d7de;border-radius:10px;overflow:hidden}}
header{{background:{color};color:#fff;padding:16px 24px}} h1{{margin:0;font-size:19px}}
.sub{{opacity:.9;font-size:12px;margin-top:4px}}
h2{{padding:10px 24px;margin:0;font-size:13px;text-transform:uppercase;letter-spacing:.03em;
color:#57606a;background:#f6f8fa;border-top:1px solid #eaecef}}
footer{{padding:12px 24px;background:#f6f8fa;font-size:12px;color:#57606a;border-top:1px solid #eaecef}}</style>
</head><body><div class="wrap">
<header><h1>Assignment 3 - API Automation (Requests + Behave BDD + Allure)
 <span style="float:right">{passed}/{total} passed</span></h1>
 <div class="sub">APIs: jsonplaceholder.typicode.com (CRUD) + httpbin.org (auth)
 | Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 | Allure results: results/allure_results{' (report generated)' if allure_ok else ' (run: allure generate results/allure_results -o allure-report)'}
</div></header>
<h2>Scenarios</h2><table style="width:100%;border-collapse:collapse">{"".join(rows)}</table>
<footer>behave exit={json_rc} | {passed} passed / {total - passed} failed of {total} scenarios
| Framework: requests + behave + allure-behave (single-file generator: assignment3.py)</footer>
</div></body></html>"""
    with open(REPORT_HTML, "w", encoding="utf-8") as f:
        f.write(doc)
    return ok

def main():
    print("=" * 70)
    print("WIPRO CAPSTONE - ASSIGNMENT 3 : API Automation (Requests + Behave BDD)")
    print("=" * 70)
    written = write_artifacts()
    print(f"framework artifacts written ({len(written)} files):")
    for w in written:
        print(f"   - {w}")
    print("-" * 70)

    print("\n>> running Behave BDD suite (JSON + Allure in one pass)")
    rc = run_behave()
    print(f"   behave exit code: {rc}")
    allure_dir = try_allure_cli()

    scenarios = parse_results()
    ok = write_html_report(scenarios, rc, bool(allure_dir))
    total = len(scenarios)
    passed = sum(1 for s in scenarios if s["status"] == "passed")

    print("-" * 70)
    print(f"scenarios: {passed}/{total} passed")
    if allure_dir:
        print(f"allure report: {allure_dir}")
    else:
        print(f"allure results: {ALLURE_RESULTS_DIR} "
              f"(install the Allure CLI to render: 'allure generate results/allure_results -o allure-report')")
    print(f"HTML summary : {REPORT_HTML}")
    print(f"Suite {'PASSED' if ok and rc == 0 else 'FAILED'}")
    sys.exit(0 if ok and rc == 0 else 1)

if __name__ == "__main__":
    main()
