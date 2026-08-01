"""
CI/CD Status Dashboard - Backend API
Fetches build data from Jenkins and stores/reads it from DynamoDB.
"""

import os
import logging
from flask import Flask, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler

from jenkins_client import JenkinsClient
from dynamodb_client import DynamoDBClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ---- Config (from environment variables, set in docker-compose.yml) ----
JENKINS_URL = os.environ.get("JENKINS_URL", "http://host.docker.internal:8080")
JENKINS_USER = os.environ.get("JENKINS_USER", "admin")
JENKINS_API_TOKEN = os.environ.get("JENKINS_API_TOKEN", "")
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "cicd_builds")
SYNC_INTERVAL_SECONDS = int(os.environ.get("SYNC_INTERVAL_SECONDS", "60"))

jenkins_client = JenkinsClient(JENKINS_URL, JENKINS_USER, JENKINS_API_TOKEN)
db_client = DynamoDBClient(AWS_REGION, DYNAMODB_TABLE)


# ---------------------------------------------------------------------
# Core sync logic: pull latest builds from Jenkins, store in DynamoDB
# ---------------------------------------------------------------------
def sync_jenkins_data():
    """Pulls all jobs + their recent builds from Jenkins and upserts into DynamoDB."""
    try:
        jobs = jenkins_client.get_all_jobs()
        logger.info(f"Found {len(jobs)} Jenkins jobs")

        for job in jobs:
            job_name = job["name"]
            builds = jenkins_client.get_job_builds(job_name)

            for build in builds:
                item = {
                    "job_name": job_name,
                    "build_number": build["number"],
                    "status": build.get("result") or "IN_PROGRESS",
                    "timestamp": build.get("timestamp"),
                    "duration_ms": build.get("duration", 0),
                    "url": build.get("url", ""),
                }
                db_client.put_build(item)

        logger.info("Sync completed successfully")
    except Exception as e:
        logger.error(f"Sync failed: {e}")


# ---------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/sync", methods=["POST"])
def trigger_sync():
    """Manually trigger a sync from Jenkins -> DynamoDB."""
    sync_jenkins_data()
    return jsonify({"message": "Sync triggered"}), 200


@app.route("/api/jobs", methods=["GET"])
def list_jobs():
    """Returns distinct job names with their latest build status."""
    jobs_summary = db_client.get_jobs_summary()
    return jsonify(jobs_summary), 200


@app.route("/api/builds/<job_name>", methods=["GET"])
def get_builds(job_name):
    """Returns build history for a specific job."""
    limit = int(request.args.get("limit", 20))
    builds = db_client.get_builds_for_job(job_name, limit=limit)
    return jsonify(builds), 200


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Returns aggregate stats: total builds, success rate, avg duration, etc."""
    stats = db_client.get_aggregate_stats()
    return jsonify(stats), 200


# ---------------------------------------------------------------------
# Background scheduler: auto-sync every N seconds
# ---------------------------------------------------------------------
scheduler = BackgroundScheduler()
scheduler.add_job(sync_jenkins_data, "interval", seconds=SYNC_INTERVAL_SECONDS)
scheduler.start()

if __name__ == "__main__":
    # Run one sync immediately on startup
    sync_jenkins_data()
    app.run(host="0.0.0.0", port=5000, debug=False)
