"""Offline CLI: python main.py [--input synthetic.json] [--output results.json] [--report comparison.md]."""
import argparse
import json
from pathlib import Path
from src.validator import InputError, validate_dataset
from src.decision_engine import decide
from src.explanation import markdown_comparison

ROOT = Path(__file__).resolve().parent


def run(input_path, policy_path):
    with open(input_path, encoding="utf-8") as f:
        payload = json.load(f)
    with open(policy_path, encoding="utf-8") as f:
        policy = json.load(f)
    cases = validate_dataset(payload)
    return cases, [decide(case, policy) for case in cases], policy


def main():
    parser = argparse.ArgumentParser(description="Offline, synthetic OT remediation decision research prototype")
    parser.add_argument("--input", type=Path, default=ROOT / "data/synthetic_cases_v0.1.json")
    parser.add_argument("--policy", type=Path, default=ROOT / "policy/v0.1.json")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/example_results.json")
    parser.add_argument("--report", type=Path, default=ROOT / "reports/triage_comparison.md")
    args = parser.parse_args()
    try:
        cases, results, policy = run(args.input, args.policy)
    except (InputError, json.JSONDecodeError, OSError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"policy_version": policy["policy_version"],
                                       "data_classification": "synthetic", "results": results},
                                      indent=2) + "\n", encoding="utf-8")
    args.report.write_text(markdown_comparison(cases, results), encoding="utf-8")
    for r in results:
        print(f"{r['case_id']}: {r['triage_tier']:>21}  {r['candidate_action']}")
    print(f"Results: {args.output}\nComparison: {args.report}")


if __name__ == "__main__":
    main()
