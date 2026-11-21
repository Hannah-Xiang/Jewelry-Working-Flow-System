
from playwright.sync_api import sync_playwright

REPORT_NUMBER = "LG687526402"

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False
    )

    page = browser.new_page()

    try:
        # Step 1: Open IGI verification page
        page.goto(
            "https://www.igi.org/Verify-Your-Report/",
            wait_until="domcontentloaded",
            timeout=60000
        )

        print("IGI page opened:", page.title())

        # Step 2: Find the report number input
        report_input = page.get_by_placeholder(
            "Enter Your Report No."
        )

        report_input.fill(REPORT_NUMBER)

        print("Report number entered:", REPORT_NUMBER)

        # Step 3: Click Verify
        verify_button = page.get_by_role(
            "button",
            name="Verify",
            exact=True
        )

        verify_button.click()

        print("Verify button clicked.")

        # Step 4: Wait for the result
        page.wait_for_load_state(
            "domcontentloaded",
            timeout=30000
        )

        page.wait_for_timeout(5000)

        # Step 5: Inspect the returned page
        print("\n========== IGI RESULT ==========")

        print("Current URL:", page.url)

        print("Page title:", page.title())

        print("\n========== FULL IGI REPORT ==========")

        report_text = page.locator("body").inner_text()

        print(report_text)

        print("\n========== HTML CHECK ==========")

        html = page.content()

        import re

        # Get visible report text
        report_text = page.locator("body").inner_text()

        lines = [
            line.strip()
            for line in report_text.splitlines()
            if line.strip()
        ]

        def get_value(label):
            """Get the text immediately following a report label."""

            for index, line in enumerate(lines):

                if line.lower() == label.lower():

                    if index + 1 < len(lines):
                        return lines[index + 1]

            return None


        # Extract measurements
        measurements = get_value("Measurements")

        measurement_values = []

        if measurements:
            measurement_values = re.findall(
                r"\d+(?:\.\d+)?",
                measurements
            )


        # Extract carat weight
        carat_text = get_value("Carat Weight")

        carat_weight = None

        if carat_text:
            match = re.search(
                r"\d+(?:\.\d+)?",
                carat_text
            )

            if match:
                carat_weight = match.group()


        # Extract report number
        report_match = re.search(
            r"Report number\s*/\s*([A-Z0-9-]+)",
            report_text,
            re.IGNORECASE
        )

        report_number = (
            report_match.group(1)
            if report_match else None
        )
        report_link = (
            f"https://www.igi.org/Verify-Your-Report/?r={report_number}"
        )

        # Build extracted data
        diamond_data = {

            "report_number": report_number,

            "description": get_value("Description"),

            "shape": get_value("Shape and Cutting Style"),

            "measurement_length": (
                measurement_values[0]
                if len(measurement_values) == 3 else None
            ),

            "measurement_width": (
                measurement_values[1]
                if len(measurement_values) == 3 else None
            ),

            "measurement_depth": (
                measurement_values[2]
                if len(measurement_values) == 3 else None
            ),

            "carat_weight": carat_weight,

            "color_grade": get_value("Color Grade"),

            "clarity_grade": get_value("Clarity Grade"),

            "cut_grade": get_value("Cut Grade"),

            "polish": get_value("Polish"),

            "symmetry": get_value("Symmetry"),

            "fluorescence": get_value("Fluorescence"),
            "company": "IGI",
            "link": report_link,

            #"comments": get_value("Comments"),

        }

        print("\n========== EXTRACTED DIAMOND DATA ==========")

        for key, value in diamond_data.items():
            print(f"{key}: {value}")

        print("============================================")


        print("HTML length:", len(html))
        print("Report number found:", REPORT_NUMBER in html)

        print("====================================")

        input("\nPress Enter to close browser...")

    except Exception as error:

        print("Error:", error)

        input("Press Enter to close browser...")

    finally:
        browser.close()
