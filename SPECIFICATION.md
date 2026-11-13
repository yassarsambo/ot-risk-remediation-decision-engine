# OT Risk & Remediation Decision Engine (OT-RRDE)

**Technical specification v0.1 (research prototype) | 13 November 2026**  
**Status (implementation update, 13 November 2026):** A Python proof-of-concept implementing the proposed policy has been written and passed 12 local unit tests. No independent evaluation, calibration, production validation or deployment has occurred.

## 1. Mission and research question

**Mission.** Provide explainable, human-reviewed recommendations for *triaging* a vulnerability affecting an operational technology (OT) asset and selecting a *candidate remediation pathway* that respects safety, availability, maintenance and evidence quality.

**Research question.** For a synthetic collection of OT scenarios, does a transparent, operations-aware remediation decision policy produce more technically defensible and operationally feasible *candidate actions* than sorting vulnerabilities by reported CVSS Base severity alone?

**Hypothesis (unproven).** A two-stage method separating *investigation urgency* from *remediation feasibility*, with explicit safety gates and missing-data escalation, will avoid some unsafe or misleading patch-first recommendations while still escalating known exploited and reachable vulnerabilities.

**Non-goals.** This first version does **not** discover vulnerabilities, calculate formal CVSS v4 scores, provide probabilities of incident occurrence for a particular asset, operate machinery, scan production networks, change firewall rules, deploy patches, certify IEC 62443 compliance or claim novel exploitation research.

## 2. Standards and evidence boundaries

- **NIST SP 800-82 Rev. 3 (final):** reflects OT-specific safety, performance and reliability requirements. NIST SP 800-82 Rev. 4 was an *initial public draft* released 21 September 2026 (not a final standard as of this specification).
- **FIRST CVSS v4.0:** the Base score measures vulnerability severity, *not* organisation-specific risk. When real CVSS values are used, preserve the version, vector, source, date and whether Threat/Environmental metrics are included. Do not imply that a nonstandard composite score is an official CVSS score.
- **FIRST EPSS:** estimates observed in-the-wild exploitation activity for a published CVE over the next 30 days; **it does not measure the probability of compromise of a particular OT asset**. Record collection date. EPSS and KEV are separate signals; confirmed exploitation should not be negated by a low EPSS.
- **CISA KEV / SSVC concepts:** use confirmed known exploitation and context as relevant signals, but our output categories are **not** official CISA SSVC decisions and do not substitute for a site-specific risk assessment.
- This is an **illustrative hypothesis and proposed decision policy**, not a validated vendor or standards method. No vendor endorsement or originality is claimed.

## 3. Intended users and workflow

**Users:** OT security analyst, OT engineer, asset owner, safety engineer, change manager.  
**Workflow:** load synthetic cases -> validate data -> derive threat/exposure and operational consequences -> assign investigation urgency -> evaluate feasible candidate actions -> produce an explainable recommendation with required approvals, missing information and evidence provenance -> human decision.

A recommendation is advisory. The system must include the exact input data and policy version that produced it; if important input changes, the recommendation must be recalculated and reviewed.

## 4. Input data model (case schema v0.1)

One case represents an *asserted affected vulnerability on a particular asset*, not merely a CVE record. Use the following fields. `unknown` is a real state, never silently treated as zero risk.

| Group | Field | Type / accepted values | Purpose |
| --- | --- | --- | --- |
| Identity | `case_id` | unique string | Reproducible case identity |
| Asset | `asset_id`, `asset_type` | strings; types such as PLC, HMI, historian, engineering workstation | What might be affected |
| Asset | `zone` | `ot_control`, `ot_dmz`, `enterprise`, `unknown` | Architecture context, not proof of reachability |
| Asset | `safety_consequence` | `none`, `moderate`, `major`, `catastrophic`, `unknown` | Worst credible safety consequence if compromised/changed; subject to expert review |
| Asset | `availability_consequence` | `low`, `medium`, `high`, `critical`, `unknown` | Potential loss of operational service |
| Asset | `redundancy_verified` | `true`, `false`, `unknown` | Whether redundancy is supported by evidence |
| Vulnerability | `applicability` | `confirmed`, `suspected`, `unknown` | Whether vulnerable component/version is actually present |
| Vulnerability | `vuln_id` | synthetic ID or validated CVE | Avoid fictional real CVE assertions |
| Vulnerability | `severity_proxy_0_10` | number 0–10 for synthetic fixtures | **Illustrative only. Not an official CVSS value.** |
| Vulnerability | `cvss` | optional object: `version`, `score`, `vector`, `source`, `as_of` | Real sourced CVSS data in later adapters; validate version/vector |
| Exploitation | `kev` | `true`, `false`, `unknown` | Confirmed catalog status where verifiable |
| Exploitation | `active_exploitation_reported` | `true`, `false`, `unknown` | Distinguish independently sourced reports from an assumption |
| Exploitation | `epss_probability` | number 0–1 or `null` | 30-day population signal, not asset compromise risk |
| Exploitation | `threat_data_as_of` | ISO date or `null` | Provenance and freshness |
| Exposure | `reachability` | `internet`, `enterprise_path`, `controlled_path`, `isolated_verified`, `unknown` | Observed or independently substantiated access path |
| Exposure | `reachability_verified` | boolean | Ensure exposure classification has supporting evidence |
| Controls | `compensating_controls` | list of `{name, effectiveness: verified/claimed/unknown, evidence}` | A listed rule is not automatically an effective control |
| Remediation | `patch_available`, `vendor_approved`, `patch_tested` | `true`, `false`, `unknown` each | Operational patch readiness |
| Remediation | `maintenance_window_approved`, `rollback_tested` | `true`, `false`, `unknown` each | Change safety and recoverability |
| Remediation | `change_authorised` | boolean | Human approval gate; never inferred |
| Provenance | `data_classification`, `notes`, `recorded_at` | strings, ISO datetime | Traceability; all initial fixtures must say `synthetic` |

**Implementation convention:** actual JSON uses `null` when a source does not provide a numeric EPSS value. A missing or stale source generates a data-quality alert; it is not equivalent to `0`.

## 5. Decision policy v0.1 — deterministic and explainable

### Stage A — validate the case (before assigning priority)

- If `applicability != confirmed`, output **ASSESS_APPLICABILITY**; request component/version verification. Retain any observed exploitation alert in the explanation.
- If safety or availability consequence is `unknown`, or reachability is `unknown` / unverified, output **NEEDS_CONTEXT_REVIEW**. Do **not** assign an apparently reassuring low priority. A known exploited vulnerability can still be flagged for immediate triage while context is established.
- Confirm a valid 0–10 synthetic severity proxy, valid EPSS probability (if supplied), enumerations and provenance. Reject malformed cases.
- Emit a separate `data_quality_warnings` list for missing/threat-data freshness and claimed-but-unverified controls.

### Stage B — investigation urgency (no automatic patching)

The following **proposal-only, uncalibrated** policy is designed for testable consistency, not real-site SLAs. Evaluate in order; first matching rule determines the tier.

1. **P1 — immediate expert triage:** (a) `kev=true` or `active_exploitation_reported=true`, *and* reachability is `internet`, `enterprise_path` or `controlled_path`; OR (b) synthetic severity >= 9.0, EPSS >= 0.10 and reachability is `internet` or `enterprise_path`.
2. **P2 — prompt assessment:** (a) confirmed exploitation but reachability is `isolated_verified`; OR (b) EPSS >= 0.10 and reachable by a known path; OR (c) severity >= 7.0 *and* `safety_consequence` is `major` or `catastrophic`; OR (d) severity >= 9.0 and reachable by a known path.
3. **P3 — scheduled assessment:** other complete, applicable cases.
4. **Unresolved** cases from Stage A retain **ASSESS_APPLICABILITY** / **NEEDS_CONTEXT_REVIEW**, not P3.

**Important:** thresholds of 0.10 and 9.0 are transparent *research defaults* for the first prototype. They are not standards thresholds, calibrated probabilities, validated risk tolerance or a substitute for threat intelligence. Safety consequences increase review attention; they must **not** force immediate patch deployment.

### Stage C — candidate remediation pathway (separate from urgency)

Decisions are made in this order:

1. **Expert safety gate.** If `safety_consequence` is `major` or `catastrophic`, record **ENGINEERING_SAFETY_REVIEW_REQUIRED** for *every* change. No route grants automatic implementation authority.
2. **Patch ready for approval:** only if `patch_available=true`, `vendor_approved=true`, `patch_tested=true`, `maintenance_window_approved=true`, `rollback_tested=true`. Output **PROPOSE_PATCH_IN_APPROVED_WINDOW** with explicit confirmation that designated human decision-makers must still authorise the change.
3. **Patch not ready:** output **PLAN_CONTROLLED_MITIGATION_AND_PATCH_REVIEW**. A control may be listed as an option only if evidence supports its feasibility; otherwise request an engineering assessment. Do not claim an untested segmentation change reduces exposure.
4. **Missing safety/operational context or unverified applicability:** output **GATHER_EVIDENCE_AND_ESCALATE**, with no operational change recommendation.
5. **Risk acceptance:** never auto-select. It requires authorised owner, recorded rationale, controls, review deadline and organisation policy.

`change_authorised=true` documents an authorisation for an *existing planned change*; it does not cause code execution. The prototype never performs any operational action. An approved maintenance window is necessary for the normal patch proposal but may be bypassed only by an independently documented organisational emergency-change process, **not by this engine**.

### Stage D — structured output

For each case return:

```json
{
  "case_id": "SYN-OT-001",
  "policy_version": "0.1",
  "triage_tier": "P2",
  "investigation_summary": "...",
  "candidate_action": "PLAN_CONTROLLED_MITIGATION_AND_PATCH_REVIEW",
  "gates": ["ENGINEERING_SAFETY_REVIEW_REQUIRED"],
  "reason_codes": ["HIGH_SAFETY_CONSEQUENCE", "NO_PATCH_TEST", "NO_MAINTENANCE_WINDOW"],
  "missing_evidence": ["approved patch test", "documented rollback"],
  "human_approvals_required": ["OT asset owner", "safety engineer", "change manager"],
  "confidence": "limited",
  "source_data_classification": "synthetic",
  "decision_generated_at": "simulation-only"
}
```

Confidence reflects **completeness of supporting evidence** (not a statistical measure of the recommendation's correctness). Each output must explain the main decision and the competing operational constraint.

## 6. Reference architecture (offline, read-only MVP)

```text
Synthetic JSON/CSV fixtures
          |
          v
   Schema validator ------> Reject/flag missing or contradictory fields
          |
          v
  Evidence normaliser ----> Provenance and stale-feed warnings
          |
          v
  Urgency policy engine ---> P1 / P2 / P3 / unresolved
          |
          v
 Remediation safety gate -> Candidate action + blockers + required approvals
          |
          v
 Explanation generator ---> JSON output + human-readable decision trace
          |
          v
 Local HTML report / CLI --> Human expert reviews; no operational connection
```

**Suggested implementation:** Python 3.12 standard library initially, JSON Schema (optional external validator), a command-line entry point and `pytest` for deterministic tests. Use versioned fixtures and policy parameters; no API keys or real OT networks required. A browser UI or offline FastAPI service is optional after correct CLI outputs are demonstrated. Do not ingest secrets or upload real asset data to public GitHub.

**Recommended repository structure (not yet created):**

```text
ot-remediation-decision-engine/
  README.md
  SPECIFICATION.md
  policy/v0.1.json
  schemas/case.schema.json
  data/synthetic_cases_v0.1.json
  src/validator.py
  src/decision_engine.py
  src/explanation.py
  tests/test_decisions.py
  reports/example_results.json
```

## 7. Synthetic test cases and *expected* outcomes

The companion `OT_RRDE_Synthetic_Cases_v0.1.json` contains five fictional cases. All severity values are **0–10 demonstration proxies**, not actual CVSS scores, and every EPSS/KEV field is a **fabricated test input**, not a claim about a real CVE.

| ID | Case | What a severity-only sort misses | Expected triage | Expected candidate action |
| --- | --- | --- | --- | --- |
| SYN-OT-001 | High-severity isolated PLC with catastrophic safety consequences, untested patch and no approved window | High severity does not make immediate patch safe | P2 | PLAN_CONTROLLED_MITIGATION_AND_PATCH_REVIEW + safety gate |
| SYN-OT-002 | Reachable, confirmed-exploitation historian with lower intrinsic severity and complete patch readiness | Exploitation evidence and exposure may justify attention before the PLC above | P1 | PROPOSE_PATCH_IN_APPROVED_WINDOW |
| SYN-OT-003 | Reachable vulnerable HMI, KEV flagged, patch not validated or scheduled | Urgency does not remove operational change prerequisites | P1 | PLAN_CONTROLLED_MITIGATION_AND_PATCH_REVIEW + safety gate |
| SYN-OT-004 | Reachable engineering workstation with high synthetic EPSS but moderate severity, prepared change plan | Dynamic exploitation likelihood can outrank severity alone | P2 | PROPOSE_PATCH_IN_APPROVED_WINDOW |
| SYN-OT-005 | Controller with uncertain applicability and reachability | Missing facts should not create an artificially low score | ASSESS_APPLICABILITY | GATHER_EVIDENCE_AND_ESCALATE |

**Key demonstration:** SYN-OT-002 ranks ahead of SYN-OT-001 for **investigation urgency** even though its severity proxy is lower. This is a *defined hypothesis of the policy*, not evidence that the engine improves real-world remediation decisions. We will test it with independent assessors.

## 8. Evaluation design and minimum acceptance tests

**Baseline:** sort by `severity_proxy_0_10` descending, with no operational context. Label baseline clearly as an illustrative *severity-only proxy*, not a faithful implementation of CVSS methodology.

**Candidate measures:**

1. **Rule consistency:** same input and policy version always produce identical categories and reason codes.
2. **Safety invariant:** no scenario suggests automatic changes; high-consequence assets always carry the safety review gate.
3. **Missing-data invariant:** unknown applicability, safety impact or reachability never silently becomes a low-priority case.
4. **Exploit-evidence invariant:** positive KEV/known exploitation can never be downgraded *solely* because EPSS is low.
5. **Evidence traceability:** each recommendation lists input values, reasons, caveats and policy version.
6. **Scenario agreement (later):** independent OT experts compare candidate actions against the baseline; log disagreement and revise rules. **Not yet tested.**
7. **Sensitivity (later):** perturb EPSS, path validity, patch readiness and safety classification to identify brittle recommendations. **Not yet tested.**

**No invented accuracy claims:** we cannot report reduced incidents, risk percentages, adoption, engineer productivity gains, compliance certification or validated patch safety. These require new experiments and/or independent trials.

## 9. Safety, security, legal and ethical boundaries

- **Offline and read-only by design** in v0.1. No active scanning, control-network access, exploit code, live patching, PLC manipulation or firewall writes.
- **Synthetic data only.** Never publish source OT device inventories, employer network diagrams, asset IPs, sensitive vendor details or customer incidents without explicit authorisation and safeguards.
- Human review by the OT asset owner, safety/engineering authority and change governance is mandatory for proposed changes.
- Avoid publication of backup files, credentials or sensitive threat intelligence. Public reports should show minimal evidence with justified redactions.
- Given the project's owner's unresolved immigration permissions, professional legal advice should clarify permitted external, voluntary and commercial activity before any external engagement or monetisation.

## 10. Milestones and exit criteria

| Milestone | Deliverable | Exit criterion |
| --- | --- | --- |
| M1 — this document | v0.1 spec + five synthetic fixtures | Input/output rules and safety limitations are explicit |
| M2 — prototype | Offline CLI policy engine | Automated tests pass for all five scenarios, with deterministic explanation traces |
| M3 — baseline | Side-by-side severity-only vs OT-aware report | Differences recorded without declaring unmeasured superiority |
| M4 — external critique | Review from relevant OT security/safety engineers and researchers | Concrete critique, review dates, changes and reviewer consent documented |
| M5 — research | Broader synthetic benchmark and uncertainty study | Replicable methods, limitations and independently inspected results |

## 11. Open questions (research backlog)

- Are these decision rules meaningfully different from existing SSVC-inspired OT workflows, and where exactly would originality lie?
- Should remediation choices be modelled as constraint satisfaction, multi-criteria decision analysis or argumentation graphs rather than threshold rules?
- How can we collect a credible and ethically usable benchmark of expert-approved OT scenarios without accessing sensitive infrastructure?
- How should control effectiveness, timing, safety assurance cases and downtime uncertainty be represented without false precision?
- What independent evaluation method best tests *decision quality* rather than raw numerical agreement?

## 12. Primary references (accessed November 2026)

1. NIST SP 800-82 Rev. 3 final, *Guide to Operational Technology Security*: https://csrc.nist.gov/pubs/sp/800/82/r3/final
2. NIST SP 800-82 Rev. 4, **initial public draft**, 21 September 2026: https://csrc.nist.gov/pubs/sp/800/82/r4/ipd
3. FIRST, *CVSS v4.0 Specification*: https://www.first.org/cvss/v4.0/specification-document
4. FIRST, *CVSS v4.0 User Guide*: https://www.first.org/cvss/user-guide
5. FIRST, *EPSS Overview*: https://www.first.org/epss/
6. FIRST, *EPSS Frequently Asked Questions*: https://www.first.org/epss/faq
7. CISA, *Known Exploited Vulnerabilities Catalog*: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**Authorship note:** This is a proposed design prepared collaboratively as a prototype planning document. Its algorithmic choices, thresholds and examples are exploratory and require technical review before publication as validated research.
