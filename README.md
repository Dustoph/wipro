# Wipro Capstone — Python Automation

E2E automation deliverables for the Wipro capstone program. Each assignment is
a **single self-contained script** that writes out any supporting framework
artifacts and then executes the full flow, generating an execution report.

| # | Assignment | Folder | Entry point | Stack |
|---|-----------|--------|-------------|-------|
| 1 | E-Commerce E2E Automation | `Assignment_1_Selenium_E2E` | `python assignment1.py` | Selenium WebDriver (Chrome) |
| 2 | Framework: Unittest + PyTest + POM | `Assignment_2_Selenium_PyTest_POM` | `python assignment2.py` | Selenium + PyTest + Unittest + Page Object Model |
| 3 | API Automation (BDD) | `Assignment_3_API_Behave_BDD` | `python assignment3.py` | Requests + Behave + Allure |
| 4 | Robot Framework Web Automation | `Assignment_4_RobotFramework` | `python assignment4.py` | Robot Framework + SeleniumLibrary |

The capstone project (the overall business flow: launch browser → login →
search → add to cart → verify cart → logout → close) is orchestrated through
the assignment scripts, all run against the public demo store
<https://tutorialsninja.com/demo/>.

## Prerequisites

- Python 3.10+ (tested on 3.14)
- Chrome browser (for assignments 1, 2 and 4)
- Dependencies: `pip install -r requirements.txt`

Selenium Manager downloads a matching `chromedriver` automatically — no
manual driver installation is required.

## Running

From the repo root, run each assignment's entry script. Every script exits
`0` on a successful run and writes an HTML report next to itself.

```bash
python Assignment_1_Selenium_E2E/assignment1.py
python Assignment_2_Selenium_PyTest_POM/assignment2.py
python Assignment_3_API_Behave_BDD/assignment3.py
python Assignment_4_RobotFramework/assignment4.py
```

Notes:

- Assignment 1 runs headless by default; pass `--headed` to watch the browser.
- Assignments 1/2 need network access to `tutorialsninja.com` and a
  Chromium-family browser. Assignment 3 needs network access to
  `jsonplaceholder.typicode.com` and `httpbin.org` (APIs only — no browser).
- Assignments 3 and 4 are deterministic against the public APIs; 1 and 2
  may log a WARN if the demo store's live search index has no results for
  the configured search term (the scripts fall back to a featured product).
