"""Exercise the installed package in Chromium during release builds."""
from playwright.sync_api import sync_playwright, expect
from unique_interface import Interface, TabbedInterface, Dropdown, Dataframe


def main():
    table = Interface(lambda rows: rows, Dataframe(["City"]), Dataframe(["Result"]),
                      examples=[[[["Salem"]]]])
    choice = Interface(str.upper, Dropdown(["small", "large"]), "text")
    app = TabbedInterface([table, choice], ["Table", "Choice"]).launch(block=False, open_browser=False)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            page.goto(app.local_url)
            page.get_by_role("button", name="Example:").click()
            cell = page.get_by_role("textbox", name="City")
            expect(cell).to_have_value("Salem")
            cell.fill("Bengaluru")
            page.get_by_role("button", name="Run", exact=True).click()
            expect(page.get_by_role("cell", name="Bengaluru")).to_be_visible()
            page.get_by_role("button", name="Choice", exact=True).click()
            page.get_by_role("combobox").select_option("large")
            page.get_by_role("button", name="Run", exact=True).click()
            expect(page.locator("article:visible pre").filter(has_text="LARGE")).to_be_visible()
            page.get_by_role("link", name="Use via API").click()
            page.get_by_role("combobox").select_option("tab1_predict")
            page.get_by_role("textbox").fill('["small"]')
            page.get_by_role("button", name="Send request").click()
            expect(page.get_by_role("status")).to_contain_text("SMALL")
            browser.close()
    finally:
        app.close()


if __name__ == "__main__":
    main()
