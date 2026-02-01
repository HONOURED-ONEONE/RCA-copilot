ACTION_SPACE = [
    "A_TRACE_CAUSAL",
    "A_LOG_METRIC_CORR",
    "A_LOG_SIGNATURE_ONLY",
    "A_CHANGE_CENTRIC",
    "B_CORR_30M_2HOP_PRUNE_TRACE",
    "B_LOGSIG_30M_1HOP_ADD_OVERLOAD",
    "B_CHANGE_30M_PRIOR_DEPLOY",
    "B_TRACE_15M_1HOP_TOPO_WEIGHT",
    "C_LOOKBACK_30M",
    "C_NEIGHBORS_2HOP",
]


def apply_action_to_strategy(base_strategy: dict, action: str) -> dict:
    s = dict(base_strategy)

    s.setdefault("lookback_minutes", 15)
    s.setdefault("neighbor_hops", 1)
    s.setdefault("mode", "TRACE_CAUSAL")
    s.setdefault("weights_preset", "balanced")
    s.setdefault("prune_trace_dependent", False)
    s.setdefault("add_overload_fallbacks", False)
    s.setdefault("prior_boost", {})

    if action == "A_TRACE_CAUSAL":
        s["mode"] = "TRACE_CAUSAL"
    elif action == "A_LOG_METRIC_CORR":
        s["mode"] = "LOG_METRIC_CORRELATION"
    elif action == "A_LOG_SIGNATURE_ONLY":
        s["mode"] = "LOG_SIGNATURE_ONLY"
    elif action == "A_CHANGE_CENTRIC":
        s["mode"] = "CHANGE_CENTRIC"

    elif action == "B_CORR_30M_2HOP_PRUNE_TRACE":
        s["mode"] = "LOG_METRIC_CORRELATION"
        s["lookback_minutes"] = 30
        s["neighbor_hops"] = 2
        s["prune_trace_dependent"] = True
        s["weights_preset"] = "corr_heavy"

    elif action == "B_LOGSIG_30M_1HOP_ADD_OVERLOAD":
        s["mode"] = "LOG_SIGNATURE_ONLY"
        s["lookback_minutes"] = 30
        s["neighbor_hops"] = 1
        s["add_overload_fallbacks"] = True
        s["weights_preset"] = "log_heavy"

    elif action == "B_CHANGE_30M_PRIOR_DEPLOY":
        s["mode"] = "CHANGE_CENTRIC"
        s["lookback_minutes"] = 30
        s["prior_boost"] = {"deploy_regression": 0.15}

    elif action == "B_TRACE_15M_1HOP_TOPO_WEIGHT":
        s["mode"] = "TRACE_CAUSAL"
        s["lookback_minutes"] = 15
        s["neighbor_hops"] = 1
        s["weights_preset"] = "topology_heavy"

    elif action == "C_LOOKBACK_30M":
        s["lookback_minutes"] = 30
    elif action == "C_NEIGHBORS_2HOP":
        s["neighbor_hops"] = 2

    s["lookback_minutes"] = min(60, max(0, int(s["lookback_minutes"])))
    s["neighbor_hops"] = min(3, max(0, int(s["neighbor_hops"])))
    return s
