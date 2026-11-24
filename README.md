# OT Risk & Remediation Decision Engine (OT-RRDE)

**Latest research policy: v0.2.1 (compensating-control evidence checks and 15-case benchmark)** · **Status: offline, synthetic-data research prototype**  
**Default CLI policy: v0.1**, retained for reproducible comparisons. Select v0.2 or v0.2.1 explicitly using `--policy policy/v0.2.json` or `--policy policy/v0.2.1.json`.

OT-RRDE is an explainable Python prototype exploring how to **separate vulnerability investigation urgency from the operational feasibility of remediation** in operational technology (OT) environments. It evaluates fictional asset and threat inputs, returns human-reviewable candidate actions, and documents the evidence needed before considering a change.

> **Safety boundary:** This is not validated operational decision software. It does not scan OT networks, connect to industrial equipment, deploy patches, modify firewalls, or authorise changes. Recommendations are illustrative and require qualified site-specific engineering and change approval.

## What's new in v0.2.1

**Control evidence and evaluation benchmark:** v0.2.1 adds optional control type, attack-path relevance and evidence date fields to fictional control records. A control is only credited as an *internally consistent synthetic evidence assertion* when its status, relevance, type and date meet a transparent **90-day research heuristic**. This is **not** independent verification of control effectiveness.

- Unsupported `isolated_verified` claims cause `NEEDS_CONTEXT_REVIEW` instead of assuming isolation has been established.
- Crediting a control **never lowers exploitation urgency**, and cannot authorise any remediation.
- A [15-case synthetic challenge dataset](data/challenge_cases_v0.2.1.json), new tests and a [benchmark evaluation script](scripts/evaluate_benchmark.py) explore boundary cases.
- See the [v0.2.1 methodology and limitations](docs/v0.2.1-control-evidence-methodology.md). The expected benchmark labels were **written from our own rules**, not supplied by independent OT experts; matching them does not measure accuracy.

### Run the v0.2.1 research policy and benchmark

```powershell
py main.py --input data/challenge_cases_v0.2.1.json --policy policy/v0.2.1.json --output reports/v0.2.1_results.json --report reports/v0.2.1_comparison.md
py -m unittest discover -s tests -v
py scripts/evaluate_benchmark.py
```

`reports/v0.2.1_benchmark.md` is produced locally by the evaluation script. All cases are fictional and no OT equipment is accessed.

## What's new in v0.2

Version 0.2 adds an **operational availability assurance gate** alongside the existing patch-readiness and safety checks:

| Condition | Research policy behaviour |
| --- | --- |
| `availability_consequence` is `high` or `critical` | Require an explicit operational availability-impact review |
| Availability review not approved or unknown | Do **not** propose a patch yet; request review evidence |
| Redundancy verified | A patch may be *proposed* if the review and all other readiness checks are satisfied |
| No verified redundancy (`false`) | Require an approved downtime contingency before a patch proposal |
| Redundancy status unknown | Do **not** propose a patch until the status is established, even if a contingency was marked approved |
| Safety consequence is `major` or `catastrophic` | Preserve the engineering safety-review gate independently of patch readiness |

The additional optional synthetic input fields are `availability_impact_review_approved` and `downtime_contingency_approved`, each accepting `true`, `false` or `"unknown"`. Missing values are **not** treated as approved.

These controls affect **candidate remediation actions**, not automatic patch execution. For details and remaining limitations, read the [v0.2 methodology and safeguard notes](docs/v0.2-availability-safeguards.md).

## Run locally (Python 3.10+)

Use a terminal or PowerShell **inside this repository's root folder** (the folder containing `main.py`). The project uses only the Python standard library; no API keys, package installation or network access are needed.

### Run the latest research policy (v0.2)

```powershell
py main.py --policy policy/v0.2.json --output reports/v0.2_results.json --report reports/v0.2_comparison.md
```

This reads the five fictional cases from `data/synthetic_cases_v0.1.json` and writes:

- `reports/v0.2_results.json`: structured triage decisions, approval gates, reason codes and missing evidence.
- `reports/v0.2_comparison.md`: human-readable comparison against a **synthetic severity-only proxy** baseline.

On systems without the Windows `py` launcher, replace `py` with `python`.

### Run the preserved v0.1 baseline

```powershell
py main.py
```

Without an explicit `--policy`, the CLI **still uses `policy/v0.1.json`** and writes `reports/example_results.json` and `reports/triage_comparison.md`. This ensures earlier results remain reproducible.

### Run all automated checks

```powershell
py -m unittest discover -s tests -v
```

**The expanded automated suite** includes the original 26 tests plus new control-evidence and benchmark checks; see [GitHub Actions](../../actions) for current results. They test deterministic outputs, missing-data handling, research policy behaviour and selected safety invariants; passing tests is **not** evidence of real-world efficacy.

## How the decision engine works

```text
Synthetic OT asset + vulnerability records
                 |
                 v
       Validate and flag unknowns
                 |
                 v
      Investigation urgency policy
      (P1 / P2 / P3 / unresolved)
                 |
                 v
  Patch-readiness, safety and availability
      assurance gates (policy v0.2)
                 |
                 v
   Explainable candidate action + reasons
            + missing evidence
                 |
                 v
       Human expert reviews findings
           (no automated changes)
```

- **Investigation urgency** considers synthetic exploitation indicators, reported exposure, consequences, and data completeness. P1 means *immediate human triage*, not immediate patching.
- **Remediation feasibility** checks patch availability, vendor approval, testing, an approved maintenance window, rollback readiness, and (with v0.2) relevant operational availability and redundancy evidence.
- **Explanations** expose the input signals, policy version, warnings, gate reasons and required human approvals for review.

## Repository guide

| Path | Contents |
| --- | --- |
| [`SPECIFICATION.md`](SPECIFICATION.md) | Original research question, v0.1 methods, model assumptions and evaluation criteria |
| [`docs/v0.2-availability-safeguards.md`](docs/v0.2-availability-safeguards.md) | v0.2 change rationale, rules and limitations |
| [`policy/v0.1.json`](policy/v0.1.json) / [`policy/v0.2.json`](policy/v0.2.json) / [`policy/v0.2.1.json`](policy/v0.2.1.json) | Versioned experimental policies |
| [`data/synthetic_cases_v0.1.json`](data/synthetic_cases_v0.1.json) | Five original fictional OT vulnerability scenarios |
| [`data/challenge_cases_v0.2.1.json`](data/challenge_cases_v0.2.1.json) | Fifteen additional policy-challenge fixtures, including modified versions of original cases |
| [`docs/v0.2.1-control-evidence-methodology.md`](docs/v0.2.1-control-evidence-methodology.md) | Evidence assessment assumptions, methodological limitations and evaluation design |
| [`src/decision_engine.py`](src/decision_engine.py) | Urgency rules and remediation gates |
| [`src/validator.py`](src/validator.py) | Type, evidence and data-quality checks |
| [`src/explanation.py`](src/explanation.py) | Comparison and explanation report generation |
| [`tests/`](tests) | Unit tests for original and v0.2 research policies |
| [`SECURITY.md`](SECURITY.md) | Safety and permitted-use boundaries |

## Research limitations and next steps

- The five scenarios, severity scores, exploitation flags and EPSS figures are **fictional**. `severity_proxy_0_10` is **not an official CVSS score**.
- Research thresholds and decision rules have **not been calibrated or externally validated**. The severity-only ranking is an illustrative baseline, not a rigorous commercial-tool comparison.
- An approval field in a synthetic case is **not proof of real-world authorisation**; the tool does not independently verify reviewer identities, redundancy topology or contingency readiness.
- v0.2.1 adds **synthetic compensating-control consistency checks**, but it does not verify real controls. Threat-intelligence provenance, site-specific operational constraints, independent OT expert review and a larger expert-labelled benchmark remain open research tasks.
- No claim of demonstrated originality, risk reduction, operational deployment, external recognition or commercial adoption is made on the basis of this code alone.

**Next planned development:** review compensating-control evidence and distinguish exploitation signals more precisely, then expand the synthetic evaluation benchmark and obtain independent OT security/safety critique.

The project is intended for **authorised, offline educational and research evaluation only**.
