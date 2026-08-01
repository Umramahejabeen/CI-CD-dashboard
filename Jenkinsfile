pipeline {
    agent any

    environment {
        EC2_HOST = '13.204.80.94'
        EC2_USER = 'ubuntu'
        REMOTE_DIR = '~/cicd-dashboard'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Run Backend Tests') {
            steps {
                dir('backend') {
                    bat 'python -m pip install --upgrade pip'
                    bat 'pip install -r requirements.txt'
                    bat 'python -m py_compile app.py jenkins_client.py dynamodb_client.py'
                }
            }
        }

        stage('Deploy & Build on EC2') {
            steps {
                withCredentials([sshUserPrivateKey(credentialsId: 'cicd-ec2-ssh-key', keyFileVariable: 'SSH_KEY', usernameVariable: 'SSH_USER')]) {
                    bat """
                    ssh -o StrictHostKeyChecking=no -i "%SSH_KEY%" %EC2_USER%@%EC2_HOST% ^
                    "cd %REMOTE_DIR% && git pull origin main && docker compose down && docker compose build --no-cache && docker compose up -d --remove-orphans"
                    """
                }
            }
        }
    }

    post {
        success {
            echo 'Pipeline completed successfully. Dashboard rebuilt and redeployed on EC2.'
        }
        failure {
            echo 'Pipeline failed. Check console output above.'
        }
    }
}