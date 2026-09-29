import csv, json, os, time
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
