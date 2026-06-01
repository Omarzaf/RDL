"""
01_load_and_audit.py
Loads all Raw Data JSON files and produces a schema/quality audit report.
"""
import json, os
import logging
from pathlib import Path

from config import RAW_DATA_DIR, PROCESSED_DIR

RAW = RAW_DATA_DIR
OUT = PROCESSED_DIR
OUT.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

if not RAW.exists():
    raise FileNotFoundError(f"Raw data directory does not exist: {RAW}")

FILES = {
    "stats":           "stats.json",
    "trends":          "trends.json",
    "industries":      "industries.json",
    "top_firms":       "top-firms.json",
    "top_clients":     "top-clients.json",
    "top_lobbyists":   "top-lobbyists.json",
    "revolving_door":  "revolving-door.json",
    "network":         "network-analysis.json",
    "firm_conc":       "firm-concentration.json",
    "gov_entities":    "gov-entities.json",
    "filing_activity": "filing-activity.json",
    "lvc":             "lobbying-vs-contracts.json",
    "text_analysis":   "text-analysis.json",
}

report = {}
raw_payloads = {}
for key, fname in FILES.items():
    path = RAW / fname
    with open(path) as f:
        data = json.load(f)
    raw_payloads[key] = data
    if isinstance(data, list):
        count = len(data)
        fields = list(data[0].keys()) if data else []
        null_rates = {}
        for field in fields:
            nulls = sum(1 for r in data if r.get(field) is None)
            null_rates[field] = round(nulls / count, 3)
    elif isinstance(data, dict):
        count = 1
        fields = list(data.keys())
        null_rates = {}
    report[key] = {"file": fname, "record_count": count, "fields": fields, "null_rates": null_rates}
    print(f"  {key}: {count} records, fields: {fields[:5]}")

placeholder_fields = {}
for key, data in raw_payloads.items():
    if not isinstance(data, list) or not data:
        continue
    fields = list(data[0].keys())
    zero_fields = []
    for field in fields:
        values = [row.get(field) for row in data if isinstance(row, dict) and field in row]
        if values and all(isinstance(value, (int, float)) and value == 0 for value in values):
            zero_fields.append(field)
    if zero_fields:
        placeholder_fields[key] = zero_fields
        report[key]["placeholder_fields"] = zero_fields

stats = raw_payloads.get("stats", {})
trends = raw_payloads.get("trends", [])
if isinstance(stats, dict) and isinstance(trends, list) and trends:
    max_trend_year = max(int(row.get("year", 0) or 0) for row in trends)
    stats_latest_year = int(stats.get("latestYear", 0) or 0)
    corrected_stats = dict(stats)
    if stats_latest_year != max_trend_year:
        logging.critical(
            "stats.latestYear (%s) does not match max trends year (%s); corrected processed copy only.",
            stats_latest_year,
            max_trend_year,
        )
        corrected_stats["latestYear"] = max_trend_year
        report["stats"]["latestYear_correction"] = {
            "raw_latestYear": stats_latest_year,
            "corrected_latestYear": max_trend_year,
        }
    with open(OUT / "stats.corrected.json", "w") as f:
        json.dump(corrected_stats, f, indent=2)

with open(OUT / "placeholder_fields.json", "w") as f:
    json.dump(placeholder_fields, f, indent=2)

with open(OUT / "audit_report.json", "w") as f:
    json.dump(report, f, indent=2)
print(f"\nAudit saved to {OUT / 'audit_report.json'}")
