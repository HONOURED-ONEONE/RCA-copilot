from collections import Counter


def extract_signals(events, incident, topo, strategy):
    logs = events["logs"]
    metrics = events["metrics"]
    changes = events["changes"]

    # keyword signatures
    sigs = []
    for l in logs:
        msg = (l.get("message") or "").lower()
        if "timeout" in msg:
            sigs.append("timeout")
        if "pool" in msg or "connection" in msg:
            sigs.append("db_connection")
        if "dns" in msg or "resolve" in msg or "nxdomain" in msg:
            sigs.append("dns")
        if "x509" in msg or "certificate" in msg or "tls" in msg:
            sigs.append("tls")
        if "cache miss" in msg or "stampede" in msg or "redis" in msg:
            sigs.append("cache")

    sig_counts = Counter(sigs)

    # metric anomalies (simple thresholds; TelemetryStorm should emit clear spikes)
    anomalies = []
    for m in metrics:
        name = (m.get("name") or "").lower()
        val = m.get("value", 0.0)
        if "pool_wait" in name and val > 1.0:
            anomalies.append("db_pool_wait_high")
        if ("error" in name or "5xx" in name) and val > 0.05:
            anomalies.append("error_rate_high")
        if ("latency" in name or "p95" in name) and val > 1.0:
            anomalies.append("latency_high")
        if "cache_hit" in name and val < 0.5:
            anomalies.append("cache_hit_low")

    has_deploy = any(c.get("type") == "deploy" for c in changes)

    return {"signature_counts": dict(sig_counts), "anomalies": anomalies, "has_deploy": has_deploy}
