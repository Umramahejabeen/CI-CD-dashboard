"""
CI/CD Status Dashboard - Frontend
Calls the backend API and renders HTML dashboards.
"""

import os
import requests
from flask import Flask, render_template

app = Flask(__name__)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:5000")


@app.route("/")
def dashboard():
    try:
        jobs = requests.get(f"{BACKEND_URL}/api/jobs", timeout=10).json()
        stats = requests.get(f"{BACKEND_URL}/api/stats", timeout=10).json()
    except requests.exceptions.RequestException:
        jobs, stats = [], {}

    return render_template("index.html", jobs=jobs, stats=stats)


@app.route("/job/<job_name>")
def job_detail(job_name):
    try:
        builds = requests.get(f"{BACKEND_URL}/api/builds/{job_name}", timeout=10).json()
    except requests.exceptions.RequestException:
        builds = []

    return render_template("job_detail.html", job_name=job_name, builds=builds)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
