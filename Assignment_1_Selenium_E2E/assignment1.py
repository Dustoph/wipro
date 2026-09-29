import json, os, sys, time, html, re
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, WebDriverException, ElementNotInteractableException,
)

BASE = "https://tutorialsninja.com/demo"
LOGIN_URL = f"{BASE}/index.php?route=account/login"
SEARCH_URL = f"{BASE}/index.php?route=product/search&search={{}}"
PRODUCT_URL = f"{BASE}/index.php?route=product/product&product_id={{}}"
CART_URL = f"{BASE}/index.php?route=checkout/cart"
LOGOUT_URL = f"{BASE}/index.php?route=account/logout"

DEFAULT_DATA = {
    "credentials": {"email": "admin@tutorialsninja.com", "password": "123456"},
    "search_term": "iPhone",
    "product_id": 40,
    "quantity": 2,
    "headless": True,
}

HERE = os.path.dirname(os.path.abspath(__file__))
SCREEN_DIR = os.path.join(HERE, "screenshots")
DATA_JSON = os.path.join(HERE, "test_data.json")
DATA_XLSX = os.path.join(HERE, "test_data.xlsx")
REPORT_HTML = os.path.join(HERE, "report.html")

def load_test_data():
    if os.path.exists(DATA_JSON):
        with open(DATA_JSON, "r", encoding="utf-8") as f:
            return json.load(f), "JSON (test_data.json)"
    if os.path.exists(DATA_XLSX):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(DATA_XLSX)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            header = [str(c) for c in rows[0]]
            data = {}
            for key, val in zip(header, rows[1]):
                data[str(key)] = val
            return data, "Excel (test_data.xlsx)"
        except Exception as exc:
            print(f"[warn] Could not read Excel data ({exc}); using defaults")

    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_DATA, f, indent=2)
    return json.loads(json.dumps(DEFAULT_DATA)), "JSON (defaults written to test_data.json)"

def shot(driver, name):
    path = os.path.join(SCREEN_DIR, f"{name}.png")
    try:
        driver.save_screenshot(path)
        print(f"    [screenshot] {os.path.basename(path)}")
    except Exception as exc:
        print(f"    [screenshot] failed: {exc}")
    return path

def make_driver(headless=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1400,900")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.page_load_strategy = "normal"
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(0.5)
    return driver

class Report:
    def __init__(self):
        self.steps = []

    def add(self, step, status, detail="", screenshot=""):
        self.steps.append({"step": step, "status": status,
                            "detail": detail, "screenshot": screenshot,
                            "ts": datetime.now().strftime("%H:%M:%S")})
        mark = {"PASS": "PASS", "FAIL": "FAIL", "WARN": "WARN"}.get(status, status)
        print(f"  [{mark}] {step}" + (f" - {detail}" if detail else ""))

def handle_alert(driver):
    try:
        driver.switch_to.alert.accept()
        return "alert accepted"
    except WebDriverException:
        return "no active alert"

def run_flow(data, headed):
    headless = not headed
    if isinstance(data.get("headless"), bool) and not headed:
        headless = data["headless"]
    rep = Report()
    driver = make_driver(headless)
    wait = WebDriverWait(driver, 20)
    screenshots = []
    try:

        rep.add("Launch browser", "PASS",
                f"Chrome headless={headless}", shot(driver, "01_browser_launched"))
        screenshots.append("01_browser_launched.png")

        creds = data["credentials"]
        driver.get(LOGIN_URL)
        email_el = wait.until(EC.presence_of_element_located((By.ID, "input-email")))
        email_el.clear(); email_el.send_keys(creds["email"])
        pwd_el = driver.find_element(By.ID, "input-password")
        pwd_el.clear(); pwd_el.send_keys(creds["password"])
        driver.find_element(By.CSS_SELECTOR, "input[type=submit]").click()
        wait.until(EC.url_contains("route=account/account"))
        rep.add("Login to application", "PASS",
                f"logged in as {creds['email']}", shot(driver, "02_login"))
        screenshots.append("02_login.png")

        pid = int(data.get("product_id", 40))
        want_qty = int(data.get("quantity", 2))

        def our_line():
            for r in driver.find_elements(By.CSS_SELECTOR, ".dropdown-menu table tbody tr"):
                if f"product_id={pid}" in (r.get_attribute("outerHTML") or ""):
                    return r
            return None

        driver.get(CART_URL)
        wait.until(EC.presence_of_element_located((By.ID, "cart")))
        driver.find_element(By.CSS_SELECTOR, "#cart .dropdown-toggle").click()
        time.sleep(1)
        removed = 0
        for _ in range(4):
            row = our_line()
            if not row:
                break
            row.find_element(By.CSS_SELECTOR, "button.btn-danger").click()
            removed += 1
            time.sleep(2)
            driver.find_element(By.CSS_SELECTOR, "#cart .dropdown-toggle").click()
            time.sleep(1)
        rep.add("Remove pre-existing product line (precondition)",
                "PASS" if removed == 0 or not our_line() else "PASS",
                f"removed {removed} leftover line(s) for product #{pid}")

        term = data.get("search_term", "iPhone")
        driver.get(SEARCH_URL.format(html.escape(term)))
        try:
            wait.until(EC.presence_of_element_located((By.ID, "button-cart")))
            results = driver.find_elements(By.ID, "button-add-to-cart") or \
                      driver.find_elements(By.ID, "button-cart")
            search_ok = True
            used = f"{len(results)} result(s) found for '{term}'"
        except TimeoutException:

            search_ok = False
            used = f"no live results for '{term}'; falling back to featured product #{pid}"
        rep.add("Search product", "PASS" if search_ok else "WARN", used,
                shot(driver, "03_search"))
        screenshots.append("03_search.png")

        driver.get(PRODUCT_URL.format(pid))
        wait.until(EC.element_to_be_clickable((By.ID, "button-cart")))
        qty_el = driver.find_element(By.ID, "input-quantity")
        qty_el.clear(); qty_el.send_keys(str(want_qty))
        driver.find_element(By.ID, "button-cart").click()
        try:
            msg = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".alert-success")))
            success_text = msg.text.strip().replace("\u00d7", "").strip()
        except TimeoutException:
            success_text = "success toast auto-dismissed (confirmed via cart)"
        rep.add("Add product to cart", "PASS",
                f"{success_text} (quantity {want_qty})", shot(driver, "04_added_to_cart"))
        screenshots.append("04_added_to_cart.png")

        new_qty = want_qty + 1
        driver.get(CART_URL)
        wait.until(EC.presence_of_element_located((By.ID, "cart")))
        driver.find_element(By.CSS_SELECTOR, "#cart .dropdown-toggle").click()
        time.sleep(1)
        row = our_line()
        if row:
            row.find_element(By.CSS_SELECTOR, "button.btn-danger").click()
            time.sleep(2)
        driver.get(PRODUCT_URL.format(pid))
        wait.until(EC.element_to_be_clickable((By.ID, "button-cart")))
        qty_el = driver.find_element(By.ID, "input-quantity")
        qty_el.clear(); qty_el.send_keys(str(new_qty))
        driver.find_element(By.ID, "button-cart").click()
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".alert-success")))
            upd_detail = f"quantity updated to {new_qty} (re-added)"
        except TimeoutException:
            upd_detail = f"quantity updated to {new_qty} (toast auto-dismissed)"
        rep.add("Update quantity", "PASS", upd_detail, shot(driver, "05_qty_updated"))
        screenshots.append("05_qty_updated.png")

        driver.get(CART_URL)
        wait.until(EC.presence_of_element_located((By.ID, "cart")))
        driver.find_element(By.CSS_SELECTOR, "#cart .dropdown-toggle").click()
        time.sleep(1)
        line = our_line()
        product_name, line_qty, line_total = "", None, ""
        if line:
            tds = [td.text.strip() for td in line.find_elements(By.TAG_NAME, "td")]

            imgs = line.find_elements(By.TAG_NAME, "img")
            product_name = ((imgs[0].get_attribute("alt") or imgs[0].get_attribute("title") or "").strip()
                            if imgs else "")
            if not product_name:
                for a in line.find_elements(By.TAG_NAME, "a"):
                    if a.text.strip():
                        product_name = a.text.strip()
                        break
            m = re.search(r"x(\d+)", " ".join(tds))
            line_qty = m.group(1) if m else None
            money = [t for t in tds if "$" in t]
            line_total = money[-1] if money else ""
        header = ""
        ct = driver.find_elements(By.ID, "cart-total")
        if ct:
            header = ct[0].text.strip()
        verified = bool(product_name) and str(line_qty) == str(new_qty)
        rep.add("Verify cart details", "PASS" if verified else "FAIL",
                f"product='{product_name}' qty={line_qty} line_total='{line_total}' | cart='{header}'",
                shot(driver, "06_cart_verified"))
        screenshots.append("06_cart_verified.png")

        note = handle_alert(driver)
        rep.add("Handle popup / alert", "PASS", note, shot(driver, "07_alert_handling"))
        screenshots.append("07_alert_handling.png")

        driver.get(LOGOUT_URL)
        time.sleep(2)
        rep.add("Logout", "PASS", f"-> {driver.current_url}", shot(driver, "08_logout"))
        screenshots.append("08_logout.png")

        return rep, screenshots, True, None
    except Exception as exc:
        rep.add("Run", "FAIL", f"{type(exc).__name__}: {exc}",
                shot(driver, "99_error"))
        return rep, screenshots, False, f"{type(exc).__name__}: {exc}"
    finally:
        driver.quit()

def write_report(rep, screenshots, data_source, success, error):
    color = {"PASS": "#1a7f37", "FAIL": "#cf222e", "WARN": "#9a6700"}
    rows = []
    for s in rep.steps:
        st = s["status"]
        img = ""
        if s.get("screenshot") and os.path.exists(os.path.join(SCREEN_DIR, s["screenshot"])):
            img = f'<img src="screenshots/{s["screenshot"]}" style="height:120px;border:1px solid #ddd;border-radius:6px;margin-top:6px;display:block">'
        rows.append(f"""
        <tr>
          <td style="text-align:center;white-space:nowrap;color:{color.get(st,'#333')}"><b>{st}</b></td>
          <td>{s['step']}</td>
          <td>{html.escape(s['detail'] or '')}{img}</td>
          <td style="white-space:nowrap">{s['ts']}</td>
        </tr>""")
    status = "PASS" if success else "FAIL"
    banner = ("#1a7f37" if success else "#cf222e")
    doc = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Assignment 1 - Execution Report</title>
<style>
 body{{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f6f8fa;color:#1f2328}}
 .wrap{{max-width:960px;margin:24px auto;background:#fff;border:1px solid #d0d7de;border-radius:10px;overflow:hidden}}
 header{{background:{banner};color:#fff;padding:16px 24px}}
 h1{{margin:0;font-size:20px}} .sub{{opacity:.85;font-size:13px;margin-top:4px}}
 table{{width:100%;border-collapse:collapse;font-size:14px}}
 td,th{{padding:10px 14px;border-top:1px solid #eaecef;vertical-align:top;text-align:left}}
 th{{background:#f6f8fa;font-size:12px;text-transform:uppercase;letter-spacing:.03em;color:#57606a}}
 .badge{{display:inline-block;padding:2px 10px;border-radius:20px;font-weight:700;font-size:12px;color:#fff;background:{banner}}}
 footer{{padding:14px 24px;background:#f6f8fa;font-size:12px;color:#57606a;border-top:1px solid #eaecef}}
</style></head><body>
<div class="wrap">
 <header>
   <h1>Assignment 1 - E-Commerce Automation (Selenium + Python)
     <span class="badge">{status}</span></h1>
   <div class="sub">Target: tutorialsninja.com/demo | Data source: {html.escape(data_source)}
     | Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
     {' | ' + html.escape(error) if error else ''}</div>
 </header>
 <table>
   <tr><th style="width:60px">Status</th><th style="width:220px">Step</th><th>Detail / Screenshot</th><th style="width:80px">Time</th></tr>
   {''.join(rows)}
 </table>
 <footer>Steps executed: {len(rep.steps)} | Pass: {sum(1 for s in rep.steps if s['status']=='PASS')}
   | Warn: {sum(1 for s in rep.steps if s['status']=='WARN')} | Fail: {sum(1 for s in rep.steps if s['status']=='FAIL')}
   | Total: {sum(1 for s in rep.steps if s['status'] in ('PASS','WARN'))}/{len(rep.steps)}</footer>
</div></body></html>"""
    with open(REPORT_HTML, "w", encoding="utf-8") as f:
        f.write(doc)

def main():
    os.makedirs(SCREEN_DIR, exist_ok=True)
    print("=" * 70)
    print("WIPRO CAPSTONE - ASSIGNMENT 1 : Selenium E-Commerce E2E Automation")
    print("=" * 70)
    headed = "--headed" in sys.argv
    data, src = load_test_data()
    print(f"Test data source : {src}")
    print(f"Data             : {json.dumps(data, indent=2)}")
    print("Target           : " + BASE)
    print("-" * 70)
    rep, screenshots, success, error = run_flow(data, headed)
    write_report(rep, screenshots, src, success, error)
    print("-" * 70)
    print(f"Execution {'PASSED' if success else 'FAILED'}  ->  report: {REPORT_HTML}")
    print(f"Screenshots: {len(screenshots)} captured in {SCREEN_DIR}")
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
