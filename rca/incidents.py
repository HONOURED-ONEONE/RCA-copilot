
def build_one_incident(events):
    """For demo: one incident per run.

    Derives incident window from alerts. If no alerts, uses services seen in logs.
    """
    alerts = events["alerts"]
    if alerts:
        alerts_sorted = sorted([a for a in alerts if a["ts"]], key=lambda x: x["ts"])
        start_dt = alerts_sorted[0]["ts"]
        end_dt = alerts_sorted[-1]["ts"]
        services = sorted(set(a["service"] for a in alerts_sorted))
    else:
        start_dt = None
        end_dt = None
        services = sorted(set(l["service"] for l in events["logs"]))

    return {"id": "INC-001", "start": start_dt, "end": end_dt, "services": services}
