"""Reproducible descriptive analysis of fictional challenge scenarios.

The 'expected' fixture labels are policy-authored and are NOT expert ground truth.
"""
import json
from collections import Counter
from pathlib import Path
from src.decision_engine import decide

ROOT = Path(__file__).resolve().parents[1]


def main():
    data = json.loads((ROOT / "data/challenge_cases_v0.2.1.json").read_text(encoding="utf-8"))
    policy = json.loads((ROOT / "policy/v0.2.1.json").read_text(encoding="utf-8"))
    cases = data["cases"]
    results = [decide(case, policy) for case in cases]
    expectation_matches = sum(
        (result["triage_tier"], result["candidate_action"]) ==
        (case["expected"]["triage_tier"], case["expected"]["candidate_action"])
        for case, result in zip(cases, results)
    )
    priorities = Counter(r["triage_tier"] for r in results)
    actions = Counter(r["candidate_action"] for r in results)
    severity_order = sorted(cases, key=lambda c: (-c["severity_proxy_0_10"], c["case_id"]))
    output = [
        "# OT-RRDE v0.2.1: Descriptive Synthetic Benchmark",
        "",
        "**Not a validity study.** Expected labels were authored alongside the test policy; matching them",
        "measures implementation consistency, not decision quality, safety or independent accuracy.",
        "",
        f"- Fictional cases: **{len(cases)}**",
        f"- Expected label matches: **{expectation_matches}/{len(cases)}** (circular regression check, NOT accuracy)",
        "- Priority counts: " + ", ".join(f"`{k}`: {v}" for k, v in sorted(priorities.items())),
        "- Candidate-action counts: " + ", ".join(f"`{k}`: {v}" for k, v in sorted(actions.items())),
        "",
        "| Severity-only rank | Case | Severity proxy | Research triage | Candidate action |",
        "| ---: | --- | ---: | --- | --- |",
    ]
    by_id = {r["case_id"]: r for r in results}
    for rank, case in enumerate(severity_order, 1):
        result = by_id[case["case_id"]]
        output.append(
            f"| {rank} | {case['case_id']} | {case['severity_proxy_0_10']:.1f} | "
            f"{result['triage_tier']} | {result['candidate_action']} |"
        )
    output += [
        "",
        "## Controlled contrasts",
        "",
        "- BENCH-006 vs BENCH-007: approval of high-availability impact review changes patch proposal eligibility.",
        "- BENCH-008 vs BENCH-009: nonredundant downtime contingency changes patch proposal eligibility.",
        "- BENCH-010: unknown redundancy is not overridden by a declared contingency.",
        "- BENCH-011 vs BENCH-012: claimed versus fresh, relevant isolation evidence changes whether isolation is considered substantiated *within the synthetic fixture*.",
        "- BENCH-012 vs BENCH-013: stale evidence is not credited even when labelled verified.",
        "- BENCH-014: irrelevant, claimed controls do not reduce exploit-driven P1 triage.",
        "",
        "## Limitations and research priorities",
        "",
        "The cases reuse fictional asset templates, are not independent expert-labelled examples, and",
        "are not representative of OT installations. The 90-day evidence-age cutoff is an arbitrary",
        "research heuristic; it is not a safety standard. The program cannot validate that a lab",
        "evidence assertion or an approval is authentic. Evidence credit never proves effective",
        "protection, does not lower vulnerability urgency, and is not a substitute for engineering",
        "risk assessment. No actual incidents, industrial processes or CVSS/EPSS feeds are studied.",
        "",
        "Next: blinded OT expert labels, counterexamples, reproducible sensitivity testing and",
        "comparison with realistic operational and SSVC-inspired prioritisation workflows.",
        "",
    ]
    target = ROOT / "reports/v0.2.1_benchmark.md"
    target.parent.mkdir(exist_ok=True)
    target.write_text("\n".join(output), encoding="utf-8")
    print(f"Written {target}; cases={len(cases)}, regression expectations={expectation_matches}/{len(cases)}")


if __name__ == "__main__":
    main()
