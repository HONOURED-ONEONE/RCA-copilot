
def architecture_flags(topo):
    roles = set(v.get("role") for v in topo["nodes"].values())
    return {
        "has_db": 1 if "db" in roles else 0,
        "has_cache": 1 if "cache" in roles else 0,
        "has_external": 1 if "external" in roles else 0,
        "has_dns": 1 if "dns" in roles else 0,
        "has_tls_boundary": 1 if "tls" in roles else 0,
    }


BASE_REGISTRY = [
    {"name": "Deploy regression", "requires": []},
    {"name": "DB pool exhaustion", "requires": ["db"]},
    {"name": "DNS resolution issue", "requires": ["dns"]},
    {"name": "TLS/certificate failure", "requires": ["tls"]},
    {"name": "Cache stampede / cache miss storm", "requires": ["cache"]},
    {"name": "External dependency degradation", "requires": ["external"]},
    {"name": "Traffic spike / overload", "requires": []},
    {"name": "Resource saturation (CPU/memory)", "requires": []},
]


def generate_candidates(topo, events, incident, strategy):
    flags = architecture_flags(topo)
    roles_present = set(v.get("role") for v in topo["nodes"].values())

    candidates = []
    for h in BASE_REGISTRY:
        req = set(h["requires"])
        if req.issubset(roles_present):
            candidates.append(h["name"])

    if strategy.get("add_overload_fallbacks"):
        if "Traffic spike / overload" not in candidates:
            candidates.append("Traffic spike / overload")
        if "Resource saturation (CPU/memory)" not in candidates:
            candidates.append("Resource saturation (CPU/memory)")

    return candidates, flags
