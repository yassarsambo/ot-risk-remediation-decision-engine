"""Offline replay of author-proposed SSVC inputs for the eight pilot dossiers."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.decision_engine import decide
from src.validator import validate_dataset


def load_materials():
    manifest = json.loads((ROOT / "data/ssvc_pilot_mapping_v0.3.json").read_text(encoding="utf-8"))
    materials = []
    for reference in (manifest["dataset"], manifest["reference_model"]):
        raw = (ROOT / reference["path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
            raise ValueError(f"Source checksum differs: {reference['path']}")
        materials.append(json.loads(raw))
    dataset, model = materials
    return manifest, dataset, model


def lookup_outcome(model, values):
    """Return the native outcome name, or None when any input is unresolved."""
    outcome = model["outcome"]
    decision_points = {
        key: point for key, point in model["decision_points"].items()
        if key != outcome
    }
    if set(values) != set(decision_points):
        raise ValueError("Supply exactly the four versioned SSVC input keys")
    for key, value in values.items():
        choices = {item["key"] for item in decision_points[key]["values"]}
        if value is not None and value not in choices:
            raise ValueError(f"Unsupported SSVC input: {key}={value!r}")
    if None in values.values():
        return None

    rows = [
        row for row in model["mapping"]
        if all(row[key] == value for key, value in values.items())
    ]
    if len(rows) != 1:
        raise ValueError("Expected exactly one matching SSVC decision-table row")
    labels = {
        item["key"]: item["name"]
        for item in model["decision_points"][outcome]["values"]
    }
    return labels[rows[0][outcome]]


def compare_pilot():
    manifest, dataset, model = load_materials()
    cases = validate_dataset(dataset)
    mappings = manifest["cases"]
    mapping_ids = [item["case_id"] for item in mappings]
    case_ids = [case["case_id"] for case in cases]
    if len(set(mapping_ids)) != len(mapping_ids) or set(mapping_ids) != set(case_ids):
        raise ValueError("Mappings must identify each pilot case exactly once")
    by_id = {item["case_id"]: item for item in mappings}
    baseline_policy = json.loads((ROOT / "policy/v0.2.1.json").read_text(encoding="utf-8"))
    candidate_policy = json.loads((ROOT / "policy/v0.3-dev.json").read_text(encoding="utf-8"))

    results = []
    gaps = Counter()
    for case in cases:
        mapping = by_id[case["case_id"]]
        if mapping["evidence_cutoff"] != case["recorded_at"]:
            raise ValueError(f"Decision cutoff differs: {case['case_id']}")
        refs = set(case) | {item["source_id"] for item in case["evidence_records"]}
        for key, decision in mapping["decisions"].items():
            if not set(decision["evidence_refs"]) <= refs:
                raise ValueError(f"Unknown evidence reference: {case['case_id']}, {key}")
        values = {key: entry["value"] for key, entry in mapping["decisions"].items()}
        priority = lookup_outcome(model, values)
        missing = [
            model["decision_points"][key]["name"]
            for key, value in values.items() if value is None
        ]
        gaps.update(missing)
        baseline = decide(case, baseline_policy)
        candidate = decide(case, candidate_policy)
        urgent_flag = "URGENT_EXPERT_TRIAGE_FLAG_DESPITE_UNRESOLVED_CASE"
        results.append({
            "case_id": case["case_id"],
            "ssvc_inputs": values,
            "ssvc_priority": priority,
            "missing_decision_points": missing,
            "defaulted_decision_points": [
                model["decision_points"][key]["name"]
                for key, entry in mapping["decisions"].items() if entry["default_applied"]
            ],
            "deployment_rating_scope": mapping["deployment_rating_scope"],
            "rrde_v0.2.1": {
                "triage_tier": baseline["triage_tier"],
                "urgent_while_unresolved": urgent_flag in baseline["reason_codes"],
                "candidate_action": baseline["candidate_action"],
            },
            "rrde_v0.3-dev": {
                "triage_tier": candidate["triage_tier"],
                "urgent_while_unresolved": urgent_flag in candidate["reason_codes"],
                "candidate_action": candidate["candidate_action"],
            },
        })

    return {
        "model": manifest["reference_model"],
        "dataset": manifest["dataset"],
        "mapping_date": manifest["date"],
        "authorship": manifest["authoring_status"],
        "case_count": len(cases),
        "complete_ssvc_inputs": sum(item["ssvc_priority"] is not None for item in results),
        "within_deployment_rating_scope": sum(
            item["deployment_rating_scope"]["within_protocol"] for item in results
        ),
        "missing_inputs_by_case_count": dict(sorted(gaps.items())),
        "results": results,
    }


if __name__ == "__main__":
    print(json.dumps(compare_pilot(), indent=2) + "\n", end="")
