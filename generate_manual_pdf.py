"""Generate the user manual PDF from the /manual page (with screenshots).

Requires the app running at BASE and playwright + Chrome installed.
Usage: python generate_manual_pdf.py
Output: static/manual/Manual_Alma_do_Livro.pdf (served by /manual/download)
"""
import os
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
OUT = os.path.join(os.path.dirname(__file__), "static", "manual", "Manual_Alma_do_Livro.pdf")

os.makedirs(os.path.dirname(OUT), exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="chrome")
    page = browser.new_context(viewport={"width": 1440, "height": 900}, locale="pt-PT").new_page()
    page.goto(BASE + "/manual")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)  # let all images finish rendering
    page.emulate_media(media="print")
    page.pdf(
        path=OUT,
        format="A4",
        print_background=True,
        margin={"top": "12mm", "bottom": "12mm", "left": "10mm", "right": "10mm"},
    )
    browser.close()

print(f"PDF generated: {OUT} ({os.path.getsize(OUT) // 1024} KB)")
