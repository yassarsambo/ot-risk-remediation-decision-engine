# OT-RRDE v0.1: synthetic severity-only baseline comparison

**Research-only demonstration.** Inputs are fictional; severity is a 0–10 proxy, not official CVSS; the policy has not been externally calibrated. Higher triage urgency is **not** a command to patch.

| Severity-only rank | Case | Synthetic severity | OT-aware triage | Candidate action |
| ---: | --- | ---: | --- | --- |
| 1 | SYN-OT-001 | 9.6 | P2 | PLAN_CONTROLLED_MITIGATION_AND_PATCH_REVIEW |
| 2 | SYN-OT-003 | 8.8 | P1 | PLAN_CONTROLLED_MITIGATION_AND_PATCH_REVIEW |
| 3 | SYN-OT-005 | 8.2 | ASSESS_APPLICABILITY | GATHER_EVIDENCE_AND_ESCALATE |
| 4 | SYN-OT-002 | 7.1 | P1 | PROPOSE_PATCH_IN_APPROVED_WINDOW |
| 5 | SYN-OT-004 | 6.8 | P2 | PROPOSE_PATCH_IN_APPROVED_WINDOW |

## Case-by-case decision explanations

### SYN-OT-001: P2

Prompt expert assessment is proposed, subject to operational constraints and safety approval.

- Candidate: `PLAN_CONTROLLED_MITIGATION_AND_PATCH_REVIEW`
- Reasons: HIGH_SAFETY_CONSEQUENCE, HIGH_SYNTHETIC_SEVERITY_SAFETY_CONSEQUENCE, VENDOR_APPROVAL_MISSING, NO_PATCH_TEST, NO_MAINTENANCE_WINDOW, NO_TESTED_ROLLBACK, MITIGATION_OPTIONS_REQUIRE_ENGINEERING_FEASIBILITY_REVIEW, CHANGE_NOT_YET_AUTHORISED
- Safety gates: ENGINEERING_SAFETY_REVIEW_REQUIRED
- Data warnings: none
- Missing evidence: confirm vendor approved, confirm patch tested, confirm maintenance window approved, confirm rollback tested

### SYN-OT-002: P1

Immediate human triage is proposed; this does not authorise an immediate patch.

- Candidate: `PROPOSE_PATCH_IN_APPROVED_WINDOW`
- Reasons: EXPLOITED_VULNERABILITY_WITH_VERIFIED_PATH, CONFIRMED_EXPLOITATION_INDICATOR_IN_SYNTHETIC_INPUT, ALL_PATCH_READINESS_GATES_SUPPORTED_IN_SYNTHETIC_RECORD, CHANGE_NOT_YET_AUTHORISED
- Safety gates: No high-consequence gate, but human approval always required
- Data warnings: none
- Missing evidence: none flagged

### SYN-OT-003: P1

Immediate human triage is proposed; this does not authorise an immediate patch.

- Candidate: `PLAN_CONTROLLED_MITIGATION_AND_PATCH_REVIEW`
- Reasons: HIGH_SAFETY_CONSEQUENCE, EXPLOITED_VULNERABILITY_WITH_VERIFIED_PATH, CONFIRMED_EXPLOITATION_INDICATOR_IN_SYNTHETIC_INPUT, NO_PATCH_TEST, NO_MAINTENANCE_WINDOW, NO_TESTED_ROLLBACK, MITIGATION_OPTIONS_REQUIRE_ENGINEERING_FEASIBILITY_REVIEW, CHANGE_NOT_YET_AUTHORISED
- Safety gates: ENGINEERING_SAFETY_REVIEW_REQUIRED
- Data warnings: UNVERIFIED_COMPENSATING_CONTROL_CLAIMS
- Missing evidence: confirm patch tested, confirm maintenance window approved, confirm rollback tested

### SYN-OT-004: P2

Prompt expert assessment is proposed, subject to operational constraints and safety approval.

- Candidate: `PROPOSE_PATCH_IN_APPROVED_WINDOW`
- Reasons: EPSS_THRESHOLD_AND_REACHABLE, ALL_PATCH_READINESS_GATES_SUPPORTED_IN_SYNTHETIC_RECORD, CHANGE_NOT_YET_AUTHORISED
- Safety gates: No high-consequence gate, but human approval always required
- Data warnings: none
- Missing evidence: none flagged

### SYN-OT-005: ASSESS_APPLICABILITY

Affected component not confirmed; verify applicability before operational remediation planning.

- Candidate: `GATHER_EVIDENCE_AND_ESCALATE`
- Reasons: VULNERABILITY_APPLICABILITY_UNCONFIRMED, NO_OPERATIONAL_CHANGE_WITH_MISSING_FACTS, CHANGE_NOT_YET_AUTHORISED
- Safety gates: No high-consequence gate, but human approval always required
- Data warnings: EPSS_NOT_PROVIDED_OR_UNKNOWN, EXPLOITATION_INTELLIGENCE_INCOMPLETE
- Missing evidence: verify vulnerable component, version and asset applicability, verify actual network reachability or isolation, OT safety consequence assessment, dated EPSS source value (if applicable)

## Methodological cautions

- This baseline merely sorts synthetic severity proxies; it does not model full CVSS or operational constraints.
- No improvement in safety, incident outcomes or real-world remediation effectiveness has been demonstrated.
- No live infrastructure, industrial devices or network scanners are connected.
- Peer review and expert-labelled scenarios are required before any claim of practical validity.
