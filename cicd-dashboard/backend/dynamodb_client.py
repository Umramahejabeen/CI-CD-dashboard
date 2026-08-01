"""
Wrapper around boto3 DynamoDB operations.
Uses the IAM Role attached to the EC2 instance for credentials —
no access keys are hardcoded anywhere in this file.
"""

import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from collections import defaultdict


class DynamoDBClient:
    def __init__(self, region, table_name):
        self.dynamodb = boto3.resource("dynamodb", region_name=region)
        self.table = self.dynamodb.Table(table_name)

    def put_build(self, item):
        """
        Upserts a build record.
        Primary key design:
          - Partition key: job_name (string)
          - Sort key: build_number (number)
        """
        clean_item = {
            "job_name": item["job_name"],
            "build_number": int(item["build_number"]),
            "status": item["status"],
            "timestamp": int(item["timestamp"]) if item["timestamp"] else 0,
            "duration_ms": int(item["duration_ms"]),
            "url": item["url"],
        }
        self.table.put_item(Item=clean_item)

    def get_builds_for_job(self, job_name, limit=20):
        response = self.table.query(
            KeyConditionExpression=Key("job_name").eq(job_name),
            ScanIndexForward=False,  # newest first
            Limit=limit,
        )
        return response.get("Items", [])

    def get_jobs_summary(self):
        """
        Scans the table and returns, per job, the latest build status.
        (For a small student project, a scan is fine. At scale you'd
        maintain a separate 'latest_build' table instead.)
        """
        response = self.table.scan()
        items = response.get("Items", [])

        latest_per_job = {}
        for item in items:
            job = item["job_name"]
            if job not in latest_per_job or item["build_number"] > latest_per_job[job]["build_number"]:
                latest_per_job[job] = item

        return list(latest_per_job.values())

    def get_aggregate_stats(self):
        response = self.table.scan()
        items = response.get("Items", [])

        total_builds = len(items)
        success_count = sum(1 for i in items if i["status"] == "SUCCESS")
        failure_count = sum(1 for i in items if i["status"] == "FAILURE")
        durations = [int(i["duration_ms"]) for i in items if i.get("duration_ms")]
        avg_duration_ms = sum(durations) / len(durations) if durations else 0

        return {
            "total_builds": total_builds,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": round((success_count / total_builds) * 100, 2) if total_builds else 0,
            "avg_duration_ms": round(avg_duration_ms, 2),
        }
