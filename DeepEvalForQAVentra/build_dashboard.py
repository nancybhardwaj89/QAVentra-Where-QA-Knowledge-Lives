"""Generates a self-contained HTML dashboard from the evaluation results.

Data is embedded directly in the HTML so the output is a single file you
can double-click — no local web server, no CORS issues, and it can be
emailed, committed as a build artifact, or screenshotted for a report.
"""

import json
import os
import sys

from framework import config

TEMPLATE_FILE = "dashboard_template.html"
OUTPUT_FILE = os.path.join(config.RESULTS_DIR, "dashboard.html")
RESULTS_FILE = os.path.join(config.RESULTS_DIR, "results.json")


def main():
    if not os.path.exists(TEMPLATE_FILE):
        print(f"Template not found: {TEMPLATE_FILE}")
        sys.exit(1)

    if not os.path.exists(RESULTS_FILE):
        print(f"No results found at {RESULTS_FILE}")
        print("Run the evaluation first:  pytest")
        sys.exit(1)

    with open(RESULTS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    with open(TEMPLATE_FILE, encoding="utf-8") as f:
        template = f.read()

    html = template.replace("__DASHBOARD_DATA__", json.dumps(data))

    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    totals = data.get("totals", {})
    print(f"Dashboard written to {OUTPUT_FILE}")
    print(
        f"  {totals.get('metrics', 0)} metrics · "
        f"{totals.get('evaluations', 0)} evaluations · "
        f"{totals.get('passed', 0)} passed, {totals.get('failed', 0)} failed"
    )
    print("Open it in your browser.")


if __name__ == "__main__":
    main()
