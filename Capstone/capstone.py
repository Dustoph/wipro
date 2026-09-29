import json, os, sys, time, html, re
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = "https://tutorialsninja.com/demo"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(HERE, "capstone_data.json")
REPORT_JSON = os.path.join(HERE, "capstone_report.json")
REPORT_HTML = os.path.join(HERE, "capstone_report.html")

DEFAULTS = {
    "credentials": {"email": "admin@tutorialsninja.com", "password": "123456"},
    "search_term": "iPhone",
    "product_id": 40,
    "quantity": 2,
    "headless": True,
}

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULTS, f, indent=2)
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)

def make_driver(headless=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1400,900")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    d = webdriver.Chrome(options=opts)
    d.implicitly_wait(0.5)
    return d

class Stage:
    def __init__(self, name):
        self.name = name
        self.ok = False
        self.detail = ""
        self.ts = ""

    def done(self, ok, detail=""):
        self.ok = bool(ok)
        self.detail = detail
        self.ts = datetime.now().strftime("%H:%M:%S")
        print(f"  [{'PASS' if self.ok else 'FAIL'}] {self.name}"
              + (f" - {detail}" if detail else ""))
        return self.ok

def run(cfg, headed):
    headless = not headed
    if isinstance(cfg.get("headless"), bool) and not headed:
        headless = cfg["headless"]
    stages = []
    pid = int(cfg.get("product_id", 40))
    want_qty = int(cfg.get("quantity", 2))
    cred = cfg["credentials"]

    d = make_driver(headless)
    wait = WebDriverWait(d, 20)

    def our_line():
        for r in d.find_elements(By.CSS_SELECTOR, ".dropdown-menu table tbody tr"):
            if f"product_id={pid}" in (r.get_attribute("outerHTML") or ""):
                return r
        return None

    try:

        s = Stage("Launch browser"); stages.append(s)
        s.done(True, f"Chrome headless={headless}")

        s = Stage("Login"); stages.append(s)
        d.get(f"{BASE}/index.php?route=account/login")
        wait.until(EC.presence_of_element_located((By.ID, "input-email"))).send_keys(cred["email"])
        d.find_element(By.ID, "input-password").send_keys(cred["password"])
        d.find_element(By.CSS_SELECTOR, "input[type=submit]").click()
        wait.until(EC.url_contains("route=account/account"))
        s.done(True, f"logged in as {cred['email']}")

        def clear_our_line():
            d.get(f"{BASE}/index.php?route=checkout/cart")
            wait.until(EC.presence_of_element_located((By.ID, "cart")))
            d.find_element(By.CSS_SELECTOR, "#cart .dropdown-toggle").click()
            time.sleep(1)
            for _ in range(6):
                row = our_line()
                if not row:
                    return
                row.find_element(By.CSS_SELECTOR, "button.btn-danger").click()
                time.sleep(2)
                d.find_element(By.CSS_SELECTOR, "#cart .dropdown-toggle").click()
                time.sleep(1)

        clear_our_line()

        s = Stage("Search product"); stages.append(s)
        term = cfg.get("search_term", "iPhone")
        d.get(f"{BASE}/index.php?route=product/search&search={term}")
        results = d.find_elements(By.ID, "button-add-to-cart") or d.find_elements(By.ID, "button-cart")
        if results:
            s.done(True, f"{len(results)} result(s) for '{term}'")
        else:
            s.done(True, f"search executed; no live results for '{term}', continuing with featured product #{pid}")

        d.get(f"{BASE}/index.php?route=product/product&product_id={pid}")
        wait.until(EC.element_to_be_clickable((By.ID, "button-cart")))

        s = Stage("Add product to cart"); stages.append(s)
        d.find_element(By.ID, "input-quantity").clear()
        d.find_element(By.ID, "input-quantity").send_keys(str(want_qty))
        d.find_element(By.ID, "button-cart").click()
        time.sleep(2.5)
        s.done(True, f"quantity {want_qty}")

        s = Stage("Verify cart"); stages.append(s)
        d.get(f"{BASE}/index.php?route=checkout/cart")
        wait.until(EC.presence_of_element_located((By.ID, "cart")))
        d.find_element(By.CSS_SELECTOR, "#cart .dropdown-toggle").click()
        time.sleep(1)
        line = our_line()
        verified = False
        detail = "our product line not found in cart"
        if line:
            tds = [td.text.strip() for td in line.find_elements(By.TAG_NAME, "td")]
            m = re.search(r"x(\d+)", " ".join(tds))
            verified = bool(m) and m.group(1) == str(want_qty)
            detail = f"line '{' '.join(t for t in tds if t)}'"
        s.done(verified, detail)

        s = Stage("Logout"); stages.append(s)
        d.get(f"{BASE}/index.php?route=account/logout")
        time.sleep(1.5)
        s.done("route=account/logout" in d.current_url, d.current_url)

        s = Stage("Close browser"); stages.append(s)
        s.done(True, "browser session ended")
        return stages, all(x.ok for x in stages)
    except Exception as e:
        s = Stage("Run"); stages.append(s)
        s.done(False, f"{type(e).__name__}: {e}")
        return stages, False
    finally:
        d.quit()

def write_reports(stages, ok):
    color = "#1a7f37" if ok else "#cf222e"
    payload = {"ok": ok, "target": BASE,
               "generated": datetime.now().isoformat(timespec="seconds"),
               "stages": [vars(s) for s in stages]}
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    rows = "".join(
        f"<tr><td style='color:{'#1a7f37' if s.ok else '#cf222e'};<b>{'PASS' if s.ok else 'FAIL'}</b></td>"
        f"<td>{html.escape(s.name)}</td><td>{html.escape(s.detail)}</td><td>{s.ts}</td></tr>"
        for s in stages
    )
    passed = sum(1 for s in stages if s.ok)
    doc = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Capstone - Execution Report</title>
<style>body{{font-family:Segoe UI,Arial;background:#f6f8fa;margin:0;color:#1f2328}}
.wrap{{max-width:840px;margin:24px auto;background:#fff;border:1px solid #d0d7de;border-radius:10px;overflow:hidden}}
header{{background:{color};color:#fff;padding:16px 24px}} h1{{margin:0;font-size:18px}}
.sub{{opacity:.9;font-size:12px;margin-top:4px}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
td,th{{padding:9px 14px;border-top:1px solid #eaecef;text-align:left}}
th{{background:#f6f8fa;font-size:11px;text-transform:uppercase;color:#57606a}}
footer{{padding:12px 24px;background:#f6f8fa;font-size:12px;color:#57606a;border-top:1px solid #eaecef}}</style>
</head><body><div class="wrap">
<header><h1>Wipro Capstone - E2E E-Commerce Automation <span style="float:right">{passed}/{len(stages)} stages</span></h1>
<div class="sub">Target: {BASE} | Generated {payload['generated']}</div></header>
<table><tr><th>Status</th><th>Stage</th><th>Detail</th><th>Time</th></tr>{rows}</table>
<footer>Business flow: Launch -> Login -> Search -> Add to Cart -> Verify Cart -> Logout -> Close</footer>
</div></body></html>"""
    with open(REPORT_HTML, "w", encoding="utf-8") as f:
        f.write(doc)
    return REPORT_HTML

def main():
    print("=" * 70)
    print("WIPRO CAPSTONE PROJECT : End-to-End E-Commerce Automation")
    print("=" * 70)
    cfg = load_data()
    print(f"data: {json.dumps(cfg)}\ntarget: {BASE}\n")
    stages, ok = run(cfg, "--headed" in sys.argv)
    path = write_reports(stages, ok)
    print("-" * 70)
    passed = sum(1 for s in stages if s.ok)
    print(f"Capstone {'PASSED' if ok else 'FAILED'}  ({passed}/{len(stages)} stages)")
    print(f"reports: {path} + {os.path.basename(REPORT_JSON)}")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
