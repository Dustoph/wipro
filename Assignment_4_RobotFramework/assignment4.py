import os, sys, shutil, subprocess, json
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))

STORE_RESOURCE_PY = r'''import csv, json, os, time
from robot.libraries.BuiltIn import BuiltIn

BASE = "https://tutorialsninja.com/demo"
HERE = os.path.dirname(os.path.abspath(__file__))

def _sl():
    return BuiltIn().get_library_instance("SeleniumLibrary")

def _driver():
    return _sl().driver

def store_open():
    from selenium.webdriver.chrome.options import Options
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1400,900")
    _sl().open_browser(BASE, browser="Chrome", options=options)

def store_close():
    _sl().close_all_browsers()

def store_login(email, password):
    sl = _sl()
    sl.go_to(BASE + "/index.php?route=account/login")
    sl.input_text("id=input-email", email)
    sl.input_text("id=input-password", password)
    sl.click_element("css=input[type=submit]")
    sl.wait_until_location_contains("route=account/account", "25s")

def store_search(term):
    _sl().go_to(BASE + "/index.php?route=product/search&search=" + str(term))

def store_open_product(product_id):
    _sl().go_to(BASE + "/index.php?route=product/product&product_id=" + str(product_id))

def store_add_to_cart(quantity):
    sl = _sl()
    sl.input_text("id=input-quantity", str(quantity))
    sl.click_element("id=button-cart")
    time.sleep(2)

def store_verify_cart(product_id, quantity):
    from selenium.webdriver.common.by import By
    driver = _driver()
    driver.get(BASE + "/index.php?route=checkout/cart")
    driver.find_element(By.CSS_SELECTOR, "#cart .dropdown-toggle").click()
    time.sleep(1)
    for r in driver.find_elements(By.CSS_SELECTOR, ".dropdown-menu table tbody tr"):
        if ("product_id=%s" % product_id) in (r.get_attribute("outerHTML") or ""):
            text = " ".join(td.text for td in r.find_elements(By.TAG_NAME, "td"))
            assert "x%d" % int(quantity) in text, "quantity mismatch: %r" % text
            return text
    raise AssertionError("product %s not found in cart" % product_id)

def store_logout():
    _sl().go_to(BASE + "/index.php?route=account/logout")
    time.sleep(1.5)

def store_clear_cart():
    from selenium.webdriver.common.by import By
    driver = _driver()
    driver.get(BASE + "/index.php?route=checkout/cart")
    time.sleep(1)
    try:
        driver.find_element(By.CSS_SELECTOR, "#cart .dropdown-toggle").click()
        time.sleep(1)
    except Exception:
        pass
    for _ in range(10):
        rows = driver.find_elements(By.CSS_SELECTOR, ".dropdown-menu table tbody tr")
        target = None
        for r in rows:
            rm = r.find_elements(By.CSS_SELECTOR, "button.btn-danger")
            if rm:
                target = rm[0]
                break
        if target is None:
            break
        target.click()
        time.sleep(2)
        try:
            driver.find_element(By.CSS_SELECTOR, "#cart .dropdown-toggle").click()
            time.sleep(1)
        except Exception:
            pass

def store_read_products(csv_path=None):
    path = csv_path or os.path.join(HERE, "..", "testdata", "products.csv")
    rows = []
    with open(path, newline="") as f:
        for r in csv.reader(f):
            if not r or r[0].startswith("#"):
                continue
            if r[0].lower() == "product_id":
                continue
            rows.append([c.strip() for c in r])
    return rows
'''

ECOMMERCE_ROBOT = r'''*** Settings ***
Library    SeleniumLibrary
Library    ${CURDIR}/../resources/store_resource.py

Suite Setup    Suite Bootstrap
Suite Teardown    Suite Teardown

*** Keywords ***
Suite Bootstrap
    [Documentation]    Open the headless browser for the whole suite.
    Store Open
Suite Teardown
    [Documentation]    Close every browser when the suite finishes.
    Store Close

*** Test Cases ***
Login And Add To Cart
    [Setup]
    Store Login    admin@tutorialsninja.com    123456
    Store Clear Cart
    Store Open Product    40
    Store Add To Cart    2
    Store Verify Cart    40    2
    [Teardown]    Store Logout

Data Driven Product Flows
    [Setup]
    Store Login    admin@tutorialsninja.com    123456
    Store Clear Cart
    ${ROWS}    Store Read Products
    FOR    ${row}    IN    @{ROWS}
        ${pid}    Set Variable    ${row}[0]
        ${qty}    Set Variable    ${row}[1]
        Log    processing product ${pid} quantity ${qty}
        Store Open Product    ${pid}
        Store Add To Cart    ${qty}
    END
    [Teardown]    Store Logout

*** Comments ***
Command line:      robot --outputdir . tests/ecommerce.robot
Jenkins:           see Jenkinsfile (generated alongside this suite).
'''

PRODUCTS_CSV = """# product_id,quantity
40,2
43,1
"""

JENKINSFILE = """// Pipeline for the Robot Framework suite (Assignment 4).
// Job steps: install deps, run robot headless, archive reports.
pipeline {
    agent any
    stages (
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Setup') {
            steps {
                sh 'python -m pip install -r requirements.txt'
            }
        }
        stage('Run Robot Suite') {
            steps {
                sh 'python Assignment_4_RobotFramework/assignment4.py'
            }
            post {
                always {
                    junit(allowEmptyResults: true, testResults:
                        'Assignment_4_RobotFramework/output.xml')
                    archiveArtifacts(
                        artifacts:
                        'Assignment_4_RobotFramework/log.html, ' +
                        'Assignment_4_RobotFramework/report.html, ' +
                        'Assignment_4_RobotFramework/output.xml',
                        allowMissing: true)
                }
            }
        }
    )
}
"""

def write_artifacts():
    layout = {
        os.path.join(HERE, "resources", "store_resource.py"): STORE_RESOURCE_PY,
        os.path.join(HERE, "tests", "ecommerce.robot"): ECOMMERCE_ROBOT,
        os.path.join(HERE, "testdata", "products.csv"): PRODUCTS_CSV,
        os.path.join(HERE, "Jenkinsfile"): JENKINSFILE,
    }
    written = []
    for path, content in layout.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        written.append(os.path.relpath(path, HERE))
    return written

def find_robot():
    exe = shutil.which("robot")
    if exe:
        return [exe]
    return [sys.executable, "-m", "robot"]

def main():
    print("=" * 70)
    print("WIPRO CAPSTONE - ASSIGNMENT 4 : Robot Framework Web Automation")
    print("=" * 70)
    written = write_artifacts()
    print(f"framework artifacts written ({len(written)} files):")
    for w in written:
        print(f"   - {w}")
    print("-" * 70)

    robot = find_robot()
    suite = os.path.join(HERE, "tests", "ecommerce.robot")
    outdir = HERE
    if "--dryrun" in sys.argv:

        cmd = robot + ["--dryrun", "--outputdir", outdir, suite]
        print("\n>> dry-run (syntax/keyword validation, no browser)")
    else:
        cmd = robot + ["--outputdir", outdir, "--loglevel", "INFO", suite]
        print("\n>> running Robot suite (headless Chrome)")
    p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
    sys.stdout.write(p.stdout[-4000:] if len(p.stdout) > 4000 else p.stdout)
    if p.returncode != 0:
        sys.stderr.write(p.stderr[-2000:] if p.stderr else "")

    print("-" * 70)
    for name in ("log.html", "report.html", "output.xml"):
        path = os.path.join(HERE, name)
        print(f"   {name}: {'generated' if os.path.exists(path) else 'n/a'}")
    status = "PASS" if p.returncode == 0 else "FAIL"
    print(f"Robot suite {status} (exit {p.returncode})")
    sys.exit(0 if p.returncode == 0 else 1)

if __name__ == "__main__":
    main()
