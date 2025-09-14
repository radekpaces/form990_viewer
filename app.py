import glob
import json
import os
from flask import Flask, request, render_template
import xmltodict

app = Flask(__name__)

CONFIG_PATH = os.environ.get("CONFIG_PATH", "config.json")
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH) as f:
        config = json.load(f)
else:
    config = {}

FILTERABLE_ATTRIBUTES = set(config.get("filterable_attributes", []))


def load_records(directory="2024"):
    records = []
    for path in glob.glob(os.path.join(directory, "*.xml")):
        with open(path, "r", encoding="utf-8") as f:
            data = xmltodict.parse(f.read())
            records.append((os.path.basename(path), data))
    return records


def flatten_dict(d, parent_key="", sep="."):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


@app.route("/")
def index():
    raw_records = load_records()
    filters = {k: v for k, v in request.args.items() if k in FILTERABLE_ATTRIBUTES}
    processed = []
    for _, record in raw_records:
        flat = flatten_dict(record)
        if all(str(flat.get(attr, "")).lower() == val.lower() for attr, val in filters.items()):
            processed.append(flat)
        elif not filters:
            processed.append(flat)
    return render_template("index.html", records=processed, filterable=FILTERABLE_ATTRIBUTES)


if __name__ == "__main__":
    app.run(debug=True)
