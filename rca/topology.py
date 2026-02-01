import re
from collections import defaultdict

DB_HINTS = [
    "timeout acquiring connection",
    "too many clients",
    "jdbc",
    "pool_wait",
    "connections_in_use",
    "db ",
]
CACHE_HINTS = ["redis", "cache hit", "eviction", "cache miss", "stampede"]
DNS_HINTS = ["nxdomain", "no such host", "dns", "resolve", "resolver"]
TLS_HINTS = ["x509", "certificate", "tls handshake", "ssl"]


def infer_topology(events, incident, strategy):
    # Incident-scoped for production; PoC uses all events.
    nodes = {}
    edges = {}  # (src, dst) -> confidence
    edge_evidence = defaultdict(list)

    # Add services seen
    services = set([l["service"] for l in events["logs"]] + [m["service"] for m in events["metrics"]])
    for s in services:
        nodes[s] = {"role": "service", "confidence": 0.9}

    # Trace-first
    traces = events.get("traces", [])
    for tr in traces:
        for sp in tr.get("spans", []):
            svc = sp.get("service")
            parent = sp.get("parent")
            if svc:
                nodes.setdefault(svc, {"role": "service", "confidence": 0.8})
            if parent and svc:
                key = (parent, svc)
                edges[key] = max(edges.get(key, 0.0), 0.85)
                edge_evidence[key].append({"type": "trace", "trace_id": tr.get("trace_id")})

    # Fallback from logs hints
    for l in events["logs"]:
        msg = (l.get("message") or "").lower()
        src = l.get("service", "unknown")

        if any(h in msg for h in DB_HINTS):
            nodes["db"] = {"role": "db", "confidence": 0.8}
            edges[(src, "db")] = max(edges.get((src, "db"), 0.0), 0.65)
            edge_evidence[(src, "db")].append({"type": "log", "snippet": msg[:140]})

        if any(h in msg for h in CACHE_HINTS):
            nodes["cache"] = {"role": "cache", "confidence": 0.75}
            edges[(src, "cache")] = max(edges.get((src, "cache"), 0.0), 0.6)
            edge_evidence[(src, "cache")].append({"type": "log", "snippet": msg[:140]})

        if any(h in msg for h in DNS_HINTS):
            nodes["dns"] = {"role": "dns", "confidence": 0.7}
            edges[(src, "dns")] = max(edges.get((src, "dns"), 0.0), 0.55)
            edge_evidence[(src, "dns")].append({"type": "log", "snippet": msg[:140]})

        if any(h in msg for h in TLS_HINTS):
            nodes["tls_boundary"] = {"role": "tls", "confidence": 0.65}
            edges[(src, "tls_boundary")] = max(edges.get((src, "tls_boundary"), 0.0), 0.5)
            edge_evidence[(src, "tls_boundary")].append({"type": "log", "snippet": msg[:140]})

        # external host detection
        m = re.search(r"https?://([a-zA-Z0-9\.\-]+)", msg)
        if m:
            host = m.group(1)
            ext = f"external:{host}"
            nodes[ext] = {"role": "external", "confidence": 0.6}
            edges[(src, ext)] = max(edges.get((src, ext), 0.0), 0.5)
            edge_evidence[(src, ext)].append({"type": "log", "host": host})

    # Topology confidence summary
    if traces and edges:
        base_conf = 0.8
    elif edges:
        base_conf = 0.55
    else:
        base_conf = 0.35

    avg_edge_conf = (sum(edges.values()) / max(1, len(edges)))
    topo = {
        "nodes": nodes,
        "edges": [
            {"src": k[0], "dst": k[1], "conf": v, "evidence": edge_evidence[k]}
            for k, v in edges.items()
        ],
        "confidence": round(min(1.0, 0.5 * base_conf + 0.5 * avg_edge_conf), 3),
        "avg_edge_conf": round(avg_edge_conf, 3),
    }
    return topo
