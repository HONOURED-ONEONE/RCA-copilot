
def inventory_from_run(events, incident, topo):
    log_count = len(events["logs"])
    metric_count = len(events["metrics"])
    trace_count = len(events.get("traces", []))
    change_count = len(events["changes"])

    services_impacted = len(
        set([l["service"] for l in events["logs"]] + [m["service"] for m in events["metrics"]])
    )

    evidence_diversity = sum(
        [
            1 if log_count else 0,
            1 if metric_count else 0,
            1 if trace_count else 0,
            1 if change_count else 0,
        ]
    )

    return {
        "log_count": log_count,
        "metric_count": metric_count,
        "trace_count": trace_count,
        "change_count": change_count,
        "services_impacted": services_impacted,
        "evidence_diversity": evidence_diversity,
    }
