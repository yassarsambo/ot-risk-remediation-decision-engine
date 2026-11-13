"""Deterministic, standard-library-only regression and safety invariant tests."""
import copy
import json
from pathlib import Path
import unittest
from src.decision_engine import decide
from src.validator import InputError, validate_case, validate_dataset
from main import run

ROOT = Path(__file__).resolve().parents[1]
CASES, RESULTS, POLICY = run(ROOT / "data/synthetic_cases_v0.1.json", ROOT / "policy/v0.1.json")


class EngineTests(unittest.TestCase):
    def test_all_five_fixture_expectations(self):
        for c, r in zip(CASES, RESULTS):
            with self.subTest(c["case_id"]):
                self.assertEqual(c["expected"]["triage_tier"], r["triage_tier"])
                self.assertEqual(c["expected"]["candidate_action"], r["candidate_action"])
                self.assertEqual(c["expected"]["safety_gate"], "ENGINEERING_SAFETY_REVIEW_REQUIRED" in r["gates"])
                self.assertFalse(r["operational_action_performed"])
                self.assertIn("OT asset owner", r["human_approvals_required"])

    def test_deterministic(self):
        self.assertEqual([decide(c, POLICY) for c in CASES], [decide(c, POLICY) for c in CASES])

    def test_high_safety_gate_even_when_patch_ready(self):
        c = copy.deepcopy(CASES[0])
        for f in POLICY["patch_readiness_fields"]:
            c[f] = True
        r = decide(c, POLICY)
        self.assertEqual(r["candidate_action"], "PROPOSE_PATCH_IN_APPROVED_WINDOW")
        self.assertIn("ENGINEERING_SAFETY_REVIEW_REQUIRED", r["gates"])
        self.assertFalse(r["operational_action_performed"])

    def test_low_epss_does_not_negate_kev(self):
        c = copy.deepcopy(CASES[1]); c["epss_probability"] = 0.0
        self.assertEqual(decide(c, POLICY)["triage_tier"], "P1")

    def test_unverified_reachability_is_unresolved(self):
        c = copy.deepcopy(CASES[1]); c["reachability_verified"] = False
        self.assertEqual(decide(c, POLICY)["triage_tier"], "NEEDS_CONTEXT_REVIEW")
        self.assertEqual(decide(c, POLICY)["candidate_action"], "GATHER_EVIDENCE_AND_ESCALATE")
        self.assertIn("URGENT_EXPERT_TRIAGE_FLAG_DESPITE_UNRESOLVED_CASE", decide(c, POLICY)["reason_codes"])

    def test_unknown_applicability_not_low_priority(self):
        c = copy.deepcopy(CASES[1]); c["applicability"] = "unknown"
        self.assertEqual(decide(c, POLICY)["triage_tier"], "ASSESS_APPLICABILITY")

    def test_unknown_patch_test_blocks_patch_proposal(self):
        c = copy.deepcopy(CASES[1]); c["patch_tested"] = "unknown"
        self.assertEqual(decide(c, POLICY)["candidate_action"], "PLAN_CONTROLLED_MITIGATION_AND_PATCH_REVIEW")

    def test_reject_invalid_epss(self):
        c = copy.deepcopy(CASES[0]); c["epss_probability"] = 1.2
        with self.assertRaises(InputError): validate_case(c)

    def test_reject_boolean_severity(self):
        c = copy.deepcopy(CASES[0]); c["severity_proxy_0_10"] = True
        with self.assertRaises(InputError): validate_case(c)

    def test_reject_real_data(self):
        c = copy.deepcopy(CASES[0]); c["data_classification"] = "confidential"
        with self.assertRaises(InputError): validate_case(c)

    def test_reject_duplicate_cases(self):
        with self.assertRaises(InputError): validate_dataset({"cases":[CASES[0], CASES[0]]})

    def test_isolation_high_severity_no_immediate_patch(self):
        c = copy.deepcopy(CASES[0]); c["kev"] = True
        r = decide(c, POLICY)
        self.assertEqual(r["triage_tier"], "P2")
        self.assertEqual(r["candidate_action"], "PLAN_CONTROLLED_MITIGATION_AND_PATCH_REVIEW")


if __name__ == "__main__":
    unittest.main()
