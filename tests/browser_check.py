"""Real-browser integration checks. Run from the project root; uses fake data only."""

import os
from pathlib import Path
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import WSGIRequestHandler, make_server

from app import create_app
from regex.masker import mask_text
from samples import SAMPLES


class QuietHandler(WSGIRequestHandler):
    def log(self, _type, _message, *args):
        pass


class BrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts = Path("test-results")
        cls.artifacts.mkdir(exist_ok=True)
        cls.server = make_server("127.0.0.1", 0, create_app({"GITHUB_URL": ""}), threaded=True,
                                 request_handler=QuietHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.playwright = sync_playwright().start()
        channel = os.environ.get("PLAYWRIGHT_CHANNEL", "chrome")
        cls.browser = cls.playwright.chromium.launch(channel=channel or None, headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=5)

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 1100},
                                                permissions=["clipboard-read", "clipboard-write"])
        self.page = self.context.new_page()
        self.errors = []
        self.external_requests = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.on("console", lambda message: self.errors.append(message.text)
                     if "Content Security Policy" in message.text else None)
        self.page.on("request", lambda request: self.external_requests.append(request.url)
                     if not request.url.startswith(self.url) and not request.url.startswith("blob:") else None)

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])
        self.assertEqual(self.external_requests, [])

    def scan(self):
        self.page.locator("#scan").click()
        expect(self.page.locator("#output-log")).to_be_visible()
        expect(self.page.locator("#scan")).to_be_enabled()

    def test_desktop_scan_compare_inspector_copy_download(self):
        page = self.page
        page.goto(self.url)
        page.screenshot(path=str(self.artifacts / "desktop-ready.png"), full_page=True)
        self.scan()
        expected = mask_text(SAMPLES[0]["text"])["masked_text"]
        self.assertEqual(page.locator("#output-log").inner_text(), expected)
        expect(page.locator("#stat-detected")).to_have_text("05")
        expect(page.locator("#stat-masked")).to_have_text("39")
        expect(page.locator("#stat-risk")).to_have_text("Medium")
        expect(page.locator(".detection-row")).to_have_count(5)
        page.locator("#detected-view").click()
        expect(page.locator("#source-preview mark")).to_have_count(5)
        page.locator("#compare-view").click()
        expect(page.locator("#source-preview .changed-source")).to_have_count(10)
        expect(page.locator("#output-log .changed-output")).to_have_count(10)
        self.assertEqual(page.locator("#source-preview").inner_text(), SAMPLES[0]["text"])
        page.screenshot(path=str(self.artifacts / "desktop-scanned.png"), full_page=True)
        page.locator(".detection-row").first.click()
        expect(page.locator("#detection-dialog")).to_be_visible()
        expect(page.locator("#dialog-preview")).to_have_text("s************e@example.com")
        page.locator("#reveal-match").click()
        expect(page.locator("#dialog-preview")).to_have_text("somchai.jaidee@example.com")
        page.keyboard.press("Escape")
        expect(page.locator("#dialog-preview")).to_have_text("")
        page.locator("#copy").click()
        expect(page.locator("#toast")).to_have_text("Masked text copied to clipboard.")
        # Windows clipboard APIs normalize line endings to CRLF.
        clipboard = page.evaluate("navigator.clipboard.readText()")
        self.assertEqual(clipboard.replace("\r\n", "\n"), expected)
        with page.expect_download() as event:
            page.locator("#download").click()
        download = event.value
        self.assertEqual(download.suggested_filename, "masked_log.txt")
        self.assertEqual(Path(download.path()).read_text(encoding="utf-8"), expected)
        self.assertEqual(page.evaluate("localStorage.length + sessionStorage.length"), 0)
        self.assertEqual(self.context.cookies(), [])

    def test_toggles_and_stale_results(self):
        page = self.page
        page.goto(self.url)
        self.scan()
        page.locator("label.rule-email").click()
        expect(page.locator("#copy")).to_be_disabled()
        expect(page.locator("#output-log")).to_be_hidden()
        self.scan()
        expect(page.locator("#stat-detected")).to_have_text("04")
        self.assertIn("somchai.jaidee@example.com", page.locator("#output-log").inner_text())
        page.locator("#toggle-all").click()  # enable all
        page.locator("#toggle-all").click()  # disable all
        self.scan()
        expect(page.locator("#stat-detected")).to_have_text("00")
        expect(page.locator("#scan-status")).to_contain_text("All rules are disabled")
        self.assertEqual(page.locator("#output-log").inner_text(), SAMPLES[0]["text"])
        page.locator("#clear").click()
        expect(page.locator("#input-log")).to_have_value("")
        expect(page.locator("#download")).to_be_disabled()
        expect(page.locator("#inspector-empty strong")).to_have_text("No detections yet")

    def test_unicode_highlights_and_html_is_inert(self):
        page = self.page
        page.goto(self.url)
        text = '🧪 ภาษาไทย\nAddress: 99/12 หมู่ 4\nEmail: card@gmail.com\n<img src=x onerror="window.injected=true">'
        page.locator("#input-log").fill(text)
        self.scan()
        page.locator("#detected-view").click()
        self.assertEqual(page.locator("#source-preview mark").all_text_contents(), ["Address: 99/12", "card@gmail.com"])
        self.assertEqual(page.locator("#output-log mark").all_text_contents(), ["Address: XX/XX", "c**d@gmail.com"])
        self.assertEqual(page.locator("#output-log img").count(), 0)
        self.assertIsNone(page.evaluate("window.injected"))
        page.locator("#source-preview mark").last.focus()
        page.keyboard.press("Enter")
        expect(page.locator("#detection-dialog")).to_be_visible()

    def test_input_errors_network_failure_and_recovery(self):
        page = self.page
        page.goto(self.url)
        page.locator("#clear").click()
        page.locator("#scan").click()
        expect(page.locator("#scan-error")).to_have_text("Enter some text to scan.")
        page.locator("#load-sample").click()
        page.route("**/api/mask", lambda route: route.abort())
        page.locator("#scan").click()
        expect(page.locator("#scan-error")).to_contain_text("Unable to reach")
        expect(page.locator("#copy")).to_be_disabled()
        page.unroute("**/api/mask")
        self.scan()
        page.locator("#input-log").fill("x" * 50_001)
        page.locator("#scan").click()
        expect(page.locator("#scan-error")).to_contain_text("50,000")

    def test_inflight_response_cannot_restore_stale_results(self):
        page = self.page
        page.goto(self.url)
        page.evaluate("""() => {
          const realFetch = window.fetch;
          window.fetch = (...args) => realFetch(...args).then(response =>
            new Promise(resolve => { window.releaseScan = () => resolve(response); }));
        }""")
        page.locator("#scan").click()
        page.wait_for_function("typeof window.releaseScan === 'function'")
        expect(page.locator("#scan-label")).to_have_text("Scanning…")
        page.locator("#input-log").fill("A new log")
        page.evaluate("window.releaseScan()")
        expect(page.locator("#copy")).to_be_disabled()
        expect(page.locator("#output-log")).to_be_hidden()
        expect(page.locator("#input-log")).to_have_value("A new log")

    def test_playground_uses_each_real_rule(self):
        page = self.page
        page.goto(self.url + "/regex-playground")
        rules = page.request.get(self.url + "/api/rules").json()["rules"]
        for rule in rules:
            page.locator(f'.pattern-choice[data-rule="{rule["key"]}"]').click()
            expect(page.locator("#pattern-code")).to_have_text(rule["pattern"])
            self.scan()
            expect(page.locator(".detection-row")).to_have_count(1)
            self.assertEqual(page.locator("#output-log").inner_text(), mask_text(rule["sample"], [rule["key"]])["masked_text"])
        page.screenshot(path=str(self.artifacts / "playground.png"), full_page=True)

    def test_examples_feed_the_masker(self):
        page = self.page
        page.goto(self.url + "/examples")
        expect(page.locator(".example-card")).to_have_count(3)
        page.get_by_role("link", name="Open in Data Masker").nth(1).click()
        expect(page.locator("#input-log")).to_have_value(SAMPLES[1]["text"])
        self.scan()
        expect(page.locator("#stat-detected")).to_have_text("07")
        page.get_by_role("link", name="Regex Playground", exact=True).click()
        expect(page.locator("h1")).to_contain_text("Drawn as machines")

    def test_upload_paste_and_drop_fill_the_workspace(self):
        page = self.page
        page.goto(self.url)
        log = "Email: taksin.k@mail.co.th\nPhone: 081-222-3344"
        with page.expect_file_chooser() as event:
            page.locator("#upload").click()
        event.value.set_files({"name": "audit.log", "mimeType": "text/plain",
                               "buffer": log.encode("utf-8")})
        expect(page.locator("#input-log")).to_have_value(log)
        expect(page.locator("#scan-status")).to_contain_text("Loaded audit.log")
        self.scan()
        expect(page.locator("#stat-detected")).to_have_text("02")
        page.evaluate("navigator.clipboard.writeText('Card: 4444-5555-6666-7777')")
        page.locator("#paste").click()
        expect(page.locator("#input-log")).to_have_value("Card: 4444-5555-6666-7777")
        page.evaluate("""() => {
          const transfer = new DataTransfer();
          transfer.items.add(new File(['DOB: 03/04/2545'], 'drop.txt', { type: 'text/plain' }));
          const zone = document.getElementById('drop-zone');
          zone.dispatchEvent(new DragEvent('dragover', { dataTransfer: transfer, bubbles: true }));
          zone.dispatchEvent(new DragEvent('drop', { dataTransfer: transfer, bubbles: true }));
        }""")
        expect(page.locator("#input-log")).to_have_value("DOB: 03/04/2545")
        expect(page.locator(".drop-hint")).to_be_hidden()

    def test_machine_diagram_walks_every_sample(self):
        page = self.page
        page.goto(self.url + "/regex-playground")
        for rule in page.request.get(self.url + "/api/rules").json()["rules"]:
            page.locator(f'.pattern-choice[data-rule="{rule["key"]}"]').click()
            expect(page.locator(".state-accept")).to_have_count(1)
            expect(page.locator(".state.current .state-label")).to_have_text("q0")
            steps = page.locator(".tape-cell").count()
            for _ in range(steps + len(rule["pattern"])):
                if page.locator("#machine-step").is_disabled():
                    break
                page.locator("#machine-step").click()
            expect(page.locator("#machine-caption")).to_contain_text("accepted")
            expect(page.locator(".tape-cell:not(.read)")).to_have_count(0)
            self.assertEqual(page.locator(".state.current .state-label").text_content(),
                             page.locator(".state-accept .state-label").text_content())
            page.locator("#machine-reset").click()
            expect(page.locator(".tape-cell.read")).to_have_count(0)
        page.screenshot(path=str(self.artifacts / "machine.png"), full_page=True)

    def test_short_emails_and_demo_risk_levels(self):
        page = self.page
        page.goto(self.url)
        for count, label in ((0, "Safe"), (1, "Low"), (3, "Medium"), (6, "High"), (11, "Critical")):
            page.locator("#input-log").fill("a@example.com " * count if count else "Hello")
            self.scan()
            expect(page.locator("#stat-risk")).to_have_text(label)
            expect(page.locator("#stat-masked")).to_have_text("00")
        expect(page.locator("#scan-status")).to_contain_text("11 short email usernames stay visible")

    def test_machine_uses_custom_input_and_stops_when_edited(self):
        page = self.page
        page.goto(self.url + "/regex-playground")
        page.locator('.pattern-choice[data-rule="email"]').click()
        text = "🧪 Mail: jane@example.co.th."
        page.locator("#input-log").fill(text)
        expect(page.locator(".tape-cell")).to_have_count(0)
        page.locator("#machine-step").click()
        expect(page.locator(".tape-cell.read")).to_have_count(1)
        self.assertEqual("".join(page.locator(".tape-cell").all_text_contents()), "jane@example.co.th")
        for _ in range(30):
            if page.locator("#machine-step").is_disabled():
                break
            page.locator("#machine-step").click()
        expect(page.locator("#machine-caption")).to_contain_text("accepted")
        expect(page.locator(".state-accept.current")).to_have_count(1)
        page.locator("#machine-reset").click()
        expect(page.locator(".tape-cell.read")).to_have_count(0)
        page.locator("#machine-play").click()
        expect(page.locator("#machine-play-label")).to_have_text("Pause")
        page.locator("#input-log").fill("user@example.com123")
        expect(page.locator("#machine-play-label")).to_have_text("Run input")
        expect(page.locator(".edge.active")).to_have_count(0)
        page.locator("#machine-play").click()
        expect(page.locator("#machine-play-label")).to_have_text("Pause")
        expect(page.locator("#machine-step")).to_be_enabled()
        page.locator('.pattern-choice[data-rule="phone"]').click()
        expect(page.locator("#input-log")).to_have_value("user@example.com123")
        page.locator("#clear").click()
        expect(page.locator("#machine-tape")).to_be_empty()
        expect(page.locator("#machine-play")).to_be_enabled()
        page.locator("#load-sample").click()
        expect(page.locator("#machine-play")).to_be_enabled()

    def test_machine_uses_uploaded_and_pasted_text(self):
        page = self.page
        page.goto(self.url + "/regex-playground")
        page.locator('.pattern-choice[data-rule="phone"]').click()
        page.locator("#file-input").set_input_files({"name": "phone.txt", "mimeType": "text/plain",
                                                     "buffer": b"Call: 111-222-3333"})
        self.scan()
        self.assertEqual("".join(page.locator(".tape-cell").all_text_contents()), "111-222-3333")
        page.evaluate("navigator.clipboard.writeText('Call: 555-666-7777')")
        page.locator("#paste").click()
        page.locator("#machine-step").click()
        expect(page.locator(".tape-cell.read")).to_have_count(1)
        self.assertEqual("".join(page.locator(".tape-cell").all_text_contents()), "555-666-7777")

    def test_machine_replays_rejection_and_can_reset_or_edit(self):
        page = self.page
        page.goto(self.url + "/regex-playground")
        page.locator('.pattern-choice[data-rule="phone"]').click()
        page.locator("#input-log").fill("111-22x-3333")
        page.locator("#machine-step").click()
        expect(page.locator(".tape-cell.read")).to_have_count(1)
        expect(page.locator("#machine-result")).to_be_hidden()
        for _ in range(5):
            page.locator("#machine-step").click()
        expect(page.locator(".tape-cell.read")).to_have_count(6)
        expect(page.locator("#machine-result")).to_be_hidden()
        page.locator("#machine-step").click()
        expect(page.locator("#machine-result")).to_have_text("Rejected")
        expect(page.locator("#machine-caption")).to_contain_text("character 7")
        expect(page.locator("#machine-caption")).to_contain_text("Expected [0-9]")
        expect(page.locator(".tape-cell.rejected")).to_have_text("x")
        expect(page.locator(".state.rejected .state-label")).to_have_text("q6")
        expect(page.locator("#machine-step")).to_be_disabled()
        expect(page.locator("#machine-play")).to_be_enabled()
        expect(page.locator("#output-log")).to_have_text("111-22x-3333")
        page.locator(".machine-panel").screenshot(path=str(self.artifacts / "machine-rejected.png"))
        page.locator("#machine-reset").click()
        expect(page.locator("#machine-result")).to_be_hidden()
        expect(page.locator(".tape-cell.read, .tape-cell.rejected, .state.rejected")).to_have_count(0)
        page.locator("#machine-play").click()
        expect(page.locator("#machine-result")).to_have_text("Rejected", timeout=8000)
        expect(page.locator("#machine-play-label")).to_have_text("Run input")
        page.locator("#input-log").fill("111-222-3333")
        expect(page.locator("#machine-result")).to_be_hidden()
        expect(page.locator(".state.rejected")).to_have_count(0)
        for _ in range(12):
            page.locator("#machine-step").click()
        expect(page.locator("#machine-result")).to_have_text("Accepted")

    def test_machine_rejects_empty_input_incomplete_input_and_boundaries(self):
        page = self.page
        page.goto(self.url + "/regex-playground")
        cases = (
            ("phone", "", "end of input", "EOF"),
            ("phone", " ", "a space", "␣"),
            ("phone", "🧪", "character 1", "🧪"),
            ("phone", "111-222-333", "Expected [0-9]", "EOF"),
            ("credit_card", "1234-5678-9012-34567", "Boundary check failed", "7"),
            ("email", "a@b.c.d", "Expected [A-Za-z]", "EOF"),
            ("dob", "DOB:\n01/01/2000", "a line break", "↵"),
            ("address", "Address: 12/3/4", "Boundary check failed", "/"),
        )
        for key, text, message, blocked in cases:
            with self.subTest(rule=key, text=text):
                page.locator(f'.pattern-choice[data-rule="{key}"]').click()
                page.locator("#input-log").fill(text)
                self.scan()
                expect(page.locator("#machine-step")).to_be_enabled()
                for _ in range(len(text) + 20):
                    if page.locator("#machine-step").is_disabled():
                        break
                    page.locator("#machine-step").click()
                expect(page.locator("#machine-result")).to_have_text("Rejected")
                expect(page.locator("#machine-caption")).to_contain_text(message)
                expect(page.locator(".tape-cell.rejected")).to_have_text(blocked)

    def test_machine_ignores_stale_response_and_recovers_from_failure(self):
        page = self.page
        page.goto(self.url + "/regex-playground")
        page.locator("#input-log").fill("4444-5555-6666-7777")
        page.evaluate("""() => {
          const realFetch = window.fetch;
          window.fetch = (...args) => realFetch(...args).then(response =>
            new Promise(resolve => { window.releaseScan = () => resolve(response); }));
        }""")
        page.locator("#machine-play").click()
        page.wait_for_function("typeof window.releaseScan === 'function'")
        page.locator("#input-log").fill("Changed input")
        page.evaluate("window.releaseScan()")
        expect(page.locator("#machine-tape")).to_have_text("Changed input")
        expect(page.locator("#machine-play-label")).to_have_text("Run input")
        expect(page.locator(".tape-cell")).to_have_count(0)
        expect(page.locator("#copy")).to_be_disabled()
        page.reload()
        page.locator("#input-log").fill("4444-5555-6666-7777")
        page.route("**/api/mask", lambda route: route.abort())
        page.locator("#machine-play").click()
        expect(page.locator("#machine-caption")).to_contain_text("Unable to test")
        expect(page.locator("#machine-play")).to_be_enabled()
        page.unroute("**/api/mask")
        page.locator("#machine-step").click()
        expect(page.locator(".tape-cell.read")).to_have_count(1)

    def test_mobile_layout_navigation_and_workflow(self):
        page = self.page
        for width in (390, 320):
            page.set_viewport_size({"width": width, "height": 844})
            page.goto(self.url)
            self.scan()
            self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
            input_box = page.locator(".input-editor").bounding_box()
            output_box = page.locator(".output-editor").bounding_box()
            self.assertGreater(output_box["y"], input_box["y"])
            page.locator("#compare-view").click()
            expect(page.locator("#source-preview")).to_be_visible()
            page.screenshot(path=str(self.artifacts / f"mobile-{width}.png"), full_page=True)
            for path in ("/regex-playground", "/examples", "/about-us"):
                page.goto(self.url + path)
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width, path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
