"""Deterministic, human-reviewed OT remediation decision-support policy."""
from .validator import validate_case

READY_FIELDS = ("patch_available", "vendor_approved", "patch_tested", "maintenance_window_approved", "rollback_tested")
FIELD_REASON = {
    "patch_available": "PATCH_NOT_CONFIRMED_AVAILABLE",
    "vendor_approved": "VENDOR_APPROVAL_MISSING",
    "patch_tested": "NO_PATCH_TEST",
    "maintenance_window_approved": "NO_MAINTENANCE_WINDOW",
    "rollback_tested": "NO_TESTED_ROLLBACK",
}


def decide(case, policy):
    warnings = validate_case(case)
    reasons, missing, gates = [], [], []
    critical_safety = case["safety_consequence"] in policy["critical_safety_categories"]
    if critical_safety:
        gates.append("ENGINEERING_SAFETY_REVIEW_REQUIRED")
        reasons.append("HIGH_SAFETY_CONSEQUENCE")
    exploited = case["kev"] is True or case["active_exploitation_reported"] is True
    reachable = case["reachability"] in policy["known_reachable_paths"]
    context_missing = (case["safety_consequence"] == "unknown" or
                       case["availability_consequence"] == "unknown" or
                       case["reachability"] == "unknown" or
                       not case["reachability_verified"])
    if case["applicability"] != "confirmed":
        tier = "ASSESS_APPLICABILITY"
        reasons.append("VULNERABILITY_APPLICABILITY_UNCONFIRMED")
        missing.append("verify vulnerable component, version and asset applicability")
    elif context_missing:
        tier = "NEEDS_CONTEXT_REVIEW"
        reasons.append("CRITICAL_OPERATIONAL_CONTEXT_INCOMPLETE")
    elif exploited and reachable:
        tier = "P1"
        reasons.append("EXPLOITED_VULNERABILITY_WITH_VERIFIED_PATH")
    elif (case["severity_proxy_0_10"] >= policy["synthetic_severity_p1"] and
          case["epss_probability"] is not None and
          case["epss_probability"] >= policy["epss_threshold"] and
          case["reachability"] in ("internet", "enterprise_path")):
        tier = "P1"
        reasons.append("SEVERE_EXPOSED_HIGH_EPSS_PROXY")
    elif (exploited and case["reachability"] == "isolated_verified"):
        tier = "P2"
        reasons.append("EXPLOITED_BUT_VERIFIED_ISOLATION")
    elif (case["epss_probability"] is not None and
          case["epss_probability"] >= policy["epss_threshold"] and reachable):
        tier = "P2"
        reasons.append("EPSS_THRESHOLD_AND_REACHABLE")
    elif (case["severity_proxy_0_10"] >= policy["synthetic_severity_p2"] and critical_safety):
        tier = "P2"
        reasons.append("HIGH_SYNTHETIC_SEVERITY_SAFETY_CONSEQUENCE")
    elif (case["severity_proxy_0_10"] >= policy["synthetic_severity_p1"] and reachable):
        tier = "P2"
        reasons.append("SEVERE_AND_REACHABLE")
    else:
        tier = "P3"
        reasons.append("COMPLETE_CASE_SCHEDULED_ASSESSMENT")

    if exploited:
        reasons.append("CONFIRMED_EXPLOITATION_INDICATOR_IN_SYNTHETIC_INPUT")
        if tier in ("ASSESS_APPLICABILITY", "NEEDS_CONTEXT_REVIEW"):
            reasons.append("URGENT_EXPERT_TRIAGE_FLAG_DESPITE_UNRESOLVED_CASE")
    if not case["reachability_verified"]:
        missing.append("verify actual network reachability or isolation")
    if case["safety_consequence"] == "unknown":
        missing.append("OT safety consequence assessment")
    if case["availability_consequence"] == "unknown":
        missing.append("OT availability consequence assessment")
    if case["epss_probability"] is None:
        missing.append("dated EPSS source value (if applicable)")
    if tier in ("ASSESS_APPLICABILITY", "NEEDS_CONTEXT_REVIEW"):
        action = "GATHER_EVIDENCE_AND_ESCALATE"
        reasons.append("NO_OPERATIONAL_CHANGE_WITH_MISSING_FACTS")
    elif all(case.get(k) is True for k in READY_FIELDS):
        action = "PROPOSE_PATCH_IN_APPROVED_WINDOW"
        reasons.append("ALL_PATCH_READINESS_GATES_SUPPORTED_IN_SYNTHETIC_RECORD")
    else:
        action = "PLAN_CONTROLLED_MITIGATION_AND_PATCH_REVIEW"
        for k in READY_FIELDS:
            if case.get(k) is not True:
                reasons.append(FIELD_REASON[k])
                missing.append(f"confirm {k.replace('_', ' ')}")
        reasons.append("MITIGATION_OPTIONS_REQUIRE_ENGINEERING_FEASIBILITY_REVIEW")

    approvals = ["OT asset owner", "change manager"]
    if critical_safety or case["safety_consequence"] == "unknown":
        approvals.insert(1, "safety engineer")
    if case["change_authorised"] is True:
        reasons.append("EXISTING_CHANGE_AUTHORISATION_RECORDED_NOT_EXECUTED")
    else:
        reasons.append("CHANGE_NOT_YET_AUTHORISED")
    confidence = "limited" if warnings or tier in ("ASSESS_APPLICABILITY", "NEEDS_CONTEXT_REVIEW") else "moderate"
    return {
        "case_id": case["case_id"], "policy_version": policy["policy_version"],
        "triage_tier": tier, "investigation_summary": _summary(tier, case, exploited),
        "candidate_action": action, "gates": gates, "reason_codes": reasons,
        "missing_evidence": missing, "data_quality_warnings": warnings,
        "human_approvals_required": approvals, "confidence": confidence,
        "confidence_meaning": "completeness of fictional inputs, NOT statistical correctness",
        "source_data_classification": "synthetic", "decision_generated_at": "simulation-only",
        "asset_id": case["asset_id"], "vuln_id": case["vuln_id"],
        "input_signals": {"severity_proxy_0_10": case["severity_proxy_0_10"],
                          "epss_probability": case["epss_probability"],
                          "kev": case["kev"], "active_exploitation_reported": case["active_exploitation_reported"],
                          "reachability": case["reachability"], "reachability_verified": case["reachability_verified"],
                          "safety_consequence": case["safety_consequence"],
                          "patch_ready_fields": {k: case[k] for k in READY_FIELDS}},
        "operational_action_performed": False,
    }


def _summary(tier, case, exploited):
    if tier == "ASSESS_APPLICABILITY":
        return "Affected component not confirmed; verify applicability before operational remediation planning."
    if tier == "NEEDS_CONTEXT_REVIEW":
        return "Critical exposure or operational impact evidence is incomplete; request expert triage."
    if tier == "P1":
        return "Immediate human triage is proposed; this does not authorise an immediate patch."
    if tier == "P2":
        return "Prompt expert assessment is proposed, subject to operational constraints and safety approval."
    return "Scheduled expert assessment is proposed from complete synthetic input signals."
