
def build_mepp(top3, events, incident, topo, signals, max_items=6):
    logs = events["logs"]
    metrics = events["metrics"]
    traces = events.get("traces", [])
    changes = events["changes"]
    edges = topo.get("edges", [])

    def pick_logs(keys):
        out = []
        for l in logs:
            msg = (l.get("message") or "").lower()
            if any(k in msg for k in keys):
                out.append(
                    {
                        "type": "log",
                        "ts": str(l.get("ts")),
                        "service": l.get("service"),
                        "level": l.get("level"),
                        "message": l.get("message"),
                    }
                )
            if len(out) >= 2:
                break
        return out

    def pick_metrics(keys):
        out = []
        for m in metrics:
            name = (m.get("name") or "").lower()
            if any(k in name for k in keys):
                out.append(
                    {
                        "type": "metric",
                        "ts": str(m.get("ts")),
                        "service": m.get("service"),
                        "name": m.get("name"),
                        "value": m.get("value"),
                    }
                )
            if len(out) >= 2:
                break
        return out

    def pick_changes():
        return [
            {"type": "change", "ts": str(c.get("ts")), "service": c.get("service"), "change": c.get("raw")}
            for c in changes[:2]
        ]

    def pick_traces():
        return [
            {"type": "trace", "trace_id": t.get("trace_id"), "spans": t.get("spans")[:4]}
            for t in traces[:1]
        ]

    topo_ev = (
        [{"type": "topology", "edges": [{"src": e["src"], "dst": e["dst"], "conf": e["conf"]} for e in edges[:5]]}]
        if edges
        else []
    )

    packs = []
    for h in top3:
        name = h["name"].lower()
        evidence = []

        if "deploy" in name:
            evidence += pick_changes()
            evidence += pick_logs(["error", "exception", "null"])
        elif "db pool" in name:
            evidence += pick_metrics(["pool_wait", "connections"])
            evidence += pick_logs(["timeout", "connection", "too many"])
        elif "dns" in name:
            evidence += pick_logs(["dns", "resolve", "nxdomain", "no such host"])
        elif "tls" in name or "certificate" in name:
            evidence += pick_logs(["x509", "certificate", "tls", "ssl"])
        elif "cache" in name:
            evidence += pick_metrics(["cache_hit", "eviction"])
            evidence += pick_logs(["cache miss", "stampede", "redis"])
        elif "external" in name:
            evidence += pick_logs(["https://", "timeout", "upstream"])
        else:
            evidence += pick_logs(["timeout", "error"])
            evidence += pick_metrics(["latency", "error"])

        evidence += topo_ev
        evidence = evidence[:max_items]

        packs.append(
            {
                "hypothesis": h["name"],
                "confidence": h["confidence"],
                "recommended_action": " / ".join(h.get("actions", [])[:2]),
                "minimal_evidence": evidence,
            }
        )

    return packs
