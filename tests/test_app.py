"""Exercise the HTTP contract and privacy properties with Flask's test client."""

import contextlib
import io
import unittest
from unittest.mock import patch

from app import MAX_CHARACTERS, create_app
from regex.masker import RULES, RULE_MAP
from team import FIELDS, TEAM


class AppTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "GITHUB_URL": ""})
        self.client = self.app.test_client()

    def test_mask_api_contract(self):
        response = self.client.post("/api/mask", json={"text": "Customer email is card@gmail.com"})
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertTrue(result["success"])
        self.assertEqual(result["masked_text"], "Customer email is c**d@gmail.com")
        self.assertEqual(result["counts"], {"credit_card": 0, "email": 1, "phone": 0, "dob": 0, "address": 0})
        self.assertEqual(result["total_detected"], 1)
        self.assertEqual(result["masked_characters"], 2)
        self.assertNotIn("card@gmail.com", response.get_data(as_text=True))

    def test_api_toggle_defaults_and_all_disabled(self):
        text = "card@gmail.com 093-245-7894"
        response = self.client.post("/api/mask", json={"text": text, "rules": {"email": False}}).get_json()
        self.assertEqual(response["masked_text"], "card@gmail.com XXX-XXX-7894")
        response = self.client.post("/api/mask", json={"text": text, "rules": dict.fromkeys(RULE_MAP, False)}).get_json()
        self.assertEqual(response["masked_text"], text)
        self.assertEqual(response["total_detected"], 0)

    def test_bad_payloads(self):
        for payload in (None, [], "text", {}, {"text": None}, {"text": 123}, {"text": ""},
                        {"text": " \t\r\n"}, {"text": "hello", "rules": None},
                        {"text": "hello", "rules": []}, {"text": "hello", "rules": {"unknown": True}},
                        {"text": "hello", "rules": {"email": 1}}, {"text": "hello", "rules": {"email": "false"}}):
            with self.subTest(payload=payload):
                import json
                response = self.client.post("/api/mask", data=json.dumps(payload), content_type="application/json")
                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.get_json()["success"])

    def test_malformed_json(self):
        response = self.client.post("/api/mask", data='{"text":', content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "The request contains invalid JSON.")

    def test_non_json(self):
        response = self.client.post("/api/mask", data="card@gmail.com")
        self.assertEqual(response.status_code, 415)

    def test_character_and_request_limits(self):
        self.assertEqual(self.client.post("/api/mask", json={"text": "a" * MAX_CHARACTERS}).status_code, 200)
        self.assertEqual(self.client.post("/api/mask", json={"text": "a" * (MAX_CHARACTERS + 1)}).status_code, 413)
        response = self.client.post("/api/mask", data=b"x" * 1_048_577, content_type="application/json")
        self.assertEqual(response.status_code, 413)
        self.assertFalse(response.get_json()["success"])

    def test_unicode_round_trip(self):
        text = "🧪 ทดสอบ\r\nAddress: 12/3 หมู่ 4"
        response = self.client.post("/api/mask", json={"text": text}).get_json()
        self.assertEqual(response["masked_text"], "🧪 ทดสอบ\r\nAddress: XX/X หมู่ 4")
        self.assertEqual(response["detections"][0]["start"], text.index("Address:"))

    def test_invalid_unicode_is_rejected_without_server_error(self):
        response = self.client.post("/api/mask", data=r'{"text": "\ud800"}', content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Use valid UTF-8 text.")

    def test_routes_render(self):
        for path in ("/", "/regex-playground", "/examples", "/about-us"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn('lang="en"', response.get_data(as_text=True))
        self.assertEqual(self.client.get("/about").status_code, 404)

    def test_about_us_shows_a_card_per_member(self):
        page = self.client.get("/about-us").get_data(as_text=True)
        self.assertEqual(len(TEAM), 10)
        self.assertEqual(page.count('class="panel member-card"'), len(TEAM))
        for _, label in FIELDS:
            self.assertEqual(page.count(f"<dt>{label}</dt>"), len(TEAM))
        # A blank line stands in for every field nobody has filled in yet.
        blank = sum(not member[key] for member in TEAM for key, _ in FIELDS)
        self.assertEqual(page.count('class="member-blank"'), blank)

    def test_about_us_prints_the_details_it_is_given(self):
        roster = [{"nickname": "Cat", "student_id": "67011031", "full_name": "Somchai Jaidee"}]
        with patch("app.TEAM", roster):
            page = self.client.get("/about-us").get_data(as_text=True)
        self.assertEqual(page.count('class="panel member-card"'), 1)
        self.assertNotIn("member-blank", page)
        for value in ("Cat", "67011031", "Somchai Jaidee"):
            self.assertIn(value, page)
        self.assertIn('class="member-avatar">C<', page)

    def test_rule_catalog_has_real_patterns(self):
        self.assertEqual(self.client.get("/api/rules").get_json()["rules"], [rule.public() for rule in RULES])

    def test_privacy_headers_and_no_cookie(self):
        response = self.client.post("/api/mask", json={"text": "card@gmail.com"})
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertNotIn("Set-Cookie", response.headers)
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)
        self.assertIn("script-src 'self'", response.headers["Content-Security-Policy"])

    def test_no_input_logging_or_file_writes(self):
        output = io.StringIO()
        with patch("builtins.open", side_effect=AssertionError("file operation")), \
             patch.object(self.app.logger, "info") as info, \
             patch.object(self.app.logger, "error") as error, \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            response = self.client.post("/api/mask", json={"text": "card@gmail.com"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(output.getvalue(), "")
        info.assert_not_called()
        error.assert_not_called()

    def test_github_config_and_missing_link(self):
        self.assertNotIn("Source code", self.client.get("/").get_data(as_text=True))
        self.app.config["GITHUB_URL"] = "https://github.com/example/assignment"
        self.assertIn('href="https://github.com/example/assignment"', self.client.get("/").get_data(as_text=True))
        for invalid in ("javascript:alert(1)", "https://example.com", "https://github.com@evil.example/path"):
            self.app.config["GITHUB_URL"] = invalid
            self.assertNotIn("Source code", self.client.get("/").get_data(as_text=True))

    def test_machines_reach_the_playground_only(self):
        playground = self.client.get("/regex-playground").get_data(as_text=True)
        for rule in RULES:
            self.assertIn(f'"{rule.key}": {{', playground)
        self.assertIn("data-machines=\'{}\'", self.client.get("/").get_data(as_text=True))
        self.assertNotIn("machine", self.client.get("/api/rules").get_data(as_text=True))

    def test_every_machine_replays_its_own_sample(self):
        """The drawn walk has to agree with what the real engine matches."""
        for rule in RULES:
            with self.subTest(rule=rule.key):
                machine = rule.machine()
                match = rule.pattern.search(rule.sample)
                self.assertEqual(machine["offset"], match.start())
                self.assertEqual("".join(move["text"] for move in machine["trace"]), match.group())
                self.assertEqual(machine["trace"][-1]["to"], len(machine["states"]) - 1)
                self.assertEqual(machine["states"][0]["kind"], "start")
                self.assertEqual(machine["states"][-1]["kind"], "accept")
                reached = {0} | {edge["to"] for edge in machine["edges"]}
                self.assertEqual(reached, set(range(len(machine["states"]))))


if __name__ == "__main__":
    unittest.main()
