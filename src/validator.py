"""Synthetic case validation. No external libraries or network access."""
from datetime import date, datetime
import math

TRISTATE = (True, False, "unknown")
SAFETY = {"none", "moderate", "major", "catastrophic", "unknown"}
AVAILABILITY = {"low", "medium", "high", "critical", "unknown"}
REACHABILITY = {"internet", "enterprise_path", "controlled_path", "isolated_verified", "unknown"}
APPLICABILITY = {"confirmed", "suspected", "unknown"}
ZONES = {"ot_control", "ot_dmz", "enterprise", "unknown"}

REQUIRED_STRINGS = ("case_id", "asset_id", "asset_type", "vuln_id", "data_classification", "notes", "recorded_at")
TRISTATE_FIELDS = ("redundancy_verified", "kev", "active_exploitation_reported", "patch_available", "vendor_approved", "patch_tested", "maintenance_window_approved", "rollback_tested")
OPTIONAL_TRISTATE_FIELDS = ("availability_impact_review_approved", "downtime_contingency_approved")


class InputError(ValueError):
    """Raised when a case cannot be safely interpreted."""


def validate_case(case):
    """Return warnings and required human evidence. Reject malformed types and values."""
    if not isinstance(case, dict):
        raise InputError("case must be a JSON object")
    for field in REQUIRED_STRINGS:
        if not isinstance(case.get(field), str) or not case[field].strip():
            raise InputError(f"{field}: expected nonempty string")
    if case["data_classification"] != "synthetic":
        raise InputError("v0.1 accepts synthetic data only")
    try:
        datetime.fromisoformat(case["recorded_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise InputError("recorded_at: invalid ISO timestamp") from exc
    for name, choices in (("safety_consequence", SAFETY), ("availability_consequence", AVAILABILITY),
                          ("applicability", APPLICABILITY), ("reachability", REACHABILITY), ("zone", ZONES)):
        if case.get(name) not in choices:
            raise InputError(f"{name}: invalid or missing value")
    for name in TRISTATE_FIELDS:
        if case.get(name) not in TRISTATE or (isinstance(case.get(name), int) and not isinstance(case.get(name), bool)):
            raise InputError(f"{name}: expected true, false or 'unknown'")
    for name in OPTIONAL_TRISTATE_FIELDS:
        if name in case and (case[name] not in TRISTATE or
                             (isinstance(case[name], int) and not isinstance(case[name], bool))):
            raise InputError(f"{name}: expected true, false or 'unknown'")
    if type(case.get("reachability_verified")) is not bool:
        raise InputError("reachability_verified: expected boolean")
    if type(case.get("change_authorised")) is not bool:
        raise InputError("change_authorised: expected boolean")
    sev = case.get("severity_proxy_0_10")
    if type(sev) not in (int, float) or not math.isfinite(sev) or not 0 <= sev <= 10:
        raise InputError("severity_proxy_0_10: expected finite number in [0,10]")
    epss = case.get("epss_probability")
    if epss is not None and (type(epss) not in (int, float) or not math.isfinite(epss) or not 0 <= epss <= 1):
        raise InputError("epss_probability: expected null or finite number in [0,1]")
    controls = case.get("compensating_controls")
    if not isinstance(controls, list):
        raise InputError("compensating_controls: expected list")
    for i, control in enumerate(controls):
        if not isinstance(control, dict) or control.get("effectiveness") not in ("verified", "claimed", "unknown"):
            raise InputError(f"compensating_controls[{i}]: invalid effectiveness")
        for field in ("name", "evidence"):
            if not isinstance(control.get(field), str) or not control[field].strip():
                raise InputError(f"compensating_controls[{i}].{field}: expected nonempty string")
        if "attack_path_relevance" in control and control["attack_path_relevance"] not in ("relevant", "irrelevant", "unknown"):
            raise InputError(f"compensating_controls[{i}].attack_path_relevance: invalid value")
        if "control_type" in control and control["control_type"] not in ("network_isolation", "access_control", "monitoring", "other"):
            raise InputError(f"compensating_controls[{i}].control_type: invalid value")
        if "verification_as_of" in control:
            try:
                date.fromisoformat(control["verification_as_of"])
            except (ValueError, TypeError) as exc:
                raise InputError(f"compensating_controls[{i}].verification_as_of: invalid ISO date") from exc
    warnings = []
    if epss is None:
        warnings.append("EPSS_NOT_PROVIDED_OR_UNKNOWN")
    dt = case.get("threat_data_as_of")
    if dt is None:
        warnings.append("THREAT_DATA_DATE_MISSING")
    else:
        try:
            d = date.fromisoformat(dt)
            recorded = datetime.fromisoformat(case["recorded_at"].replace("Z", "+00:00")).date()
            if (recorded - d).days > 30:
                warnings.append("THREAT_DATA_OLDER_THAN_30_DAYS_RESEARCH_HEURISTIC")
            elif (recorded - d).days < 0:
                warnings.append("THREAT_DATA_DATE_AFTER_RECORDING")
        except (ValueError, TypeError) as exc:
            raise InputError("threat_data_as_of: expected ISO date or null") from exc
    if any(c["effectiveness"] != "verified" for c in controls):
        warnings.append("UNVERIFIED_COMPENSATING_CONTROL_CLAIMS")
    if case["reachability"] == "isolated_verified" and not case["reachability_verified"]:
        warnings.append("ISOLATION_NOT_VERIFIED")
    if case["kev"] == "unknown" or case["active_exploitation_reported"] == "unknown":
        warnings.append("EXPLOITATION_INTELLIGENCE_INCOMPLETE")
    return warnings


def validate_dataset(raw):
    if not isinstance(raw, dict) or not isinstance(raw.get("cases"), list) or not raw["cases"]:
        raise InputError("dataset must be an object with a nonempty cases list")
    seen = set()
    for case in raw["cases"]:
        validate_case(case)
        ident = case["case_id"]
        if ident in seen:
            raise InputError(f"duplicate case_id: {ident}")
        seen.add(ident)
    return raw["cases"]
