"""Control-evidence checks and 15-case synthetic challenge benchmark (research only)."""
import copy
import json
from pathlib import Path
import unittest

from src.decision_engine import decide
from src.validator import InputError, validate_case, validate_dataset

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = json.loads((ROOT / "data/challenge_cases_v0.2.1.json").read_text(encoding="utf-8"))
POLICY = json.loads((ROOT / "policy/v0.2.1.json").read_text(encoding="utf-8"))
BASE_POLICY = json.loads((ROOT / "policy/v0.2.json").read_text(encoding="utf-8"))
CASES = BENCHMARK["cases"]
BY_ID = {case["case_id"]: case for case in CASES}


class ControlEvidenceAndBenchmarkTests(unittest.TestCase):
    def test_benchmark_contains_fifteen_unique_synthetic_cases(self):
        self.assertEqual(len(validate_dataset(BENCHMARK)), 15)
        self.assertEqual(len(BY_ID), 15)

    def test_all_fifteen_expected_decisions_are_reproduced(self):
        for case in CASES:
            with self.subTest(case=case["case_id"]):
                result = decide(case, POLICY)
                self.assertEqual(result["triage_tier"], case["expected"]["triage_tier"])
                self.assertEqual(result["candidate_action"], case["expected"]["candidate_action"])
                self.assertFalse(result["operational_action_performed"])
                self.assertIn("control_assessment", result)

    def test_legacy_v02_does_not_apply_new_control_review(self):
        result = decide(BY_ID["BENCH-011"], BASE_POLICY)
        self.assertNotIn("control_assessment", result)
        self.assertNotEqual(result["triage_tier"], "NEEDS_CONTEXT_REVIEW")

    def test_claimed_isolation_fails_closed(self):
        result = decide(BY_ID["BENCH-011"], POLICY)
        self.assertEqual(result["triage_tier"], "NEEDS_CONTEXT_REVIEW")
        self.assertIn("ISOLATION_ASSERTION_UNSUPPORTED_BY_CONTROL_EVIDENCE", result["reason_codes"])
        self.assertFalse(result["control_assessment"]["isolation_record_supported"])

    def test_relevant_fresh_isolation_passes_synthetic_consistency_not_safety(self):
        result = decide(BY_ID["BENCH-012"], POLICY)
        self.assertEqual(result["triage_tier"], "P2")
        self.assertTrue(result["control_assessment"]["isolation_record_supported"])
        self.assertIn("ENGINEERING_SAFETY_REVIEW_REQUIRED", result["gates"])
        self.assertFalse(result["operational_action_performed"])

    def test_stale_isolation_is_not_credited(self):
        result = decide(BY_ID["BENCH-013"], POLICY)
        self.assertEqual(result["triage_tier"], "NEEDS_CONTEXT_REVIEW")
        reasons = [item["reason"] for item in result["control_assessment"]["not_credited"]]
        self.assertIn("CONTROL_EVIDENCE_STALE_RESEARCH_HEURISTIC", reasons)

    def test_irrelevant_control_does_not_reduce_exploitation_urgency(self):
        result = decide(BY_ID["BENCH-014"], POLICY)
        self.assertEqual(result["triage_tier"], "P1")
        self.assertFalse(result["control_assessment"]["credited"])
        self.assertIn("CONTROL_EFFECTIVENESS_NOT_VERIFIED", result["reason_codes"])

    def test_exploited_known_reachable_case_does_not_change_with_claimed_control(self):
        original = copy.deepcopy(BY_ID["BENCH-014"])
        altered = copy.deepcopy(original)
        altered["compensating_controls"] = []
        self.assertEqual(decide(original, POLICY)["triage_tier"], decide(altered, POLICY)["triage_tier"])

    def test_malformed_control_relevance_is_rejected(self):
        case = copy.deepcopy(BY_ID["BENCH-011"])
        case["compensating_controls"][0]["attack_path_relevance"] = "always safe"
        with self.assertRaises(InputError):
            validate_case(case)

    def test_malformed_control_date_is_rejected(self):
        case = copy.deepcopy(BY_ID["BENCH-012"])
        case["compensating_controls"][0]["verification_as_of"] = "yesterday"
        with self.assertRaises(InputError):
            validate_case(case)

    def test_unknown_relevance_is_not_credited(self):
        case = copy.deepcopy(BY_ID["BENCH-012"])
        case["compensating_controls"][0]["attack_path_relevance"] = "unknown"
        result = decide(case, POLICY)
        self.assertEqual(result["triage_tier"], "NEEDS_CONTEXT_REVIEW")

    def test_isolated_without_controls_is_not_assumed_verified(self):
        case = copy.deepcopy(BY_ID["BENCH-012"])
        case["compensating_controls"] = []
        result = decide(case, POLICY)
        self.assertEqual(result["triage_tier"], "NEEDS_CONTEXT_REVIEW")

    def test_critical_availability_requires_approval_in_new_policy(self):
        result = decide(BY_ID["BENCH-006"], POLICY)
        self.assertIn("OPERATIONAL_AVAILABILITY_REVIEW_REQUIRED", result["gates"])
        self.assertEqual(result["candidate_action"], "PLAN_CONTROLLED_MITIGATION_AND_PATCH_REVIEW")

    def test_reproducible_results(self):
        first = [decide(case, POLICY) for case in CASES]
        second = [decide(case, POLICY) for case in CASES]
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
