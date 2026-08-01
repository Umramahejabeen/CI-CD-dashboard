"""
Thin wrapper around the Jenkins REST API using plain 'requests'
(avoids needing the python-jenkins package, keeps it dependency-light).
"""

import requests
from requests.auth import HTTPBasicAuth


class JenkinsClient:
    def __init__(self, base_url, user, api_token):
        self.base_url = base_url.rstrip("/")
        self.auth = HTTPBasicAuth(user, api_token)

    def get_all_jobs(self):
        """Returns a list of all jobs configured in Jenkins."""
        url = f"{self.base_url}/api/json?tree=jobs[name,url]"
        resp = requests.get(url, auth=self.auth, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("jobs", [])

    def get_job_builds(self, job_name, limit=10):
        """Returns recent builds for a given job with status/duration/timestamp."""
        url = (
            f"{self.base_url}/job/{job_name}/api/json"
            f"?tree=builds[number,result,timestamp,duration,url]{{0,{limit}}}"
        )
        resp = requests.get(url, auth=self.auth, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("builds", [])
