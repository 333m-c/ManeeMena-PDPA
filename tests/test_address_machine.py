"""The address automaton must recognize the existing regex, character by character."""

from itertools import product
import unittest

from regex.address import RULE
from regex.rule import build_machine, trace_machine


class AddressMachineTest(unittest.TestCase):
    def assert_accepts(self, text):
        match = RULE.pattern.search(text)
        self.assertIsNotNone(match)
        machine = RULE.machine(text)
        self.assertTrue(machine["matched"])
        self.assertIsNone(machine["failure"])
        self.assertEqual(machine["offset"], match.start())
        self.assertEqual("".join(move["text"] for move in machine["trace"]), match.group())
        state, position = 0, match.start()
        masked_positions = []
        for move in machine["trace"]:
            edge = machine["edges"][move["edge"]]
            self.assertEqual((edge["from"], move["start"]), (state, position))
            self.assertEqual(edge["to"], move["to"])
            self.assertEqual(move["end"] - move["start"], 0 if edge["kind"] == "skip" else 1)
            if edge["masked"]:
                masked_positions.extend(range(move["start"], move["end"]))
            state, position = move["to"], move["end"]
        self.assertEqual(position, match.end())
        self.assertEqual(machine["states"][state]["kind"], "accept")
        self.assertEqual(masked_positions, [index for index in range(*match.span("house"))
                                           if text[index] != "/"])

    def test_sample_reaches_accept(self):
        self.assert_accepts(RULE.sample)

    def test_optional_parts_alternative_labels_and_whitespace(self):
        for house, space, soi, subdistrict, district, province in product(
            ("1", "987/654"), (" ", "\t  "),
            ("", "ซอยสุข ", "ซอย สุข 12 "),
            ("แขวง", "ตำบล"), ("เขต", "อำเภอ"), ("", "จังหวัด "),
        ):
            text = (f"Address:{space}{house}{space}{soi}ถนน{space}สุข{space}"
                    f"{subdistrict}{space}สวน{space}{district}{space}เมือง{space}"
                    f"{province}เชียงใหม่")
            with self.subTest(text=text):
                self.assert_accepts(text)
        # The regex permits no space after labels, including before จังหวัด.
        self.assert_accepts("Address:1 ถนนสุข แขวงสวน เขตเมืองจังหวัด เชียงใหม่")

    def test_invalid_addresses_have_a_rejection_trace(self):
        tail = "ถนนสุข แขวงสวน เขตเมือง กรุงเทพฯ"
        for text in (
            "", "Address: 12 a", "Address: 12", "Address: 12/3/4",
            "Address: 12 road", "Address: 12 ถนนสุข", "Address: 12 ถนนสุข แขวงสวน",
            "Address: 12 ถนนสุข แขวงสวน เขตเมือง", "Address: 12 ถนน แขวงสวน เขตเมือง กรุงเทพฯ",
            "Address: 12 ถนนสุข แขบลสวน เขตเมือง กรุงเทพฯ",
            "Address: 12 ถนนสุข แขวงสวน เขำเภอเมือง กรุงเทพฯ",
            f"Address: 12 ซอยสุข12 {tail}", f"Address: 12 ซอย 12 {tail}",
            f"Address: 12/ {tail}", f"Address: 12/3/4 {tail}",
            f"Address: 12\n{tail}", f"Address: 12\r\n{tail}",
            "Address: 12 ถนนสุข\nแขวงสวน เขตเมือง กรุงเทพฯ",
        ):
            with self.subTest(text=text):
                self.assertIsNone(RULE.pattern.search(text))
                machine = RULE.machine(text)
                self.assertFalse(machine["matched"])
                self.assertIsNotNone(machine["failure"])
                failure = machine["failure"]
                self.assertEqual("".join(move["text"] for move in machine["trace"]),
                                 text[:failure["position"]])
                self.assertEqual(failure["state"], machine["trace"][-1]["to"] if machine["trace"] else 0)

    def test_left_boundary_matches_the_regex(self):
        machine = build_machine(RULE.steps)
        for prefix in ("x", "ก", "_", "9", "/", "-"):
            with self.subTest(prefix=prefix):
                text = prefix + RULE.sample
                self.assertIsNone(RULE.pattern.search(text))
                moves, failure = trace_machine(machine, text, len(prefix), len(text))
                self.assertEqual(moves, [])
                self.assertEqual(failure["reason"], "guard")
                self.assertEqual(failure["position"], len(prefix))

    def test_search_offsets_and_unrestricted_right_boundary(self):
        for prefix in ("", "🧪 Log:\r\n", "Address: 12 a\n"):
            for suffix in ("", "/123", "-x", "abc", "\n" + RULE.sample):
                with self.subTest(prefix=prefix, suffix=suffix):
                    self.assert_accepts(prefix + RULE.sample + suffix)

    def test_long_name_loops_to_the_end(self):
        self.assert_accepts("Address:12 ถนน" + "ก" * 2000 + " แขวงสวน เขตเมือง กรุงเทพฯ")


if __name__ == "__main__":
    unittest.main()
