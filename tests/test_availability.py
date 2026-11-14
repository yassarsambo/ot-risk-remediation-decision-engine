"""v0.2 operational availability and redundancy safety-invariant tests.

Synthetic test inputs only. No operational controls are changed.
"""
import copy
from pathlib import Path
import json
import unittest

from src.decision_engine import decide
from src.validator import InputError, validate_case

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/synthetic_cases_v0.1.json").read_text(encoding="utf-8"))["cases"]
POLICY_01 = json.loads((ROOT / "policy/v0.1.json").read_text(encoding="utf-8"))
POLICY_02 = json.loads((ROOT / "policy/v0.2.json").read_text(encoding="utf-8"))


def ready_case(index=1, impact="critical", redundant=True):
    case = copy.deepcopy(CASES[index])
    for field in POLICY_02["patch_readiness_fields"]:
        case[field] = True
    case["availability_consequence"] = impact
    case["redundancy_verified"] = redundant
    return case


class AvailabilityAssuranceTests(unittest.TestCase):
    def test_legacy_policy_behavior_is_preserved(self):
        case = ready_case(index=0, impact="critical", redundant=False)
        old = decide(case, POLICY_01)
        self.assertEqual(old["candidate_action"], "PROPOSE_PATCH_IN_APPROVED_WINDOW")
        self.assertNotIn("OPERATIONAL_AVAILABILITY_REVIEW_REQUIRED", old["gates"])
        self.assertEqual(old["policy_version"], "0.1")

    def test_critical_impact_without_review_blocks_patch(self):
        case = ready_case()
        result = decide(case, POLICY_02)
        self.assertEqual(result["candidate_action"], "PLAN_CONTROLLED_MITIGATION_AND_PATCH_REVIEW")
        self.assertIn("OPERATIONAL_AVAILABILITY_REVIEW_REQUIRED", result["gates"])
        self.assertIn("AVAILABILITY_ASSURANCE_BLOCKS_PATCH_PROPOSAL", result["reason_codes"])
        self.assertIn("OT operations engineer", result["human_approvals_required"])
        self.assertFalse(result["operational_action_performed"])

    def test_verified_redundancy_with_approved_review_can_propose_patch(self):
        case = ready_case()
        case["availability_impact_review_approved"] = True
        result = decide(case, POLICY_02)
        self.assertEqual(result["candidate_action"], "PROPOSE_PATCH_IN_APPROVED_WINDOW")
        self.assertIn("OPERATIONAL_AVAILABILITY_REVIEW_REQUIRED", result["gates"])
        self.assertIn("OT operations engineer", result["human_approvals_required"])
        self.assertFalse(result["operational_action_performed"])

    def test_nonredundant_without_contingency_blocks_patch(self):
        case = ready_case(redundant=False)
        case["availability_impact_review_approved"] = True
        result = decide(case, POLICY_02)
        self.assertEqual(result["candidate_action"], "PLAN_CONTROLLED_MITIGATION_AND_PATCH_REVIEW")
        self.assertIn("NON_REDUNDANT_SERVICE_CONTINGENCY_REQUIRED", result["gates"])
        self.assertIn("DOWNTIME_CONTINGENCY_NOT_APPROVED", result["reason_codes"])

    def test_nonredundant_with_explicit_contingency_allows_proposal_only(self):
        case = ready_case(redundant=False)
        case["availability_impact_review_approved"] = True
        case["downtime_contingency_approved"] = True
        result = decide(case, POLICY_02)
        self.assertEqual(result["candidate_action"], "PROPOSE_PATCH_IN_APPROVED_WINDOW")
        self.assertIn("NON_REDUNDANT_SERVICE_CONTINGENCY_REQUIRED", result["gates"])
        self.assertFalse(result["operational_action_performed"])

    def test_unknown_redundancy_cannot_be_bypassed_with_contingency(self):
        case = ready_case(redundant="unknown")
        case["availability_impact_review_approved"] = True
        case["downtime_contingency_approved"] = True
        result = decide(case, POLICY_02)
        self.assertEqual(result["candidate_action"], "PLAN_CONTROLLED_MITIGATION_AND_PATCH_REVIEW")
        self.assertIn("REDUNDANCY_STATUS_VERIFICATION_REQUIRED", result["gates"])

    def test_unknown_review_not_treated_as_approval(self):
        case = ready_case()
        case["availability_impact_review_approved"] = "unknown"
        result = decide(case, POLICY_02)
        self.assertEqual(result["candidate_action"], "PLAN_CONTROLLED_MITIGATION_AND_PATCH_REVIEW")

    def test_medium_impact_preserves_existing_patch_proposal(self):
        case = ready_case(impact="medium", redundant="unknown")
        result = decide(case, POLICY_02)
        self.assertEqual(result["candidate_action"], "PROPOSE_PATCH_IN_APPROVED_WINDOW")
        self.assertNotIn("OPERATIONAL_AVAILABILITY_REVIEW_REQUIRED", result["gates"])

    def test_critical_safety_gate_remains_enforced(self):
        case = ready_case(index=0, impact="critical", redundant=False)
        case["availability_impact_review_approved"] = True
        case["downtime_contingency_approved"] = True
        result = decide(case, POLICY_02)
        self.assertEqual(result["candidate_action"], "PROPOSE_PATCH_IN_APPROVED_WINDOW")
        self.assertIn("ENGINEERING_SAFETY_REVIEW_REQUIRED", result["gates"])
        self.assertIn("safety engineer", result["human_approvals_required"])
        self.assertFalse(result["operational_action_performed"])

    def test_unknown_availability_impact_still_escalates(self):
        case = ready_case(impact="unknown")
        case["availability_impact_review_approved"] = True
        result = decide(case, POLICY_02)
        self.assertEqual(result["triage_tier"], "NEEDS_CONTEXT_REVIEW")
        self.assertEqual(result["candidate_action"], "GATHER_EVIDENCE_AND_ESCALATE")

    def test_reject_nonboolean_approval_integer(self):
        case = ready_case()
        case["availability_impact_review_approved"] = 1
        with self.assertRaises(InputError):
            validate_case(case)

    def test_reject_invalid_contingency_field(self):
        case = ready_case()
        case["downtime_contingency_approved"] = "yes"
        with self.assertRaises(InputError):
            validate_case(case)

    def test_unready_patch_cannot_bypass_gates(self):
        case = ready_case()
        case["availability_impact_review_approved"] = True
        case["patch_tested"] = False
        result = decide(case, POLICY_02)
        self.assertEqual(result["candidate_action"], "PLAN_CONTROLLED_MITIGATION_AND_PATCH_REVIEW")
        self.assertIn("NO_PATCH_TEST", result["reason_codes"])

    def test_v02_outputs_explain_availability_evidence(self):
        case = ready_case(redundant="unknown")
        result = decide(case, POLICY_02)
        self.assertEqual(result["input_signals"]["availability_consequence"], "critical")
        self.assertEqual(result["input_signals"]["redundancy_verified"], "unknown")
        self.assertEqual(result["input_signals"]["availability_impact_review_approved"], "unknown")
        self.assertTrue(any("redundancy" in s for s in result["missing_evidence"]))


if __name__ == "__main__":
    unittest.main()
