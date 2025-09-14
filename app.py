import glob
import json
import os
from flask import Flask, request, render_template
import xmltodict

app = Flask(__name__)

# Base directory of this file to allow running from any location
BASE_DIR = os.path.dirname(__file__)

CONFIG_PATH = os.environ.get(
    "CONFIG_PATH", os.path.join(BASE_DIR, "config.json")
)

if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH) as f:
        config = json.load(f)
else:
    config = {}

FILTERABLE_ATTRIBUTES = config.get("filterable_attributes", {})


def load_records(directory=os.path.join(BASE_DIR, "2024")):
    """Load XML files and return a list of (filename, data) tuples."""
    records = []
    for path in glob.glob(os.path.join(directory, "*.xml")):
        with open(path, "r", encoding="utf-8") as f:
            data = xmltodict.parse(f.read())
            records.append((os.path.basename(path), data))
    return records

def flatten_dict(obj, parent_key="", sep="."):
    items = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.startswith("@"):  # skip XML attributes
                continue
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            items.extend(flatten_dict(v, new_key, sep=sep).items())
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_key = f"{parent_key}[{i}]"
            items.extend(flatten_dict(v, new_key, sep=sep).items())
    else:
        items.append((parent_key, obj))
    return dict(items)

def aggregate_numeric_fields(records):
    """Compute min, max, and average for numeric fields across records."""
    stats = {}
    for rec in records:
        for key, value in rec.items():
            if key == "filename" or not key.startswith("Return.ReturnData.IRS990PF."):
                continue
            try:
                num = float(value)
            except (TypeError, ValueError):
                continue
            if key not in stats:
                stats[key] = {"min": num, "max": num, "sum": num, "count": 1}
            else:
                s = stats[key]
                s["min"] = min(s["min"], num)
                s["max"] = max(s["max"], num)
                s["sum"] += num
                s["count"] += 1
    # finalize averages
    return {
        k: {"min": v["min"], "max": v["max"], "avg": v["sum"] / v["count"]}
        for k, v in stats.items()
    }


@app.route("/")
def index():
    raw_records = load_records()

    # Ignore empty filter values to allow querying by any combination
    filters = {
        k: v
        for k, v in request.args.items()
        if k in FILTERABLE_ATTRIBUTES and v.strip()
    }
    processed = []
    for filename, record in raw_records:
        flat = flatten_dict(record)

        if flat.get("Return.ReturnHeader.ReturnTypeCd") != "990PF":
            continue

        flat["filename"] = filename
        matches = all(
            str(flat.get(FILTERABLE_ATTRIBUTES[attr], "")).lower() == val.lower()
            for attr, val in filters.items()
        )
        if matches or not filters:
            processed.append(flat)

    stats = aggregate_numeric_fields(processed)
    return render_template(
        "index.html", stats=stats, filterable=FILTERABLE_ATTRIBUTES.keys()

    )


if __name__ == "__main__":
    # Enable debug mode when FLASK_DEBUG is truthy
    debug_flag = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(debug=debug_flag)

