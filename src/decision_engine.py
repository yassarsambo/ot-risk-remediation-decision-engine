"""Deterministic, human-reviewed OT remediation decision-support policy."""
from copy import deepcopy
from datetime import date, datetime, timezone

from .validator import validate_case

READY_FIELDS = ("patch_available", "vendor_approved", "patch_tested", "maintenance_window_approved", "rollback_tested")
FIELD_REASON = {
    "patch_available": "PATCH_NOT_CONFIRMED_AVAILABLE",
    "vendor_approved": "VENDOR_APPROVAL_MISSING",
    "patch_tested": "NO_PATCH_TEST",
    "maintenance_window_approved": "NO_MAINTENANCE_WINDOW",
    "rollback_tested": "NO_TESTED_ROLLBACK",
}


def _availability_assurance(case, policy):
    """Additional v0.2 assurance gates; disabled for v0.1 policy reproduction."""
    if not policy.get("availability_gate_enabled", False):
        return [], [], [], True
    if case["availability_consequence"] not in policy["availability_review_categories"]:
        return [], [], [], True

    gates = ["OPERATIONAL_AVAILABILITY_REVIEW_REQUIRED"]
    reasons = ["HIGH_AVAILABILITY_CONSEQUENCE"]
    missing = []
    impact_review = case.get("availability_impact_review_approved", "unknown")
    if impact_review is True:
        reasons.append("AVAILABILITY_IMPACT_REVIEW_RECORDED")
    else:
        reasons.append("AVAILABILITY_IMPACT_REVIEW_PENDING")
        missing.append("record authorised operational availability-impact review")

    redundancy = case["redundancy_verified"]
    if redundancy is True:
        reasons.append("REDUNDANCY_VERIFIED_IN_SYNTHETIC_INPUT")
        redundancy_ready = True
    elif redundancy is False:
        gates.append("NON_REDUNDANT_SERVICE_CONTINGENCY_REQUIRED")
        reasons.append("NON_REDUNDANT_SERVICE")
        if case.get("downtime_contingency_approved", "unknown") is True:
            reasons.append("DOWNTIME_CONTINGENCY_APPROVED_IN_SYNTHETIC_INPUT")
            redundancy_ready = True
        else:
            reasons.append("DOWNTIME_CONTINGENCY_NOT_APPROVED")
            missing.append("approve documented downtime contingency for nonredundant service")
            redundancy_ready = False
    else:
        gates.append("REDUNDANCY_STATUS_VERIFICATION_REQUIRED")
        reasons.append("REDUNDANCY_STATUS_UNVERIFIED")
        missing.append("verify redundancy status and contingency requirements")
        redundancy_ready = False

    # An approved contingency supports a known nonredundant design, but cannot
    # substitute for verifying an UNKNOWN redundancy state.
    return gates, reasons, missing, impact_review is True and redundancy_ready


def _review_controls(case, policy):
    """Examine synthetic evidence assertions; never infer real-world efficacy."""
    if not policy.get("control_evidence_enabled", False):
        return None

    recorded = datetime.fromisoformat(case["recorded_at"].replace("Z", "+00:00")).date()
    credited, uncredited = [], []
    max_age = policy["control_evidence_max_age_days"]
    for control in case["compensating_controls"]:
        reason = None
        if control["effectiveness"] != "verified":
            reason = "CONTROL_EFFECTIVENESS_NOT_VERIFIED"
        elif control.get("attack_path_relevance") != "relevant":
            reason = "CONTROL_ATTACK_PATH_RELEVANCE_NOT_ESTABLISHED"
        elif control.get("control_type") not in ("network_isolation", "access_control", "monitoring", "other"):
            reason = "CONTROL_TYPE_UNSPECIFIED"
        elif not control.get("verification_as_of"):
            reason = "CONTROL_EVIDENCE_DATE_MISSING"
        else:
            verified_at = date.fromisoformat(control["verification_as_of"])
            age = (recorded - verified_at).days
            if age < 0:
                reason = "CONTROL_EVIDENCE_FUTURE_DATED"
            elif age > max_age:
                reason = "CONTROL_EVIDENCE_STALE_RESEARCH_HEURISTIC"
        item = {"name": control["name"], "control_type": control.get("control_type", "unknown")}
        if reason:
            uncredited.append({**item, "reason": reason})
        else:
            credited.append(item)
    return {
        "credited": credited,
        "not_credited": uncredited,
        "isolation_record_supported": any(c["control_type"] == "network_isolation" for c in credited),
        "caveat": "Credits only consistent assertions in synthetic inputs, not independently validated real controls.",
    }


def _utc_timestamp(raw):
    if not isinstance(raw, str):
        raise TypeError("expected an ISO timestamp")
    timestamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("timestamp requires an explicit UTC offset")
    return timestamp.astimezone(timezone.utc)


def _epss_timing_issue(case):
    """Check the supplied synthetic snapshot against the decision cutoff."""
    if case["epss_probability"] is None:
        return "EPSS_NOT_PROVIDED_OR_UNKNOWN"

    evidence = case.get("epss_evidence")
    if evidence is None:
        return "EPSS_SNAPSHOT_EVIDENCE_MISSING"
    snapshot_id = evidence.get("snapshot_id") if isinstance(evidence, dict) else None
    if not isinstance(snapshot_id, str) or not snapshot_id.strip():
        return "EPSS_SNAPSHOT_EVIDENCE_INVALID"

    try:
        score_date_text = evidence.get("score_date")
        score_date = date.fromisoformat(score_date_text)
        available_at = _utc_timestamp(evidence.get("available_at"))
        cutoff = _utc_timestamp(case["recorded_at"])
    except (TypeError, ValueError, OverflowError):
        return "EPSS_SNAPSHOT_TIMESTAMPS_INVALID"
    if score_date.isoformat() != score_date_text:
        return "EPSS_SNAPSHOT_TIMESTAMPS_INVALID"
    if score_date > cutoff.date() or available_at > cutoff:
        return "EPSS_EVIDENCE_AFTER_DECISION_CUTOFF"
    if score_date > available_at.date():
        return "EPSS_SNAPSHOT_AVAILABILITY_PRECEDES_SCORE_DATE"
    return None


def decide(case, policy):
    warnings = validate_case(case)
    reasons, missing, gates = [], [], []
    epss_probability = case["epss_probability"]
    epss_assessment = None
    if policy.get("epss_timing_gate_enabled", False):
        issue = _epss_timing_issue(case)
        if issue:
            epss_probability = None
            if issue not in warnings:
                warnings.append(issue)
        epss_assessment = {
            "decision_cutoff": case["recorded_at"],
            "snapshot_evidence": deepcopy(case.get("epss_evidence")),
            "eligible_probability": epss_probability,
            "exclusion_reason": issue,
        }
    control_review = _review_controls(case, policy)
    critical_safety = case["safety_consequence"] in policy["critical_safety_categories"]
    if critical_safety:
        gates.append("ENGINEERING_SAFETY_REVIEW_REQUIRED")
        reasons.append("HIGH_SAFETY_CONSEQUENCE")
    availability_gates, availability_reasons, availability_missing, availability_ready = _availability_assurance(case, policy)
    gates.extend(availability_gates)
    reasons.extend(availability_reasons)
    missing.extend(availability_missing)
    if control_review:
        for item in control_review["not_credited"]:
            reasons.append(item["reason"])
        if control_review["not_credited"]:
            missing.append("check compensating-control scope, supporting tests, and verification dates")
        if control_review["credited"]:
            reasons.append("CONTROL_EVIDENCE_ASSERTION_PASSES_SYNTHETIC_CHECKS")
        # Credited controls are never used to decrease triage urgency.
    isolated_claim_unsubstantiated = bool(
        control_review is not None
        and case["reachability"] == "isolated_verified"
        and not control_review["isolation_record_supported"]
    )
    if isolated_claim_unsubstantiated:
        reasons.append("ISOLATION_ASSERTION_UNSUPPORTED_BY_CONTROL_EVIDENCE")
        missing.append("substantiate network isolation for the stated attack path")
    exploited = case["kev"] is True or case["active_exploitation_reported"] is True
    reachable = case["reachability"] in policy["known_reachable_paths"]
    context_missing = (case["safety_consequence"] == "unknown" or
                       case["availability_consequence"] == "unknown" or
                       case["reachability"] == "unknown" or
                       not case["reachability_verified"] or
                       isolated_claim_unsubstantiated)
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
          epss_probability is not None and
          epss_probability >= policy["epss_threshold"] and
          case["reachability"] in ("internet", "enterprise_path")):
        tier = "P1"
        reasons.append("SEVERE_EXPOSED_HIGH_EPSS_PROXY")
    elif (exploited and case["reachability"] == "isolated_verified"):
        tier = "P2"
        reasons.append("EXPLOITED_BUT_VERIFIED_ISOLATION")
    elif epss_probability is not None and epss_probability >= policy["epss_threshold"] and reachable:
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
    if epss_probability is None:
        missing.append(
            "EPSS snapshot available by the decision cutoff (if applicable)"
            if epss_assessment is not None else "dated EPSS source value (if applicable)"
        )
    if tier in ("ASSESS_APPLICABILITY", "NEEDS_CONTEXT_REVIEW"):
        action = "GATHER_EVIDENCE_AND_ESCALATE"
        reasons.append("NO_OPERATIONAL_CHANGE_WITH_MISSING_FACTS")
    elif all(case.get(k) is True for k in READY_FIELDS) and availability_ready:
        action = "PROPOSE_PATCH_IN_APPROVED_WINDOW"
        reasons.append("ALL_PATCH_READINESS_GATES_SUPPORTED_IN_SYNTHETIC_RECORD")
    else:
        action = "PLAN_CONTROLLED_MITIGATION_AND_PATCH_REVIEW"
        if not availability_ready:
            reasons.append("AVAILABILITY_ASSURANCE_BLOCKS_PATCH_PROPOSAL")
        for k in READY_FIELDS:
            if case.get(k) is not True:
                reasons.append(FIELD_REASON[k])
                missing.append(f"confirm {k.replace('_', ' ')}")
        reasons.append("MITIGATION_OPTIONS_REQUIRE_ENGINEERING_FEASIBILITY_REVIEW")

    approvals = ["OT asset owner", "change manager"]
    if critical_safety or case["safety_consequence"] == "unknown":
        approvals.insert(1, "safety engineer")
    if availability_gates:
        approvals.insert(1, "OT operations engineer")
    if case["change_authorised"] is True:
        reasons.append("EXISTING_CHANGE_AUTHORISATION_RECORDED_NOT_EXECUTED")
    else:
        reasons.append("CHANGE_NOT_YET_AUTHORISED")
    if control_review is not None and control_review["not_credited"]:
        warnings.append("CONTROL_EVIDENCE_UNCONFIRMED_FOR_STATED_ATTACK_PATH")
    confidence = "limited" if warnings or tier in ("ASSESS_APPLICABILITY", "NEEDS_CONTEXT_REVIEW") else "moderate"
    outcome = {
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
    if policy.get("availability_gate_enabled", False):
        outcome["input_signals"].update({
            "availability_consequence": case["availability_consequence"],
            "redundancy_verified": case["redundancy_verified"],
            "availability_impact_review_approved": case.get("availability_impact_review_approved", "unknown"),
            "downtime_contingency_approved": case.get("downtime_contingency_approved", "unknown"),
        })
    if control_review is not None:
        outcome["control_assessment"] = control_review
    if epss_assessment is not None:
        outcome["epss_assessment"] = epss_assessment
    return outcome


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
