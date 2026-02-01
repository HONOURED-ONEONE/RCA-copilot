import time
import streamlit as st

from rca.loader import load_run
from rca.orchestrator import run_with_aogc

st.set_page_config(page_title="RCA Copilot (Demo)", layout="wide")

st.title("RCA Copilot — Live Demo (One Incident per Run)")

# Sidebar settings
st.sidebar.header("Settings")
current_dir = st.sidebar.text_input("Shared current/ path", "shared_demo_root/current")
poll_seconds = st.sidebar.slider("Poll interval (seconds)", 1, 5, 2)
auto_reload = st.sidebar.toggle("Auto reload", value=True)
model_path = st.sidebar.text_input("Policy model path", "policy/model.joblib")

# Session state
if "last_run_id" not in st.session_state:
    st.session_state.last_run_id = None
if "last_loaded_at" not in st.session_state:
    st.session_state.last_loaded_at = None
if "run_data" not in st.session_state:
    st.session_state.run_data = None
if "result_bundle" not in st.session_state:
    st.session_state.result_bundle = None


def do_load_and_run():
    run = load_run(current_dir)
    if run is None:
        st.session_state.run_data = None
        st.session_state.result_bundle = None
        return

    run_id = run["manifest"].get("run_id")
    if run_id != st.session_state.last_run_id:
        st.session_state.last_run_id = run_id
        st.session_state.last_loaded_at = time.strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.run_data = run
        st.session_state.result_bundle = run_with_aogc(run, model_path=model_path)


# Manual reload button
if st.sidebar.button("Reload now"):
    do_load_and_run()

# Auto reload
if auto_reload:
    time.sleep(poll_seconds)
    do_load_and_run()

# If no data yet
if st.session_state.run_data is None:
    st.warning("Waiting for TelemetryStorm to promote a run into current/ (manifest.json + READY)...")
    st.info(
        "Expected: shared_demo_root/current/manifest.json and shared_demo_root/current/READY\n\n"
        "Tip: Ensure TelemetryStorm uses atomic folder swap and writes manifest last."
    )
    st.stop()

run = st.session_state.run_data
manifest = run["manifest"]

# Header banner
colA, colB, colC, colD = st.columns([2, 2, 2, 2])
with colA:
    st.metric("run_id", manifest.get("run_id", "—"))
with colB:
    st.metric("scenario", manifest.get("scenario", "—"))
with colC:
    st.metric("variant", manifest.get("variant", "—"))
with colD:
    st.metric("last loaded", st.session_state.last_loaded_at or "—")

gaps = manifest.get("telemetry_gaps", [])
if gaps:
    st.caption(f"Telemetry gaps (by design): {', '.join(gaps)}")

# Stream counts quick view
stats = run.get("stats")
if stats:
    st.sidebar.subheader("TelemetryStorm stats.json")
    st.sidebar.json(stats)
else:
    st.sidebar.subheader("Stream counts (computed)")
    st.sidebar.write(
        {
            "alerts": len(run["alerts"]),
            "logs": len(run["logs"]),
            "metrics": len(run["metrics"]),
            "traces": len(run["traces"]),
            "changes": len(run["changes"]),
        }
    )

bundle = st.session_state.result_bundle
baseline = bundle["baseline"]
rerun = bundle.get("rerun")
final = bundle["final"]

tabs = st.tabs(["Final Output", "Baseline", "AOGC Rerun", "Telemetry Preview"])


def render_rca(result, title_prefix=""):
    left, right = st.columns([2, 3])
    with left:
        st.subheader(f"{title_prefix}Top‑3 RCA")
        for i, h in enumerate(result["top3"], start=1):
            st.write(f"**{i}. {h['name']}** — confidence: `{h['confidence']:.2f}`")
            if h.get("actions"):
                st.caption("Actions: " + " | ".join(h["actions"][:3]))

        st.subheader(f"{title_prefix}TSS")
        st.metric("Telemetry Sufficiency Score", f"{result['tss']:.3f}")
        if result["missing"]:
            st.caption("Missing/weak signals: " + ", ".join(result["missing"]))

        st.subheader(f"{title_prefix}Topology summary")
        st.write(result["topology_summary"])
        st.subheader(f"{title_prefix}Architecture flags")
        st.write(result["architecture_flags"])
        st.subheader(f"{title_prefix}Inventory")
        st.write(result["inventory"])

    with right:
        st.subheader(f"{title_prefix}MEPP (Minimal Evidence Proof Packs)")
        for pack in result["mepp"]:
            with st.expander(
                f"{pack['hypothesis']} (conf {pack['confidence']:.2f})", expanded=True
            ):
                st.caption(pack.get("recommended_action", ""))
                st.json(pack["minimal_evidence"])


with tabs[0]:
    st.subheader("Final (after AOGC if triggered)")
    render_rca(final)
    if bundle.get("action"):
        st.info(
            f"AOGC action chosen: **{bundle['action']}**  — kept: **{bundle['kept']}**"
        )
        st.write("Deltas:", bundle.get("deltas", {}))

with tabs[1]:
    st.subheader("Baseline run")
    render_rca(baseline, title_prefix="Baseline • ")

with tabs[2]:
    st.subheader("AOGC rerun (max_reruns = 1)")
    if rerun is None:
        st.success("AOGC did not trigger (TSS/confidence sufficient).")
    else:
        st.info(f"AOGC action chosen: **{bundle['action']}** — kept: **{bundle['kept']}**")
        st.write("Deltas:", bundle.get("deltas", {}))
        render_rca(rerun, title_prefix="Rerun • ")

with tabs[3]:
    st.subheader("Telemetry preview (raw counts + samples)")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("alerts", len(run["alerts"]))
    c2.metric("logs", len(run["logs"]))
    c3.metric("metrics", len(run["metrics"]))
    c4.metric("traces", len(run["traces"]))
    c5.metric("changes", len(run["changes"]))

    st.markdown("### Sample records")
    sample_n = st.slider("Sample size", 3, 30, 10)
    st.write("**alerts**")
    st.json(run["alerts"][:sample_n])
    st.write("**logs**")
    st.json(run["logs"][:sample_n])
    st.write("**metrics**")
    st.json(run["metrics"][:sample_n])
    st.write("**traces**")
    st.json(run["traces"][: min(sample_n, 5)])
    st.write("**changes**")
    st.json(run["changes"][:sample_n])
