"""Capture screenshots for the user manual.
Runs against the local dev server (http://127.0.0.1:5000).
Usage: python capture_manual_screenshots.py
"""
import os
import sys
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
OUT = os.path.join(os.path.dirname(__file__), "static", "img", "manual")
TEXTS = os.path.join(OUT, "texts")
BOOK_TITLE = "Cartas de Amor aos Mortos"
BOOK_AUTHOR = "Ava Dellaira"
CHARACTER = "Laurel"
DEMO_EMAIL = "demo@almadolivro.pt"
DEMO_PASS = "Demo12345!"

os.makedirs(TEXTS, exist_ok=True)


def shot(page, name, full=False):
    page.screenshot(path=os.path.join(OUT, f"{name}.png"), full_page=full)
    print(f"  [shot] {name}.png", flush=True)


def save_text(page, selector, name):
    try:
        el = page.locator(selector)
        if el.count():
            txt = el.first.inner_text()
            with open(os.path.join(TEXTS, f"{name}.txt"), "w", encoding="utf-8") as f:
                f.write(txt)
    except Exception as e:
        print(f"  [text-skip] {name}: {e}", flush=True)


def wait_loading_done(page, timeout=240000):
    page.wait_for_selector("#loadingState.hidden", state="attached", timeout=timeout)


def run_aspect(page, aspect, name):
    print(f"  [aspect] {aspect}", flush=True)
    page.evaluate(f"loadAspect('{aspect}')")
    page.wait_for_timeout(2000)
    wait_loading_done(page)
    page.wait_for_timeout(800)
    save_text(page, "#contentArea", f"aspect-{aspect}")
    page.locator("#contentArea").screenshot(path=os.path.join(OUT, f"{name}.png"))
    print(f"  [shot] {name}.png", flush=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="pt-PT",
        )
        ctx.add_init_script("localStorage.setItem('alma_onboarding_completed','true')")
        page = ctx.new_page()
        page.set_default_timeout(60000)

        # ---------- Public pages ----------
        print("[1] public pages", flush=True)
        for name, url in [("01-landing", "/"), ("02-register", "/register"), ("03-login", "/login")]:
            page.goto(BASE + url)
            page.wait_for_load_state("networkidle")
            shot(page, name)

        # ---------- Login ----------
        print("[2] login as demo", flush=True)
        page.goto(BASE + "/login")
        page.fill("input[name=email]", DEMO_EMAIL)
        page.fill("input[name=password]", DEMO_PASS)
        page.click("button[type=submit]")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        page.goto(BASE + "/setup-api-key")
        page.wait_for_load_state("networkidle")
        shot(page, "04-setup-api-key")

        # ---------- Explorer ----------
        print("[3] explorer form", flush=True)
        page.goto(BASE + "/explorer")
        page.wait_for_load_state("networkidle")
        shot(page, "05-explorer")

        print("[4] exploring book", flush=True)
        page.fill("#bookTitle", BOOK_TITLE)
        page.fill("#bookAuthor", BOOK_AUTHOR)
        page.click("#exploreBtn")
        page.wait_for_selector("#interactiveFeatures:not(.hidden)", timeout=240000)
        page.wait_for_timeout(1200)
        shot(page, "06-explorer-header")
        page.locator("#interactiveFeatures").screenshot(path=os.path.join(OUT, "07-interactive-features.png"))
        print("  [shot] 07-interactive-features.png", flush=True)
        page.locator("#aspectsGrid").screenshot(path=os.path.join(OUT, "08-aspects-grid.png"))
        print("  [shot] 08-aspects-grid.png", flush=True)

        # ---------- Aspects ----------
        for aspect, name in [
            ("summary", "09-aspect-summary"),
            ("characters", "10-aspect-characters"),
            ("themes", "11-aspect-themes"),
            ("quotes", "12-aspect-quotes"),
            ("playlist", "13-aspect-playlist"),
            ("trailer", "14-aspect-trailer"),
        ]:
            try:
                run_aspect(page, aspect, name)
            except Exception as e:
                print(f"  [aspect-fail] {aspect}: {e}", flush=True)

        # ---------- Favorite ----------
        try:
            page.click("#favoriteBtn")
            page.wait_for_timeout(1500)
        except Exception as e:
            print(f"  [fav-skip] {e}", flush=True)

        # ---------- Interview ----------
        print("[5] interview", flush=True)
        try:
            page.evaluate("openExplorerInterview()")
            page.fill("#interviewCharName", CHARACTER)
            page.click("#charSelectSection button")
            page.wait_for_timeout(500)
            page.fill("#interviewInput", "O que sentiste quando a tua irmã May morreu?")
            page.click("#interviewChatArea button[type=submit]")
            # wait for the answer bubble (greeting + user + response = >=3 bubbles)
            page.wait_for_function(
                "document.querySelectorAll('#interviewMessages > div').length >= 3",
                timeout=240000,
            )
            page.wait_for_timeout(1200)
            save_text(page, "#interviewMessages", "interview")
            page.locator("#interviewModal").screenshot(path=os.path.join(OUT, "15-interview.png"))
            print("  [shot] 15-interview.png", flush=True)
            page.evaluate("document.querySelector('#interviewModal').remove()")
        except Exception as e:
            print(f"  [interview-fail] {e}", flush=True)

        # ---------- Quiz ----------
        print("[6] quiz", flush=True)
        try:
            page.evaluate("openExplorerQuiz()")
            page.click("#quizSetup button")
            page.wait_for_selector("#quizPlay:not(.hidden)", timeout=240000)
            page.wait_for_timeout(600)
            page.locator("#quizModal").screenshot(path=os.path.join(OUT, "16-quiz.png"))
            print("  [shot] 16-quiz.png", flush=True)
            # answer first question to capture explanation
            page.locator("#qOptions button").first.click()
            page.wait_for_timeout(800)
            page.locator("#quizModal").screenshot(path=os.path.join(OUT, "17-quiz-answered.png"))
            print("  [shot] 17-quiz-answered.png", flush=True)
            page.evaluate("document.querySelector('#quizModal').remove()")
        except Exception as e:
            print(f"  [quiz-fail] {e}", flush=True)

        # ---------- Other pages ----------
        print("[7] other pages", flush=True)
        for name, url in [
            ("18-favorites", "/favorites"),
            ("19-history", "/history"),
            ("20-profile", "/profile"),
            ("21-recommendations", "/recommendations"),
        ]:
            try:
                page.goto(BASE + url)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(600)
                shot(page, name)
            except Exception as e:
                print(f"  [page-fail] {url}: {e}", flush=True)

        # ---------- Compare ----------
        print("[8] compare", flush=True)
        try:
            page.goto(BASE + "/compare")
            page.wait_for_load_state("networkidle")
            page.fill("#book1Title", BOOK_TITLE)
            page.fill("#book1Author", BOOK_AUTHOR)
            page.fill("#book2Title", "A Culpa é das Estrelas")
            page.fill("#book2Author", "John Green")
            shot(page, "22-compare-form")
            page.click("#compareBtn")
            page.wait_for_selector("#resultsArea:not(.hidden)", timeout=240000)
            page.wait_for_timeout(1000)
            save_text(page, "#resultsArea", "compare")
            shot(page, "23-compare-result", full=True)
        except Exception as e:
            print(f"  [compare-fail] {e}", flush=True)

        browser.close()
        print("DONE", flush=True)


if __name__ == "__main__":
    sys.exit(main())
