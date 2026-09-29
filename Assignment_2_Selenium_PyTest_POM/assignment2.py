import csv, json, os, sys, time, subprocess, shutil

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(HERE, "reports")
SCREEN_DIR = os.path.join(REPORT_DIR, "screenshots")
CONFIG_JSON = os.path.join(HERE, "config.json")
LOGIN_CSV = os.path.join(HERE, "login_data.csv")
PRODUCT_CSV = os.path.join(HERE, "product_data.csv")

DEFAULT_CONFIG = {
    "base_url": "https://tutorialsninja.com/demo",
    "login_email": "admin@tutorialsninja.com",
    "login_password": "123456",
    "search_term": "ipad",
    "product_id": 40,
    "headless": True,
    "implicit_wait": 2,
    "explicit_wait": 15,
}

def save_config():
    with open(CONFIG_JSON, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    return load_config()

def load_config():
    if os.path.exists(CONFIG_JSON):
        with open(CONFIG_JSON, encoding="utf-8") as f:
            return json.load(f)
    return dict(DEFAULT_CONFIG)

def write_test_data():
    login_rows = [
        ["case", "email", "password", "expect"],
        ["valid", "admin@tutorialsninja.com", "123456", "success"],
        ["invalid", "admin@tutorialsninja.com", "wrong-pass", "error"],
    ]
    with open(LOGIN_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(login_rows)
    prod_rows = [
        ["search_term", "product_id", "expect"],
        ["ipad", 40, "found"],
        ["imac", 43, "found"],
    ]
    with open(PRODUCT_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(prod_rows)

    with open(LOGIN_CSV, encoding="utf-8") as f:
        valid = [r for r in csv.DictReader(f) if r["expect"] == "success"][0]
    return valid

class BrowserManager:
    def __init__(self, cfg=None):
        self.cfg = cfg or load_config()
        self.driver = None
        self.wait = None
        self.screenshots = []

    def start(self):
        opts = Options()
        if self.cfg.get("headless", True):
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1400,900")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        self.driver = webdriver.Chrome(options=opts)
        self.driver.implicitly_wait(self.cfg.get("implicit_wait", 2))
        self.wait = WebDriverWait(self.driver, self.cfg.get("explicit_wait", 15))
        os.makedirs(SCREEN_DIR, exist_ok=True)
        return self.driver

    def screenshot(self, tag):
        if not self.driver:
            return None
        path = os.path.join(SCREEN_DIR, f"{tag}.png")
        try:
            self.driver.save_screenshot(path)
            self.screenshots.append(os.path.basename(path))
        except Exception:
            pass
        return path

    def stop(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    @property
    def base_url(self):
        return self.cfg["base_url"]

class BasePage:
    def __init__(self, browser):
        self.bm = browser
        self.driver = browser.driver
        self.wait = browser.wait
        self.base = browser.base_url

    def open(self, path):
        self.driver.get(self.base + path)

    def screenshot(self, tag):
        return self.bm.screenshot(tag)

    def wait_visible(self, by, value, desc=""):
        return self.wait.until(EC.visibility_of_element_located((by, value)))

class LoginPage(BasePage):
    EMAIL = (By.ID, "input-email")
    PASSWORD = (By.ID, "input-password")
    SUBMIT = (By.CSS_SELECTOR, "input[type=submit]")
    ERROR = (By.CSS_SELECTOR, ".alert-danger, #error")
    ACCOUNT_URL = "index.php?route=account/account"
    LOGIN_URL = "index.php?route=account/login"
    LOGOUT_URL = "index.php?route=account/logout"

    def go(self):
        self.open("/" + self.LOGIN_URL)

    def logout(self):
        self.open("/" + self.LOGOUT_URL)
        self.open("/" + self.LOGIN_URL)

    def login(self, email, password):
        self.logout()
        self.wait_visible(*self.EMAIL).send_keys(email)
        self.driver.find_element(*self.PASSWORD).send_keys(password)
        self.driver.find_element(*self.SUBMIT).click()

        def settled(driver):
            if self.ACCOUNT_URL in driver.current_url:
                return True
            return any(e.is_displayed() for e in driver.find_elements(*self.ERROR))

        self.wait.until(settled)
        return self

    def logged_in(self):
        return self.ACCOUNT_URL in self.driver.current_url

    def error_visible(self):
        try:
            el = self.wait.until(EC.presence_of_element_located(self.ERROR))
            return el.is_displayed()
        except TimeoutException:
            return False

class ProductPage(BasePage):
    SEARCH_URL = "/index.php?route=product/search&search={term}"
    PRODUCT_URL = "/index.php?route=product/product&product_id={pid}"
    H1 = (By.TAG_NAME, "h1")

    def search(self, term):
        self.open(self.SEARCH_URL.format(term=term))
        try:
            self.wait.until(EC.presence_of_element_located((By.ID, "heading-title")))
        except TimeoutException:
            pass
        return self

    def heading(self):
        try:
            return self.wait_visible(*self.H1).text.strip()
        except NoSuchElementException:
            return ""

    def page_text(self):
        return self.driver.find_element(By.TAG_NAME, "body").text

import pytest

@pytest.fixture(scope="session")
def browser():
    cfg = load_config()
    bm = BrowserManager(cfg)
    bm.start()
    yield bm
    bm.stop()

@pytest.fixture(autouse=True)
def _capture_on_failure(request, browser):
    yield
    call = getattr(request.node, "rep_call", None)
    if call is None:
        return
    tag = "PASS_" if call.passed else "FAIL_"
    browser.screenshot(f"{tag}{request.node.name}")

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, when):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + when, rep)

def test_login_success(browser):
    row = write_test_data()
    page = LoginPage(browser)
    page.login(row["email"], row["password"])
    assert page.logged_in(), "login did not reach the account dashboard"
    browser.screenshot("login_success")

def test_login_failure(browser):
    bad = write_test_data()["password"]
    page = LoginPage(browser)
    page.login("admin@tutorialsninja.com", "definitely-wrong-" + bad)
    assert not page.logged_in(), "wrong password should NOT reach the dashboard"
    assert page.error_visible(), "an error banner should be shown on bad login"

def test_product_search(browser):
    row = write_test_data()
    page = ProductPage(browser)

    LoginPage(browser).login(row["email"], row["password"])
    term = load_config()["search_term"]
    page.search(term)
    heading = page.heading()
    text = page.page_text().lower()

    assert term in text or term in heading.lower(), (
        f"search term '{term}' should be reflected on the results page "
        f"(heading={heading!r})")
    browser.screenshot(f"search_{term}")

def test_product_page_loads(browser):
    cfg = load_config()
    page = ProductPage(browser)
    page.open("/" + page.PRODUCT_URL.format(pid=cfg["product_id"]))
    assert page.driver.find_element(*ProductPage.H1), "product page should render an h1"
    browser.screenshot(f"product_{cfg['product_id']}")

import unittest

class TestSeleniumFramework(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bm = BrowserManager(load_config())
        cls.bm.start()

    @classmethod
    def tearDownClass(cls):
        cls.bm.stop()

    def test_01_login_success(self):
        row = write_test_data()
        page = LoginPage(self.bm)
        page.login(row["email"], row["password"])
        self.assertTrue(page.logged_in(), "should reach account dashboard")
        self.bm.screenshot("unit_login_success")

    def test_02_search_echo(self):
        row = write_test_data()
        LoginPage(self.bm).login(row["email"], row["password"])
        term = load_config()["search_term"]
        page = ProductPage(self.bm)
        page.search(term)
        self.assertIn(term, page.page_text().lower(), "search term must be echoed on the page")
        self.bm.screenshot("unit_search")

def write_summary(pytest_rc, unittest_rc):
    ok = pytest_rc == 0 and unittest_rc == 0
    color = "#1a7f37" if ok else "#cf222e"
    shots = [f for f in sorted(os.listdir(SCREEN_DIR))] if os.path.exists(SCREEN_DIR) else []
    imgs = "".join(
        f'<figure style="width:240px;display:inline-block;margin:6px">'
        f'<img src="screenshots/{s}" style="width:220px;border:1px solid #ddd">'
        f'<figcaption style="font-size:11px;color:#57606a">{s}</figcaption></figure>'
        for s in shots
    )
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Assignment 2 - Framework Report</title>
<style>body{{font-family:Segoe UI,Arial;background:#f6f8fa;margin:0;color:#1f2328}}
.wrap{{max-width:1000px;margin:24px auto;background:#fff;border:1px solid #d0d7de;border-radius:10px;padding:24px}}
h1{{margin:0}} .b{{display:inline-block;background:{color};color:#fff;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:700}}
.grid{{display:flex;gap:16px;flex-wrap:wrap;margin-top:16px}}
.card{{border:1px solid #eaecef;border-radius:8px;padding:14px;flex:1;min-width:220px}}
code{{background:#f6f8fa;padding:1px 5px;border-radius:4px;font-size:12px}}</style></head>
<body><div class="wrap">
<h1>Assignment 2 - Selenium Framework (Unittest + PyTest + POM)
 <span class="b">{'ALL PASS' if ok else 'HAS FAILURES'}</span></h1>
<div class="grid">
  <div class="card"><b>PyTest</b> &nbsp;exit <code>{pytest_rc}</code><br>
    HTML report: <code>pytest_report.html</code> (pytest-html)</div>
  <div class="card"><b>Unittest</b> &nbsp;exit <code>{unittest_rc}</code><br>
    2 tests (login + search) via <code>unittest.TestCase</code></div>
  <div class="card"><b>Framework pieces</b><br>
    POM: LoginPage, ProductPage<br>Utilities: BrowserManager, screenshot-on-failure<br>
    Config: <code>config.json</code> &nbsp; CSV: <code>login_data.csv</code>, <code>product_data.csv</code></div>
</div>
<h3 style="margin-top:22px">Captured screenshots ({len(shots)})</h3>
<div style="margin-top:8px">{imgs or '<i>none</i>'}</div>
</div></body></html>"""
    out = os.path.join(HERE, "framework_report.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return out, ok

def run_pytest():
    cmd = [sys.executable, "-m", "pytest", os.path.basename(__file__),
           "--html=pytest_report.html", "--self-contained-html",
           "-p", "no:cacheprovider", "--tb=short", "-o", "addopts="]
    p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
    sys.stdout.write(p.stdout)
    if p.stderr:
        sys.stderr.write(p.stderr)
    return p.returncode

def run_unittest():
    p = subprocess.run([sys.executable, "-m", "unittest", "assignment2", "-v"],
                       cwd=HERE, capture_output=True, text=True)
    sys.stdout.write(p.stdout)
    if p.stderr:
        sys.stderr.write(p.stderr)
    return p.returncode

def main():
    print("=" * 70)
    print("WIPRO CAPSTONE - ASSIGNMENT 2 : Selenium + PyTest + Unittest + POM")
    print("=" * 70)
    cfg = save_config()
    write_test_data()
    print(f"config written -> {os.path.basename(CONFIG_JSON)}")
    print(f"CSV data written -> {os.path.basename(LOGIN_CSV)}, {os.path.basename(PRODUCT_CSV)}")
    print("-" * 70)

    print("\n>> PyTest run (session driver + HTML report + screenshot-on-failure)")
    pytest_rc = run_pytest()
    print(f"   pytest exit code: {pytest_rc}\n")

    print(">> Unittest run (module driver)")
    unittest_rc = run_unittest()
    print(f"   unittest exit code: {unittest_rc}\n")

    path, ok = write_summary(pytest_rc, unittest_rc)
    print("-" * 70)
    print(f"Framework {'PASSED' if ok else 'FAILED'} -> {path}")
    print(f"pytest HTML report : {os.path.join(HERE, 'pytest_report.html')}")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
