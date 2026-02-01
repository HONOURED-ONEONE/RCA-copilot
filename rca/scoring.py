
def score_hypotheses(candidates, signals, topo, events, incident, strategy):
    sig = signals["signature_counts"]
    anomalies = set(signals["anomalies"])
    has_deploy = signals["has_deploy"]

    # evidence diversity
    evidence_types = 0
    if events["logs"]:
        evidence_types += 1
    if events["metrics"]:
        evidence_types += 1
    if events.get("traces"):
        evidence_types += 1
    if events["changes"]:
        evidence_types += 1
    diversity = min(1.0, evidence_types / 3.0)

    topo_conf = topo.get("confidence", 0.4)

    scored = []
    for h in candidates:
        base = 0.1
        name = h.lower()

        if "deploy regression" in name:
            base += 0.45 if has_deploy else 0.05
            base += 0.15 if ("error_rate_high" in anomalies or "latency_high" in anomalies) else 0.0

        if "db pool" in name:
            base += 0.35 if "db_pool_wait_high" in anomalies else 0.05
            base += 0.25 if sig.get("timeout", 0) > 0 else 0.05
            base += 0.15 if sig.get("db_connection", 0) > 0 else 0.0

        if "dns" in name:
            base += 0.5 if sig.get("dns", 0) > 0 else 0.05

        if "tls" in name or "certificate" in name:
            base += 0.55 if sig.get("tls", 0) > 0 else 0.05

        if "cache stampede" in name:
            base += 0.35 if "cache_hit_low" in anomalies else 0.05
            base += 0.25 if sig.get("cache", 0) > 0 else 0.05

        if "external dependency" in name:
            base += 0.25 if topo_conf > 0.55 else 0.05
            base += 0.15 if "latency_high" in anomalies else 0.0

        if "traffic spike" in name or "overload" in name:
            base += 0.2 if ("latency_high" in anomalies and "error_rate_high" in anomalies) else 0.05

        if "resource saturation" in name:
            base += 0.15 if "latency_high" in anomalies else 0.05

        conf = min(1.0, base + 0.2 * diversity + 0.15 * topo_conf)
        scored.append((h, conf))

    scored.sort(key=lambda x: x[1], reverse=True)
    top3 = scored[:3]

    def actions_for(hname):
        hname = hname.lower()
        if "db pool" in hname:
            return ["Check pool limits", "Inspect slow queries", "Look for connection leaks"]
        if "deploy" in hname:
            return ["Check recent deploy", "Rollback if needed", "Compare error budget"]
        if "dns" in hname:
            return ["Check resolver health", "Validate DNS latency", "Mitigate with caching"]
        if "tls" in hname or "certificate" in hname:
            return ["Check cert expiry", "Verify TLS chain", "Rotate cert/secret"]
        if "cache" in hname:
            return ["Check cache hit ratio", "Enable request coalescing", "Warm cache"]
        if "external" in hname:
            return ["Check provider status", "Tune timeouts/retries", "Enable circuit breaker"]
        return ["Inspect dashboards", "Check saturation", "Review recent changes"]

    return [{"name": n, "confidence": float(c), "actions": actions_for(n)} for n, c in top3]
