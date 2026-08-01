# CI/CD Status Dashboard

A "DevOps tool for DevOps" project — a live dashboard that pulls build history and
status directly from your Jenkins server via its REST API, stores it in DynamoDB,
and displays pass/fail trends, success rates, and build durations on a web dashboard.

## Architecture

```
GitHub Repo (push) --webhook--> Jenkins (Windows)
                                     |
                                     |  build & push images
                                     v
                              Docker Hub (image registry)
                                     |
                                     |  ssh deploy
                                     v
                        EC2 Instance (Docker host)
                        +-------------------------+
                        |  backend container       |  <-- polls Jenkins API,
                        |  (Flask API, port 5000)  |      writes to DynamoDB
                        |                           |
                        |  frontend container       |  <-- calls backend API,
                        |  (Flask + Jinja2, 8000)  |      renders dashboard
                        +-------------------------+
                                     |
                              IAM Role (attached to EC2)
                                     |
                                     v
                              DynamoDB Table (cicd_builds)
```

## Tech Stack

- **Backend:** Python, Flask, boto3, APScheduler
- **Frontend:** Python, Flask, Jinja2, Chart.js
- **Database:** AWS DynamoDB
- **Compute:** AWS EC2 (Docker host)
- **Security:** IAM Role (no hardcoded AWS credentials)
- **Containerization:** Docker, Docker Compose
- **CI/CD:** Jenkins (on Windows) + GitHub Webhook
- **Registry:** Docker Hub

## Project Structure

```
cicd-dashboard/
├── backend/
│   ├── app.py                 # Flask API, scheduler, routes
│   ├── jenkins_client.py      # Jenkins REST API wrapper
│   ├── dynamodb_client.py     # boto3 DynamoDB wrapper
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app.py                 # Flask app rendering dashboard
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── templates/
│   │   ├── index.html
│   │   └── job_detail.html
│   └── static/css/style.css
├── docker-compose.yml
├── Jenkinsfile
├── .env.example
├── .gitignore
└── README.md
```

---

## Step-by-Step Setup Guide

### Part 1 — AWS Setup

**1. Create a DynamoDB table**
1. Go to AWS Console → DynamoDB → Create table
2. Table name: `cicd_builds`
3. Partition key: `job_name` (String)
4. Sort key: `build_number` (Number)
5. Use default settings (on-demand capacity) → Create table

**2. Create an IAM Role for EC2**
1. Go to IAM → Roles → Create role
2. Trusted entity: **AWS service** → **EC2**
3. Attach a custom policy (create it under IAM → Policies) with:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "dynamodb:PutItem",
           "dynamodb:GetItem",
           "dynamodb:Query",
           "dynamodb:Scan"
         ],
         "Resource": "arn:aws:dynamodb:*:*:table/cicd_builds"
       }
     ]
   }
   ```
4. Name the role e.g. `cicd-dashboard-ec2-role`
5. Create the role

**3. Launch an EC2 instance**
1. EC2 → Launch instance
2. AMI: Ubuntu 22.04 LTS
3. Instance type: t2.micro (free tier) or t2.small if available
4. Under **IAM instance profile**, attach the role you just created (`cicd-dashboard-ec2-role`)
5. Security group — open these inbound ports:
   - 22 (SSH) — your IP only
   - 5000 (backend API) — your IP or 0.0.0.0/0 for testing
   - 8000 (frontend dashboard) — 0.0.0.0/0
6. Launch and download the `.pem` key file
7. SSH into it and install Docker:
   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose-plugin
   sudo usermod -aG docker $USER
   newgrp docker
   docker --version
   docker compose version
   ```

---

### Part 2 — Jenkins Setup (Windows)

**1. Install Jenkins**
- Download from https://www.jenkins.io/download/ (Windows installer)
- Install and start it — accessible at `http://localhost:8080`

**2. Install required plugins**
Go to *Manage Jenkins → Plugins → Available plugins*, install:
- Docker Pipeline
- SSH Agent Plugin
- GitHub Integration Plugin
- Credentials Binding Plugin

**3. Generate a Jenkins API token (for the dashboard backend to read build data)**
1. Click your username (top-right) → Configure
2. Under **API Token**, click **Add new Token** → Generate
3. Copy the token — you'll need it for `JENKINS_API_TOKEN`

**4. Add credentials in Jenkins**
Go to *Manage Jenkins → Credentials → System → Global credentials → Add Credentials*
- **Docker Hub:** Username/password type, ID = `dockerhub-creds`
- **EC2 SSH key:** SSH Username with private key type, ID = `ec2-ssh-key`
  (paste in the contents of your `.pem` file)

**5. Create the Pipeline job**
1. New Item → Pipeline → name it `cicd-dashboard-pipeline`
2. Under **Build Triggers**, check **GitHub hook trigger for GITScm polling**
3. Under **Pipeline**, choose **Pipeline script from SCM** → Git → paste your GitHub repo URL → Script Path: `Jenkinsfile`
4. Save

---

### Part 3 — GitHub Setup

**1. Push your project to GitHub**
```bash
cd cicd-dashboard
git init
git add .
git commit -m "Initial commit: CI/CD dashboard project"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/cicd-dashboard.git
git push -u origin main
```

**2. Expose Jenkins to the internet (so GitHub can reach the webhook)**
Since Jenkins runs on your local Windows machine, GitHub's servers can't reach
`localhost:8080` directly. Use **ngrok**:
```bash
ngrok http 8080
```
Copy the generated `https://xxxx.ngrok-free.app` URL.

**3. Add the webhook in GitHub**
1. Go to your repo → Settings → Webhooks → Add webhook
2. Payload URL: `https://xxxx.ngrok-free.app/github-webhook/`
3. Content type: `application/json`
4. Event: Just the push event
5. Save

> Note: ngrok's free URL changes every restart — update the webhook URL each
> time, or use a static domain if you have an ngrok paid plan.

---

### Part 4 — Configure and Deploy the App

**1. Fill in environment variables**
On your EC2 instance:
```bash
mkdir ~/cicd-dashboard && cd ~/cicd-dashboard
nano .env
```
Paste (edit values accordingly):
```
JENKINS_URL=https://xxxx.ngrok-free.app
JENKINS_USER=your-jenkins-username
JENKINS_API_TOKEN=your-jenkins-api-token
AWS_REGION=ap-south-1
DYNAMODB_TABLE=cicd_builds
```

**2. Copy `docker-compose.yml` to EC2**
```bash
scp -i your-key.pem docker-compose.yml ubuntu@YOUR_EC2_IP:~/cicd-dashboard/
```

**3. Update `Jenkinsfile` and `docker-compose.yml` placeholders**
Replace these in both files before pushing to GitHub:
- `YOUR_DOCKERHUB_USERNAME`
- `YOUR_EC2_PUBLIC_IP`

**4. Trigger your first pipeline run**
Push a commit to `main` — Jenkins should auto-trigger via the webhook, then:
1. Run tests
2. Build both Docker images
3. Push to Docker Hub
4. SSH into EC2 and run `docker compose up -d`

**5. Access your dashboard**
Open in browser:
```
http://YOUR_EC2_PUBLIC_IP:8000
```

---

## Local Testing (before deploying)

You can run everything locally first:
```bash
cd backend
pip install -r requirements.txt
set JENKINS_URL=http://localhost:8080
set JENKINS_USER=admin
set JENKINS_API_TOKEN=your-token
python app.py
```
In a separate terminal:
```bash
cd frontend
pip install -r requirements.txt
set BACKEND_URL=http://localhost:5000
python app.py
```
Visit `http://localhost:8000`.

---

## API Endpoints (backend)

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/sync` | POST | Manually trigger a Jenkins → DynamoDB sync |
| `/api/jobs` | GET | List all jobs with latest build status |
| `/api/builds/<job_name>` | GET | Build history for a specific job |
| `/api/stats` | GET | Aggregate stats (success rate, avg duration, etc.) |

---

## Future Enhancements

- Add Slack/email notifications on build failure (via SES)
- Add authentication (JWT) to protect the dashboard
- Push custom metrics to CloudWatch instead of/alongside DynamoDB
- Use SSM Session Manager instead of raw SSH keys for Jenkins → EC2 deploy
- Add branch-based multi-environment deploys (dev/staging/prod)

---

## Author

Built as a Cloud/DevOps student project demonstrating EC2, IAM, Docker,
Jenkins, GitHub Webhooks, and a Python full-stack application working together
in a real CI/CD pipeline.
