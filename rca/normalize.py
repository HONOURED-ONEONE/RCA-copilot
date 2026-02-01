from datetime import datetime, timezone


def parse_ts(ts: str):
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def normalize_logs(logs):
    out = []
    for l in logs:
        out.append(
            {
                "ts": parse_ts(l.get("ts")),
                "service": l.get("service", "unknown"),
                "level": l.get("level", "INFO"),
                "message": l.get("message", ""),
                "trace_id": l.get("trace_id") or l.get("correlation_id"),
                "raw": l,
            }
        )
    return out


def normalize_alerts(alerts):
    out = []
    for a in alerts:
        out.append(
            {
                "ts": parse_ts(a.get("ts")),
                "service": a.get("service", "unknown"),
                "severity": a.get("severity", "warning"),
                "name": a.get("name", "unknown"),
                "value": a.get("value"),
                "raw": a,
            }
        )
    return out


def normalize_metrics(metrics):
    out = []
    for m in metrics:
        out.append(
            {
                "ts": parse_ts(m.get("ts")),
                "service": m.get("service", "unknown"),
                "name": m.get("name", "unknown"),
                "value": float(m.get("value", 0.0)),
                "labels": m.get("labels", {}),
                "raw": m,
            }
        )
    return out


def normalize_traces(traces):
    # Expected TelemetryStorm format:
    # {"trace_id":"...","spans":[{"service":"api","parent":null},{"service":"db","parent":"api"}]}
    out = []
    for t in traces:
        out.append(
            {
                "ts": parse_ts(t.get("ts")),
                "trace_id": t.get("trace_id"),
                "spans": t.get("spans", []),
                "raw": t,
            }
        )
    return out


def normalize_changes(changes):
    out = []
    for c in changes:
        out.append(
            {
                "ts": parse_ts(c.get("ts")),
                "service": c.get("service", "unknown"),
                "type": c.get("type", "change"),
                "version": c.get("version"),
                "raw": c,
            }
        )
    return out


def normalize_all(run):
    return {
        "alerts": normalize_alerts(run["alerts"]),
        "logs": normalize_logs(run["logs"]),
        "metrics": normalize_metrics(run["metrics"]),
        "traces": normalize_traces(run.get("traces", [])),
        "changes": normalize_changes(run["changes"]),
        "truth": run.get("truth"),
        "manifest": run["manifest"],
    }
