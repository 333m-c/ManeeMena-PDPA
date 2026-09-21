"""Regression cases for the original exercises and unified span metadata."""

import contextlib
import importlib
import io
import unittest
from unittest.mock import patch

from regex.address import censor_house_number, mask_address
from regex.birthdayreg import mask_dob
from regex.creditcardreg import mask_credit_card
from regex.gmailreg import email_parse, mask_email
from regex.masker import RULES, RULE_MAP, mask_text
from regex.phonereg import mask_phone
from samples import SAMPLES


class IndividualRulesTest(unittest.TestCase):
    def test_cards_preserve_last_four(self):
        self.assertEqual(mask_credit_card("Card: 1234-5678-9012-3456\n0000-1111-2222-3333"),
                         "Card: XXXX-XXXX-XXXX-3456\nXXXX-XXXX-XXXX-3333")

    def test_cards_reject_partial_and_unformatted_numbers(self):
        for text in ("123-456", "1234567890123456", "91234-5678-9012-3456",
                     "1234-5678-9012-34567", "1234-5678-9012-3456-7890", "A1234-5678-9012-3456"):
            with self.subTest(text=text):
                self.assertEqual(mask_credit_card(text), text)

    def test_email_examples_and_supported_characters(self):
        examples = {
            "card@gmail.com": "c**d@gmail.com",
            "somchai.d@company.com": "s*******d@company.com",
            "somchai.jaidee@company.co.th": "s************e@company.co.th",
            "user_name123@test.com": "u**********3@test.com",
            "A.b_c%+9-z@company.co.th": "A********z@company.co.th",
            "a@gmail.com": "a@gmail.com",
            "ab@gmail.com": "ab@gmail.com",
        }
        for text, expected in examples.items():
            with self.subTest(text=text):
                self.assertEqual(mask_email(text), expected)
                self.assertEqual(email_parse(text), expected)

    def test_multiple_emails_in_context_and_punctuation(self):
        self.assertEqual(mask_email("Email: <card@gmail.com>, other: jane@example.org."),
                         "Email: <c**d@gmail.com>, other: j**e@example.org.")

    def test_email_does_not_match_suffix_of_invalid_or_masked_address(self):
        for text in ("c**d@gmail.com", "x@@card@gmail.com", "user@example.com123", "no at sign"):
            with self.subTest(text=text):
                self.assertEqual(mask_email(text), text)
        self.assertEqual(email_parse("bad input"), "Invalid email")

    def test_phones_in_log(self):
        self.assertEqual(mask_phone("093-245-7894 / 081-123-4567 / 123-456-7890"),
                         "XXX-XXX-7894 / XXX-XXX-4567 / XXX-XXX-7890")

    def test_phone_rejects_unformatted_and_longer_numbers(self):
        for text in ("0811234567", "1093-245-7894", "093-245-78940", "093-245-7894-1234"):
            with self.subTest(text=text):
                self.assertEqual(mask_phone(text), text)

    def test_dob_preserves_spacing_and_century(self):
        for text, expected in (("DOB:25/12/2549", "DOB:XX/XX/25XX"),
                               ("DOB: 25/12/2549", "DOB: XX/XX/25XX"),
                               ("DOB:01/01/2500", "DOB:XX/XX/25XX"),
                               ("DOB:\t 31/02/1990", "DOB:\t XX/XX/19XX")):
            with self.subTest(text=text):
                self.assertEqual(mask_dob(text), expected)

    def test_dob_requires_exact_label_and_same_line(self):
        for text in ("25/12/2549", "dob:25/12/2549", "XDOB:25/12/2549",
                     "DOB:\n25/12/2549", "DOB:25/12/25490", "DOB:25/12/2549/1"):
            with self.subTest(text=text):
                self.assertEqual(mask_dob(text), text)

    def test_address_masks_one_x_per_digit(self):
        """The masked house number keeps the length and the slash of the original."""
        tail = " ซอยลาดกระบัง 19 ถนนลาดกระบัง แขวงลาดกระบัง เขตลาดกระบัง กรุงเทพฯ"
        for number, masked in (("689", "XXX"), ("45", "XX"), ("99/12", "XX/XX"),
                               ("12/3", "XX/X"), ("1", "X"), ("100200", "XXXXXX")):
            for spacing in ("", " ", "\t  "):
                text = "Address:" + spacing + number + tail
                with self.subTest(number=number, spacing=spacing):
                    self.assertEqual(mask_address(text), "Address:" + spacing + masked + tail)
        self.assertEqual(mask_address("Address: 12/3 หมู่ 4 ถนน..."), "Address: XX/X หมู่ 4 ถนน...")

    def test_address_inside_multiline_log(self):
        self.assertEqual(mask_address("Start\nAddress: 45 ถนน...\nAddress: 99/12 ถนน...\nEnd"),
                         "Start\nAddress: XX ถนน...\nAddress: XX/XX ถนน...\nEnd")

    def test_address_no_partial_house_number_or_cross_line_match(self):
        for text in ("Address:\n45 ถนน", "Address: 99/12/3 ถนน", "Address: 12-34", "Address: 123abc",
                     "address: 123", "MyAddress: 123", "unrelated text"):
            with self.subTest(text=text):
                self.assertEqual(censor_house_number(text), text)

    def test_imports_have_no_input_output_or_file_io(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=AssertionError("interactive input")), \
             patch("builtins.open", side_effect=AssertionError("file operation")), \
             contextlib.redirect_stdout(output):
            for name in ("creditcardreg", "gmailreg", "phonereg", "birthdayreg", "address"):
                importlib.reload(importlib.import_module("regex." + name))
        self.assertEqual(output.getvalue(), "")


class MaskerTest(unittest.TestCase):
    def test_five_rule_sample(self):
        result = mask_text(SAMPLES[0]["text"])
        self.assertEqual(result["total_detected"], 5)
        self.assertEqual(result["counts"], dict.fromkeys(RULE_MAP, 1))
        self.assertEqual(result["masked_characters"], 39)
        self.assertIn("s************e@example.com", result["masked_text"])

    def test_seven_match_sample(self):
        result = mask_text(SAMPLES[1]["text"])
        self.assertEqual(result["total_detected"], 7)
        self.assertEqual(result["counts"], {"credit_card": 1, "email": 2, "phone": 2, "dob": 1, "address": 1})

    def test_each_toggle_only_changes_selected_rule(self):
        text = SAMPLES[0]["text"]
        for rule in RULES:
            with self.subTest(rule=rule.key):
                result = mask_text(text, [rule.key])
                self.assertEqual(result["masked_text"], rule.mask(text))
                self.assertEqual(result["total_detected"], 1)
                self.assertEqual(result["counts"][rule.key], 1)

    def test_disabled_email_is_unchanged(self):
        text = SAMPLES[0]["text"]
        result = mask_text(text, [key for key in RULE_MAP if key != "email"])
        self.assertIn("somchai.jaidee@example.com", result["masked_text"])
        self.assertEqual(result["counts"]["email"], 0)

    def test_all_rules_disabled(self):
        text = SAMPLES[0]["text"]
        result = mask_text(text, [])
        self.assertEqual(result["masked_text"], text)
        self.assertEqual(result["total_detected"], 0)
        self.assertEqual(result["masked_characters"], 0)

    def test_short_emails_detected_but_not_masked(self):
        result = mask_text("a@gmail.com ab@gmail.com")
        self.assertEqual(result["total_detected"], 2)
        self.assertEqual(result["masked_characters"], 0)
        self.assertTrue(all(not detection["changes"] for detection in result["detections"]))

    def test_empty_and_unmatched_text(self):
        for text in ("", " \t\n", "Hello สวัสดี 🧪 <script>alert(1)</script>"):
            with self.subTest(text=text):
                self.assertEqual(mask_text(text)["masked_text"], text)
                self.assertEqual(mask_text(text)["total_detected"], 0)

    def test_metadata_spans_unicode_and_crlf(self):
        text = "🧪 ภาษาไทย\r\nAddress: 99/12 หมู่ 4\r\nEmail: card@gmail.com\rDOB: 25/12/2549"
        result = mask_text(text)
        self.assertEqual([item["line"] for item in result["detections"]], [2, 3, 4])
        self.assertEqual(result["masked_characters"], 12)  # 4 house digits + 2 email chars + 6 DOB chars
        # Each rule now swaps a character for a character, so output offsets
        # match input offsets even after three replacements on three lines.
        self.assertEqual(len(result["masked_text"]), len(text))
        self.assertEqual(result["detections"][1]["output_start"], text.index("card@gmail.com"))
        edits = []
        for detection in result["detections"]:
            self.assertEqual(result["masked_text"][detection["output_start"]:detection["output_end"]],
                             detection["masked_preview"])
            self.assertEqual(RULE_MAP[detection["rule"]].mask(text[detection["start"]:detection["end"]]),
                             detection["masked_preview"])
            edits.extend(detection["changes"])
        reconstructed = text
        for change in reversed(edits):
            replacement = result["masked_text"][change["output_start"]:change["output_end"]]
            reconstructed = reconstructed[:change["start"]] + replacement + reconstructed[change["end"]:]
        self.assertEqual(reconstructed, result["masked_text"])

    def test_compare_spans_leave_separators_visible(self):
        text = "1234-5678-9012-3456 093-245-7894 DOB: 25/12/2549 Address: 99/12"
        result = mask_text(text)
        for detection in result["detections"]:
            for change in detection["changes"]:
                self.assertTrue(text[change["start"]:change["end"]].isdigit())

    def test_overlapping_card_email_is_one_email(self):
        result = mask_text("1234-5678-9012-3456@example.com")
        self.assertEqual(result["total_detected"], 1)
        self.assertEqual(result["counts"]["email"], 1)
        self.assertEqual(result["masked_text"], "1*****************6@example.com")

    def test_repeated_scanning_does_not_change_masked_output(self):
        text = SAMPLES[0]["text"] + "\nEmail: a@gmail.com ab@gmail.com"
        masked = mask_text(text)["masked_text"]
        self.assertEqual(mask_text(masked)["masked_text"], masked)

    def test_bad_module_arguments(self):
        with self.assertRaises(TypeError):
            mask_text(None)
        with self.assertRaises(ValueError):
            mask_text("text", ["unknown"])

    def test_public_patterns_match_compiled_patterns(self):
        for rule in RULES:
            self.assertEqual(rule.public()["pattern"], rule.pattern.pattern)
            self.assertTrue(rule.public()["tokens"])


if __name__ == "__main__":
    unittest.main()
