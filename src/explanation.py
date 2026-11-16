"""Human-readable offline report; no OT control interfaces."""


def markdown_comparison(cases, results):
    by_id = {r["case_id"]: r for r in results}
    baseline = sorted(cases, key=lambda x: (-x["severity_proxy_0_10"], x["case_id"]))
    policy_version = next(iter(by_id.values()), {}).get("policy_version", "0.1")
    lines = [f"# OT-RRDE v{policy_version}: synthetic severity-only baseline comparison", "",
             "**Research-only demonstration.** Inputs are fictional; severity is a 0–10 proxy, not official CVSS; the policy has not been externally calibrated. Higher triage urgency is **not** a command to patch.", "",
             "| Severity-only rank | Case | Synthetic severity | OT-aware triage | Candidate action |", "| ---: | --- | ---: | --- | --- |"]
    for i, c in enumerate(baseline, 1):
        r = by_id[c["case_id"]]
        lines.append(f"| {i} | {c['case_id']} | {c['severity_proxy_0_10']:.1f} | {r['triage_tier']} | {r['candidate_action']} |")
    lines += ["", "## Case-by-case decision explanations", ""]
    for r in results:
        lines += [f"### {r['case_id']}: {r['triage_tier']}", "", r["investigation_summary"], "",
                  f"- Candidate: `{r['candidate_action']}`",
                  f"- Reasons: {', '.join(r['reason_codes'])}",
                  f"- Safety gates: {', '.join(r['gates']) if r['gates'] else 'No high-consequence gate, but human approval always required'}",
                  f"- Data warnings: {', '.join(r['data_quality_warnings']) if r['data_quality_warnings'] else 'none'}",
                  f"- Missing evidence: {', '.join(r['missing_evidence']) if r['missing_evidence'] else 'none flagged'}", ""]
    lines += ["## Methodological cautions", "",
              "- This baseline merely sorts synthetic severity proxies; it does not model full CVSS or operational constraints.",
              "- No improvement in safety, incident outcomes or real-world remediation effectiveness has been demonstrated.",
              "- No live infrastructure, industrial devices or network scanners are connected.",
              "- Peer review and expert-labelled scenarios are required before any claim of practical validity."]
    return "\n".join(lines) + "\n"
