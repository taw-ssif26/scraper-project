import csv
import json
import os
from datetime import datetime
import config


def _ensure_output_dir():
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)


def _generate_filename(extension: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(config.OUTPUT_DIR, f"scraped_{timestamp}.{extension}")


def save_results(records: list[dict]) -> dict[str, str]:
    """
    Save extracted records to both CSV and JSON.
    Returns dict with paths: {"csv": "...", "json": "..."}
    Returns empty dict if no records to save.
    """
    if not records:
        print("[Output] No records to save.")
        return {}

    _ensure_output_dir()

    csv_path  = _generate_filename("csv")
    json_path = _generate_filename("json")

    # ── JSON ──────────────────────────────────────────────────────────────────
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    # ── CSV ───────────────────────────────────────────────────────────────────
    # Collect all keys that appear across all records (handles inconsistent fields)
    all_keys = []
    for record in records:
        for key in record.keys():
            if key not in all_keys:
                all_keys.append(key)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            # Fill missing keys with empty string
            row = {key: record.get(key, "") for key in all_keys}
            writer.writerow(row)

    print(f"[Output] Saved {len(records)} records → {csv_path}, {json_path}")
    return {"csv": csv_path, "json": json_path}
