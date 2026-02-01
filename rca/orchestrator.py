import os

import joblib
import pandas as pd

from rca.actions import apply_action_to_strategy
from rca.features import extract_policy_features
from rca.incidents import build_one_incident
from rca.normalize import normalize_all
from rca.pipeline_core import run_pipeline_once

TSS_TH = 0.65
CONF_TH = 0.55
MIN_DELTA = 0.05

FEATURE_COLS = [
    "tss",
    "missing_traces",
    "missing_corr_ids",
    "missing_metrics",
    "missing_changes",
    "topology_conf",
    "log_count",
    "metric_count",
    "trace_count",
    "change_count",
    "services_impacted",
    "evidence_diversity",
    "top1_conf",
    "top2_conf",
    "top3_conf",
    "conf_gap12",
    "conf_gap23",
    "conf_entropy",
    "has_db",
    "has_cache",
    "has_external",
    "has_dns",
    "has_tls_boundary",
    "edge_count",
    "avg_edge_conf",
]


def should_adapt(result):
    top1 = result["top3"][0]["confidence"] if result["top3"] else 0.0
    return (result["tss"] < TSS_TH) or (top1 < CONF_TH)


def fallback_action(result):
    # Demo-safe fallback if model is missing
    missing = set(result.get("missing", []))
    if "distributed_traces" in missing and "correlation_ids_in_logs" in missing:
        return "B_LOGSIG_30M_1HOP_ADD_OVERLOAD"
    if "distributed_traces" in missing:
        return "B_CORR_30M_2HOP_PRUNE_TRACE"
    if "change_events" in missing:
        return "A_LOG_METRIC_CORR"
    return "C_LOOKBACK_30M"


def load_policy(model_path):
    if not model_path or not os.path.exists(model_path):
        return None
    bundle = joblib.load(model_path)
    return bundle.get("model"), bundle.get("feature_cols", FEATURE_COLS)


def run_with_aogc(run_data: dict, model_path: str):
    events = normalize_all(run_data)
    incident = build_one_incident(events)

    base_strategy = {
        "mode": "TRACE_CAUSAL",
        "lookback_minutes": 15,
        "neighbor_hops": 1,
        "weights_preset": "balanced",
        "prune_trace_dependent": False,
        "add_overload_fallbacks": False,
        "prior_boost": {},
    }

    r0 = run_pipeline_once(events, incident, base_strategy)
    bundle = {
        "baseline": r0,
        "rerun": None,
        "final": r0,
        "action": None,
        "kept": "baseline",
        "deltas": {},
    }

    if not should_adapt(r0):
        return bundle

    model_info = load_policy(model_path)
    if model_info is None:
        action = fallback_action(r0)
    else:
        model, cols = model_info
        feats = extract_policy_features(r0)
        X = pd.DataFrame([[feats.get(c, 0) for c in cols]], columns=cols)
        action = model.predict(X)[0]

    s1 = apply_action_to_strategy(base_strategy, action)
    r1 = run_pipeline_once(events, incident, s1)

    bundle["rerun"] = r1
    bundle["action"] = action

    b1 = r0["top3"][0]["confidence"] if r0["top3"] else 0.0
    a1 = r1["top3"][0]["confidence"] if r1["top3"] else 0.0
    bundle["deltas"] = {
        "delta_top1_conf": round(a1 - b1, 3),
        "delta_tss": round(r1["tss"] - r0["tss"], 3),
        "delta_diversity": r1["inventory"]["evidence_diversity"] - r0["inventory"]["evidence_diversity"],
    }

    if (a1 - b1) >= MIN_DELTA:
        bundle["final"] = r1
        bundle["kept"] = "rerun"

    return bundle
