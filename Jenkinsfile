pipeline {
    agent any

    environment {
        DOCKER_CREDENTIALS = 'dockerhub-creds'
        DOCKER_USERNAME = 'umramahejabeen'
        BACKEND_IMAGE         = "${DOCKER_USERNAME}/cicd-dashboard-backend"
        FRONTEND_IMAGE        = "${DOCKER_USERNAME}/cicd-dashboard-frontend"
        EC2_HOST              = '13.204.80.94'
        EC2_USER              = 'ubuntu'
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

        stage('Build Docker Images') {
            steps {
                bat "docker build -t %BACKEND_IMAGE%:%BUILD_NUMBER% -t %BACKEND_IMAGE%:latest ./backend"
                bat "docker build -t %FRONTEND_IMAGE%:%BUILD_NUMBER% -t %FRONTEND_IMAGE%:latest ./frontend"
            }
        }

        stage('Push to Docker Hub') {
            steps {
                bat "echo %DOCKER_CREDENTIALS_PSW% | docker login -u %DOCKER_CREDENTIALS_USR% --password-stdin"
                bat "docker push %BACKEND_IMAGE%:%BUILD_NUMBER%"
                bat "docker push %BACKEND_IMAGE%:latest"
                bat "docker push %FRONTEND_IMAGE%:%BUILD_NUMBER%"
                bat "docker push %FRONTEND_IMAGE%:latest"
            }
        }

        stage('Deploy to EC2') {
            steps {
                sshagent(credentials: ['ec2-ssh-key']) {   // Jenkins credential ID for EC2 SSH key
                    bat """
                    ssh -o StrictHostKeyChecking=no %EC2_USER%@%EC2_HOST% ^
                    "cd ~/cicd-dashboard && docker compose pull && docker compose up -d --remove-orphans"
                    """
                }
            }
        }
    }

    post {
        success {
            echo 'Pipeline completed successfully. Dashboard redeployed.'
        }
        failure {
            echo 'Pipeline failed. Check console output above.'
        }
        always {
            bat 'docker logout'
        }
    }
}
