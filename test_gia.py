
from playwright.sync_api import sync_playwright
from datetime import datetime
from urllib.parse import urlencode
import re

REPORT_NUMBER = "2231120907"

REPORT_URL = (
    "https://www.gia.edu/report-check?"
    + urlencode({
        "locale": "en_US",
        "reportno": REPORT_NUMBER
    })
)


def get_next_line(lines, label):
    """Get the line immediately after a standalone label."""

    for index, line in enumerate(lines):
        if line.strip().lower() == label.lower():
            if index + 1 < len(lines):
                return lines[index + 1].strip()

    return ""


def get_inline_value(report_text, label):
    """Extract a value appearing on the same line as its label."""

    pattern = (
        rf"^\s*{re.escape(label)}\s+(.+?)\s*$"
    )

    match = re.search(
        pattern,
        report_text,
        re.IGNORECASE | re.MULTILINE
    )

    return match.group(1).strip() if match else ""


def extract_gia_data(report_text):

    lines = [
        line.strip()
        for line in report_text.splitlines()
        if line.strip()
    ]

    # -----------------------------------------
    # Report Number
    # -----------------------------------------

    report_number = get_next_line(
        lines,
        "GIA REPORT NUMBER"
    )

    # -----------------------------------------
    # Date of Issue
    # -----------------------------------------

    date_text = get_next_line(
        lines,
        "DATE OF ISSUE"
    )

    diamond_date = ""

    if date_text:

        try:
            diamond_date = datetime.strptime(
                date_text.replace(".", ""),
                "%b %d, %Y"
            ).strftime("%Y-%m-%d")

        except ValueError:
            try:
                diamond_date = datetime.strptime(
                    date_text.replace(".", ""),
                    "%B %d, %Y"
                ).strftime("%Y-%m-%d")

            except ValueError:
                pass

    # -----------------------------------------
    # Grading Results
    # -----------------------------------------

    shape_full = get_inline_value(
        report_text,
        "Shape"
    )

    shape = (
        shape_full.split()[0].upper()
        if shape_full else ""
    )

    carat_text = get_inline_value(
        report_text,
        "Carat Weight"
    )

    carat_match = re.search(
        r"\d+(?:\.\d+)?",
        carat_text
    )

    carat_weight = (
        carat_match.group()
        if carat_match else ""
    )

    color = get_inline_value(
        report_text,
        "Color Grade"
    )

    clarity = get_inline_value(
        report_text,
        "Clarity Grade"
    )

    cut = get_inline_value(
        report_text,
        "Cut Grade"
    )

    polish = get_inline_value(
        report_text,
        "Polish"
    )

    symmetry = get_inline_value(
        report_text,
        "Symmetry"
    )

    fluorescence_match = re.search(
        r"FLUORESCENCE\s+Fluorescence\s+([^\n]+)",
        report_text,
        re.IGNORECASE
    )

    fluorescence = (
        fluorescence_match.group(1).strip()
        if fluorescence_match else ""
    )

    # -----------------------------------------
    # Measurements
    # -----------------------------------------

    measurements = get_inline_value(
        report_text,
        "Measurements"
    )

    measurement_values = re.findall(
        r"\d+(?:\.\d+)?",
        measurements
    )

    measurement_length = ""
    measurement_width = ""
    measurement_depth = ""

    if len(measurement_values) >= 3:

        measurement_length = measurement_values[0]
        measurement_width = measurement_values[1]
        measurement_depth = measurement_values[2]

    # -----------------------------------------
    # Diamond Type
    # -----------------------------------------

    diamond_type = ""

    if re.search(
        r"FOR\s+LABORATORY[- ]GROWN DIAMOND",
        report_text,
        re.IGNORECASE
    ):
        diamond_type = "lab_grown"

    elif re.search(
        r"FOR\s+NATURAL DIAMOND",
        report_text,
        re.IGNORECASE
    ):
        diamond_type = "natural"

    # -----------------------------------------
    # Report Link
    # -----------------------------------------

    report_link = (
        "https://www.gia.edu/report-check?"
        + urlencode({
            "locale": "en_US",
            "reportno": report_number
        })
    )

    return {

        "report_number": report_number,
        "report_link": report_link,
        "company": "GIA",

        "diamond_date": diamond_date,

        "shape": shape,
        "carat_weight": carat_weight,

        "color_grade": color,
        "clarity_grade": clarity,
        "cut_grade": cut,

        "polish": polish,
        "symmetry": symmetry,
        "fluorescence": fluorescence,

        "diamond_type": diamond_type,

        "measurement_length": measurement_length,
        "measurement_width": measurement_width,
        "measurement_depth": measurement_depth,
    }


# =============================================
# MAIN
# =============================================

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False,
        args=["--disable-http2"]
    )

    page = browser.new_page()

    try:

        print("Opening GIA report...")

        page.goto(
            REPORT_URL,
            wait_until="commit",
            timeout=60000
        )

        page.wait_for_timeout(8000)

        report_text = page.locator("body").inner_text()

        # Verify report number
        data = extract_gia_data(report_text)

        if data["report_number"] != REPORT_NUMBER:

            print("ERROR: GIA report number does not match.")
            print("Returned:", data["report_number"])

        else:

            print("\n========== EXTRACTED GIA DATA ==========")

            for key, value in data.items():
                print(f"{key}: {value}")

            print("========================================")

    except Exception as error:

        print("GIA ERROR:", repr(error))

    finally:

        browser.close()
