import json
from pathlib import Path


def read_jsonl(path: Path):
    if path is None or not path.exists():
        return []
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def load_run(current_dir: str):
    cur = Path(current_dir)
    manifest_path = cur / "manifest.json"
    ready_path = cur / "READY"

    if not manifest_path.exists() or not ready_path.exists():
        return None

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    streams = manifest.get("streams", {})

    def stream_path(key):
        fn = streams.get(key)
        return (cur / fn) if fn else None

    run = {
        "manifest": manifest,
        "alerts": read_jsonl(stream_path("alerts")),
        "logs": read_jsonl(stream_path("logs")),
        "metrics": read_jsonl(stream_path("metrics")),
        "traces": read_jsonl(stream_path("traces")) if stream_path("traces") else [],
        "changes": read_jsonl(stream_path("changes")),
        "truth": None,
        "stats": None,
    }

    truth_p = stream_path("truth")
    if truth_p and truth_p.exists():
        run["truth"] = json.loads(truth_p.read_text(encoding="utf-8"))

    stats_p = cur / "stats.json"
    if stats_p.exists():
        run["stats"] = json.loads(stats_p.read_text(encoding="utf-8"))

    return run
