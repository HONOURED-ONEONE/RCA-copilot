from rca.topology import infer_topology
from rca.hypotheses import generate_candidates
from rca.signals import extract_signals
from rca.scoring import score_hypotheses
from rca.tss import compute_tss
from rca.mepp import build_mepp
from rca.utils import inventory_from_run


def run_pipeline_once(events, incident, strategy):
    topo = infer_topology(events, incident, strategy=strategy)
    candidates, arch_flags = generate_candidates(topo, events, incident, strategy=strategy)

    signals = extract_signals(events, incident, topo, strategy=strategy)
    top3 = score_hypotheses(candidates, signals, topo, events, incident, strategy=strategy)

    tss, missing = compute_tss(events, topo, incident)
    inv = inventory_from_run(events, incident, topo)

    mepp = build_mepp(top3, events, incident, topo, signals)

    return {
        "run_id": events["manifest"].get("run_id"),
        "incident_id": incident["id"],
        "mode": strategy.get("mode"),
        "top3": top3,
        "tss": tss,
        "missing": missing,
        "inventory": inv,
        "topology_summary": {
            "confidence": topo.get("confidence", 0.0),
            "edge_count": len(topo.get("edges", [])),
            "avg_edge_conf": topo.get("avg_edge_conf", 0.0),
        },
        "architecture_flags": arch_flags,
        "mepp": mepp,
        "debug": {"strategy": strategy, "signals": signals},
    }
