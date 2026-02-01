import math


def _entropy(vals):
    s = sum(vals) + 1e-9
    p = [v / s for v in vals]
    return -sum(pi * math.log(pi + 1e-9) for pi in p)


def extract_policy_features(rca_result: dict) -> dict:
    top3 = rca_result["top3"]
    c1 = top3[0]["confidence"] if len(top3) > 0 else 0.0
    c2 = top3[1]["confidence"] if len(top3) > 1 else 0.0
    c3 = top3[2]["confidence"] if len(top3) > 2 else 0.0

    missing = set(rca_result.get("missing", []))
    inv = rca_result.get("inventory", {})
    topo = rca_result.get("topology_summary", {})
    arch = rca_result.get("architecture_flags", {})

    return {
        "tss": float(rca_result.get("tss", 0.0)),
        "missing_traces": 1 if "distributed_traces" in missing else 0,
        "missing_corr_ids": 1 if "correlation_ids_in_logs" in missing else 0,
        "missing_metrics": 1 if "key_metrics" in missing else 0,
        "missing_changes": 1 if "change_events" in missing else 0,
        "topology_conf": float(topo.get("confidence", 0.0)),

        "log_count": int(inv.get("log_count", 0)),
        "metric_count": int(inv.get("metric_count", 0)),
        "trace_count": int(inv.get("trace_count", 0)),
        "change_count": int(inv.get("change_count", 0)),
        "services_impacted": int(inv.get("services_impacted", 0)),
        "evidence_diversity": int(inv.get("evidence_diversity", 0)),

        "top1_conf": float(c1),
        "top2_conf": float(c2),
        "top3_conf": float(c3),
        "conf_gap12": float(c1 - c2),
        "conf_gap23": float(c2 - c3),
        "conf_entropy": float(_entropy([c1, c2, c3])),

        "has_db": int(arch.get("has_db", 0)),
        "has_cache": int(arch.get("has_cache", 0)),
        "has_external": int(arch.get("has_external", 0)),
        "has_dns": int(arch.get("has_dns", 0)),
        "has_tls_boundary": int(arch.get("has_tls_boundary", 0)),

        "edge_count": int(topo.get("edge_count", 0)),
        "avg_edge_conf": float(topo.get("avg_edge_conf", 0.0)),
    }
