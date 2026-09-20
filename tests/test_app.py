"""Exercise the HTTP contract and privacy properties with Flask's test client."""

import contextlib
import io
import unittest
from unittest.mock import patch

from app import MAX_CHARACTERS, create_app
from regex.masker import RULES, RULE_MAP


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
        self.assertEqual(response["masked_text"], "🧪 ทดสอบ\r\nAddress: XXX หมู่ 4")
        self.assertEqual(response["detections"][0]["start"], text.index("Address:"))

    def test_invalid_unicode_is_rejected_without_server_error(self):
        response = self.client.post("/api/mask", data=r'{"text": "\ud800"}', content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Use valid UTF-8 text.")

    def test_routes_render(self):
        for path in ("/", "/regex-playground", "/examples", "/about"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn('lang="en"', response.get_data(as_text=True))

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
        page = self.client.get("/about").get_data(as_text=True)
        self.assertIn("Repository link not configured", page)
        self.app.config["GITHUB_URL"] = "https://github.com/example/assignment"
        self.assertIn('href="https://github.com/example/assignment"', self.client.get("/").get_data(as_text=True))
        for invalid in ("javascript:alert(1)", "https://example.com", "https://github.com@evil.example/path"):
            self.app.config["GITHUB_URL"] = invalid
            self.assertIn("Repository link not configured", self.client.get("/about").get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
