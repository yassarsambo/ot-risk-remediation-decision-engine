"""Check the published table adapter and preservation of unknown evidence."""
from copy import deepcopy
import unittest

from scripts.evaluate_ssvc_pilot import compare_pilot, load_materials, lookup_outcome


class SsvcComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, cls.dataset, cls.model = load_materials()
        cls.outcome = cls.model["outcome"]
        cls.inputs = [key for key in cls.model["decision_points"] if key != cls.outcome]

    def test_all_published_rows_return_their_native_outcome(self):
        labels = {
            item["key"]: item["name"]
            for item in self.model["decision_points"][self.outcome]["values"]
        }
        self.assertEqual(len(self.model["mapping"]), 72)
        for row in self.model["mapping"]:
            values = {key: row[key] for key in self.inputs}
            with self.subTest(values=values):
                self.assertEqual(lookup_outcome(self.model, values), labels[row[self.outcome]])

    def test_unknown_input_withholds_a_priority(self):
        complete = {key: self.model["mapping"][0][key] for key in self.inputs}
        for key in self.inputs:
            with self.subTest(missing=key):
                incomplete = {**complete, key: None}
                self.assertIsNone(lookup_outcome(self.model, incomplete))

    def test_literal_none_differs_from_unresolved_exploitation(self):
        values = {key: self.model["mapping"][0][key] for key in self.inputs}
        self.assertEqual(values["ssvc:E:1.1.0"], "N")
        self.assertEqual(lookup_outcome(self.model, values), "Defer")
        values["ssvc:E:1.1.0"] = None
        self.assertIsNone(lookup_outcome(self.model, values))

    def test_invalid_value_and_incomplete_key_set_are_rejected(self):
        values = {key: self.model["mapping"][0][key] for key in self.inputs}
        with self.assertRaisesRegex(ValueError, "Unsupported SSVC input"):
            lookup_outcome(self.model, {**values, "ssvc:A:2.0.0": False})
        values.pop("ssvc:A:2.0.0")
        with self.assertRaisesRegex(ValueError, "exactly the four"):
            lookup_outcome(self.model, values)

    def test_duplicate_reference_rows_raise_a_clear_error(self):
        altered = deepcopy(self.model)
        altered["mapping"].append(deepcopy(altered["mapping"][0]))
        values = {key: altered["mapping"][0][key] for key in self.inputs}
        with self.assertRaisesRegex(ValueError, "exactly one"):
            lookup_outcome(altered, values)

    def test_replay_retains_scope_defaults_and_urgent_flags(self):
        report = compare_pilot()
        self.assertEqual(report["case_count"], 8)
        by_id = {item["case_id"]: item for item in report["results"]}
        pump = by_id["PILOT-72"]
        self.assertEqual(pump["ssvc_inputs"]["ssvc:EXP:1.0.1"], "O")
        self.assertEqual(pump["defaulted_decision_points"], ["System Exposure"])
        self.assertTrue(pump["rrde_v0.3-dev"]["urgent_while_unresolved"])
        self.assertIsNone(by_id["PILOT-16"]["ssvc_inputs"]["ssvc:E:1.1.0"])
        self.assertTrue(by_id["PILOT-35"]["deployment_rating_scope"]["within_protocol"])
        self.assertFalse(by_id["PILOT-64"]["deployment_rating_scope"]["within_protocol"])

    def test_ssvc_exploitation_does_not_use_epss_as_observation(self):
        report = compare_pilot()
        by_id = {item["case_id"]: item for item in report["results"]}
        for case_id in ("PILOT-41", "PILOT-83"):
            with self.subTest(case=case_id):
                self.assertIsNone(by_id[case_id]["ssvc_inputs"]["ssvc:E:1.1.0"])
        self.assertEqual(by_id["PILOT-83"]["rrde_v0.2.1"]["triage_tier"], "P2")
        self.assertEqual(by_id["PILOT-83"]["rrde_v0.3-dev"]["triage_tier"], "P3")


if __name__ == "__main__":
    unittest.main()
