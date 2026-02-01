# RCA Copilot (Demo)

## Run

```bash
cd ~/RCA-copilot
pip install -r requirements.txt
streamlit run app.py
```

## Expected input (from TelemetryStorm)

RCA Copilot watches a shared folder (default `shared_demo_root/current`).
TelemetryStorm should atomically swap a fully generated dataset into `current/`.

`current/` must contain:
- `READY` marker file
- `manifest.json` (written last)
- `alerts.jsonl`, `logs.jsonl`, `metrics.jsonl`, `changes.jsonl`
- `traces.jsonl` optional (variant dependent)

Optional:
- `truth.json` for accuracy display (not required)
- `stats.json` for quick UI info

## Policy model

If `policy/model.joblib` exists, AOGC uses it to choose one adaptation action and reruns once.
If missing, a rule-based fallback action is used so the demo still works.
