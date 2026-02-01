
def compute_tss(events, topo, incident):
    logs = events["logs"]
    metrics = events["metrics"]
    traces = events.get("traces", [])
    changes = events["changes"]

    has_metrics = 1.0 if metrics else 0.0
    has_traces = 1.0 if traces else 0.0
    has_changes = 1.0 if changes else 0.0

    topo_conf = topo.get("confidence", 0.0)
    has_topology = 1.0 if topo_conf >= 0.5 else (0.5 if topo_conf > 0 else 0.0)

    # correlation quality in logs
    if logs:
        with_corr = sum(1 for l in logs if l.get("trace_id"))
        corr_ratio = with_corr / max(1, len(logs))
        logs_score = 1.0 if corr_ratio >= 0.3 else 0.5
    else:
        logs_score = 0.0

    tss = 0.25 * logs_score + 0.20 * has_metrics + 0.20 * has_traces + 0.20 * has_topology + 0.15 * has_changes
    tss = round(tss, 3)

    missing = []
    if not logs:
        missing.append("logs")
    elif logs_score < 1.0:
        missing.append("correlation_ids_in_logs")
    if not metrics:
        missing.append("key_metrics")
    if not traces:
        missing.append("distributed_traces")
    if topo_conf < 0.5:
        missing.append("service_topology_low_confidence")
    if not changes:
        missing.append("change_events")

    return tss, missing
