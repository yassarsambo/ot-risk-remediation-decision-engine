"""Matched synthetic probes for the experimental EPSS decision cutoff."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from src.decision_engine import decide

ROOT = Path(__file__).resolve().parents[1]
BASELINE = json.loads((ROOT / "policy/v0.2.1.json").read_text(encoding="utf-8"))
CANDIDATE = json.loads((ROOT / "policy/v0.3-dev.json").read_text(encoding="utf-8"))
BENCHMARK = json.loads((ROOT / "data/challenge_cases_v0.2.1.json").read_text(encoding="utf-8"))
TEMPLATE = next(case for case in BENCHMARK["cases"] if case["case_id"] == "BENCH-014")


def make_case(score_date="2026-11-14", available_at="2026-11-14T08:00:00Z"):
    case = deepcopy(TEMPLATE)
    case.pop("expected", None)
    case.update(
        recorded_at="2026-11-15T12:00:00Z",
        reachability="internet",
        reachability_verified=True,
        severity_proxy_0_10=9.6,
        kev=False,
        active_exploitation_reported=False,
        epss_probability=0.30,
        threat_data_as_of=score_date,
        epss_evidence={
            "snapshot_id": f"SYNTH-EPSS-{score_date}",
            "score_date": score_date,
            "available_at": available_at,
        },
    )
    return case


class EpssTimingTests(unittest.TestCase):
    def test_matched_baseline_and_candidate_priorities(self):
        in_time = make_case()
        future = make_case("2026-11-16", "2026-11-16T08:00:00Z")
        missing = make_case()
        missing.update(epss_probability=None, threat_data_as_of=None, epss_evidence=None)

        expected = [
            ("available", in_time, "P1", "P1", 0.30, None),
            ("future", future, "P1", "P2", None, "EPSS_EVIDENCE_AFTER_DECISION_CUTOFF"),
            ("missing", missing, "P2", "P2", None, "EPSS_NOT_PROVIDED_OR_UNKNOWN"),
        ]
        for label, case, legacy_tier, candidate_tier, score, exclusion in expected:
            with self.subTest(case=label):
                baseline = decide(case, BASELINE)
                candidate = decide(case, CANDIDATE)
                self.assertEqual(baseline["triage_tier"], legacy_tier)
                self.assertEqual(candidate["triage_tier"], candidate_tier)
                self.assertEqual(candidate["candidate_action"], baseline["candidate_action"])
                self.assertNotIn("epss_assessment", baseline)
                self.assertEqual(candidate["input_signals"]["epss_probability"], case["epss_probability"])
                assessment = candidate["epss_assessment"]
                self.assertEqual(assessment["eligible_probability"], score)
                self.assertEqual(assessment["exclusion_reason"], exclusion)
                self.assertEqual(assessment["snapshot_evidence"], case["epss_evidence"])
                if exclusion:
                    self.assertIn(exclusion, candidate["data_quality_warnings"])

        self.assertIn("THREAT_DATA_DATE_AFTER_RECORDING", decide(future, BASELINE)["data_quality_warnings"])

    def test_same_day_cutoff_includes_exact_instant_and_respects_offset(self):
        case = make_case("2026-11-15", "2026-11-15T11:00:00Z")
        case["recorded_at"] = "2026-11-15T12:00:00+01:00"

        at_cutoff = decide(case, CANDIDATE)
        self.assertEqual(at_cutoff["triage_tier"], "P1")
        self.assertEqual(at_cutoff["epss_assessment"]["eligible_probability"], 0.30)

        case["epss_evidence"]["available_at"] = "2026-11-15T11:00:01Z"
        after_cutoff = decide(case, CANDIDATE)
        self.assertEqual(after_cutoff["triage_tier"], "P2")
        self.assertEqual(after_cutoff["epss_assessment"]["exclusion_reason"], "EPSS_EVIDENCE_AFTER_DECISION_CUTOFF")
        self.assertEqual(at_cutoff["epss_assessment"]["snapshot_evidence"]["available_at"], "2026-11-15T11:00:00Z")

    def test_future_score_date_can_exclude_an_in_time_availability_claim(self):
        case = make_case("2026-11-16", "2026-11-15T08:00:00Z")
        result = decide(case, CANDIDATE)
        self.assertEqual(result["triage_tier"], "P2")
        self.assertEqual(result["epss_assessment"]["exclusion_reason"], "EPSS_EVIDENCE_AFTER_DECISION_CUTOFF")

    def test_score_date_is_compared_in_utc(self):
        case = make_case("2026-11-15", "2026-11-15T00:05:00Z")
        case["recorded_at"] = "2026-11-14T19:30:00-05:00"
        result = decide(case, CANDIDATE)
        self.assertEqual(result["triage_tier"], "P1")
        self.assertEqual(result["epss_assessment"]["eligible_probability"], 0.30)

    def test_zero_is_an_eligible_score_with_valid_evidence(self):
        case = make_case()
        case["epss_probability"] = 0
        result = decide(case, CANDIDATE)
        self.assertEqual(result["triage_tier"], "P2")
        self.assertEqual(result["epss_assessment"]["eligible_probability"], 0)
        self.assertIsNone(result["epss_assessment"]["exclusion_reason"])

    def test_unusable_snapshot_evidence_withholds_only_epss(self):
        good_evidence = make_case()["epss_evidence"]
        variants = [
            (None, "EPSS_SNAPSHOT_EVIDENCE_MISSING"),
            ({**good_evidence, "snapshot_id": " "}, "EPSS_SNAPSHOT_EVIDENCE_INVALID"),
            ({**good_evidence, "score_date": "yesterday"}, "EPSS_SNAPSHOT_TIMESTAMPS_INVALID"),
            ({**good_evidence, "available_at": "2026-11-14T08:00:00"}, "EPSS_SNAPSHOT_TIMESTAMPS_INVALID"),
            ({**good_evidence, "available_at": "2026-11-13T08:00:00Z"}, "EPSS_SNAPSHOT_AVAILABILITY_PRECEDES_SCORE_DATE"),
        ]
        for evidence, reason in variants:
            with self.subTest(reason=reason):
                case = make_case()
                case["epss_evidence"] = evidence
                result = decide(case, CANDIDATE)
                self.assertEqual(result["triage_tier"], "P2")
                self.assertEqual(result["epss_assessment"]["exclusion_reason"], reason)

        case = make_case()
        case["recorded_at"] = "2026-11-15T12:00:00"
        result = decide(case, CANDIDATE)
        self.assertEqual(result["triage_tier"], "P2")
        self.assertEqual(result["epss_assessment"]["exclusion_reason"], "EPSS_SNAPSHOT_TIMESTAMPS_INVALID")

    def test_future_snapshot_cannot_drive_the_lower_epss_priority_rule(self):
        in_time = make_case()
        future = make_case("2026-11-16", "2026-11-16T08:00:00Z")
        for case in (in_time, future):
            case.update(severity_proxy_0_10=6.8, reachability="controlled_path", safety_consequence="moderate")

        self.assertEqual(decide(in_time, CANDIDATE)["triage_tier"], "P2")
        self.assertEqual(decide(future, CANDIDATE)["triage_tier"], "P3")

    def test_reported_exploitation_retains_urgent_review_with_unknown_reachability(self):
        case = make_case("2026-11-16", "2026-11-16T08:00:00Z")
        case.update(active_exploitation_reported=True, reachability="unknown", reachability_verified=False)
        result = decide(case, CANDIDATE)

        self.assertEqual(result["triage_tier"], "NEEDS_CONTEXT_REVIEW")
        self.assertIn("URGENT_EXPERT_TRIAGE_FLAG_DESPITE_UNRESOLVED_CASE", result["reason_codes"])
        self.assertEqual(result["candidate_action"], "GATHER_EVIDENCE_AND_ESCALATE")
        self.assertIsNone(result["epss_assessment"]["eligible_probability"])
        self.assertFalse(result["operational_action_performed"])
