# OT Risk & Remediation Decision Engine (OT-RRDE)

**Version:** v0.1 · **Status:** offline research prototype, not operational decision software.

A small Python implementation of the two-stage policy in `SPECIFICATION.md`:

1. Validate fictional OT vulnerability inputs, preserving unknown states.
2. Assign investigation urgency: `P1`, `P2`, `P3`, or unresolved.
3. Apply **separate** patch readiness and engineering safety gates.
4. Generate explainable, human-reviewed *candidate* actions.
5. Compare results with a simple severity-proxy-only rank (not official CVSS).

## Run with Python 3.10+

From this repository directory:

```bash
python main.py
python -m unittest discover -s tests -v
```

The script reads `data/synthetic_cases_v0.1.json` and writes:

- `reports/example_results.json` — structured decisions and reason codes
- `reports/triage_comparison.md` — synthetic severity-only ranking versus OT-aware triage

No third-party packages, API keys, network access, scanning, production inventory or equipment changes are required.

## Files

- `SPECIFICATION.md` — design, methodology, assumptions, limitations
- `policy/v0.1.json` — research thresholds and gates
- `data/synthetic_cases_v0.1.json` — five fictional cases with expected outputs
- `src/validator.py` — strict type/value checks and evidence warnings
- `src/decision_engine.py` — urgency and candidate remediation decisions
- `src/explanation.py` — human-readable baseline comparison
- `tests/test_engine.py` — regression and safety-invariant tests

## Fundamental limits

- Inputs and results are **synthetic**. `severity_proxy_0_10` is not an official CVSS score; example KEV and EPSS values are fabricated.
- Triage policy is proposed and uncalibrated. It is **not an official SSVC decision tree** and has no demonstrated clinical, engineering or security accuracy.
- The engine only *suggests* actions. It cannot authorise or execute a patch, firewall rule or any operational change.
- Confidence labels describe completeness of synthetic inputs, not verified effectiveness.
- No original innovation, peer recognition, commercial value, risk reduction or Global Talent eligibility is established by this prototype. Such claims require comparison, expert review and reproducible external evaluation.

**Next research step:** present the five-case comparison to independent OT security/safety reviewers, collect criticism, and expand the benchmark with challenging counterexamples.
