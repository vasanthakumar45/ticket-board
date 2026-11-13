pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timeout(time: 60, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    environment {
        API_IMAGE = 'vasanth45/ticket-api'
        WEB_IMAGE = 'vasanth45/ticket-web'
        TAG       = "${env.BUILD_NUMBER}"
    }

    stages {
        stage('Test API') {
            steps {
                sh '''
                    python3 -m venv "$WORKSPACE/.venv"
                    . "$WORKSPACE/.venv/bin/activate"
                    pip install --quiet -r api/requirements.txt
                    cd api
                    python -m pytest
                '''
            }
        }

        stage('Build images') {
            steps {
                sh '''
                    docker build -t $API_IMAGE:$TAG ./api
                    docker build -t $WEB_IMAGE:$TAG ./web
                '''
            }
        }

        stage('Security scan') {
            steps {
                sh '''
                    for img in $API_IMAGE:$TAG $WEB_IMAGE:$TAG; do
                        echo "=== Report (HIGH and CRITICAL) for $img ==="
                        trivy image --no-progress --scanners vuln --severity HIGH,CRITICAL --exit-code 0 $img
                        echo "=== Gate (fail on fixable CRITICAL) for $img ==="
                        trivy image --no-progress --scanners vuln --severity CRITICAL --ignore-unfixed --exit-code 1 $img
                    done
                '''
            }
        }

        stage('Push images') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub',
                                                  usernameVariable: 'DH_USER',
                                                  passwordVariable: 'DH_PASS')]) {
                    sh '''
                        echo "$DH_PASS" | docker login -u "$DH_USER" --password-stdin
                        docker push $API_IMAGE:$TAG
                        docker push $WEB_IMAGE:$TAG
                    '''
                }
            }
        }

        stage('Deploy to dev') {
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh '''
                        set -e
                        kubectl get secret db-credentials -n ticket-dev >/dev/null || { echo "Secret db-credentials is missing in ticket-dev (see Step 4.2)"; exit 1; }
                        sed -i "s/newTag: .*/newTag: $TAG/" k8s/overlays/dev/kustomization.yaml
                        kubectl apply -k k8s/overlays/dev
                        for d in db api web; do
                            kubectl rollout status deployment/$d -n ticket-dev --timeout=180s
                        done
                    '''
                }
            }
        }

        stage('Smoke test dev') {
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh 'sh scripts/smoke-test.sh dev write'
                }
            }
        }

        stage('Approve prod') {
            steps {
                timeout(time: 30, unit: 'MINUTES') {
                    input message: "Dev passed all checks with ${env.API_IMAGE}:${env.TAG}. Deploy it to PROD?", ok: 'Deploy to prod'
                }
            }
        }

        stage('Deploy to prod') {
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh '''
                        set -e
                        kubectl get secret db-credentials -n ticket-prod >/dev/null || { echo "Secret db-credentials is missing in ticket-prod (see Step 4.2)"; exit 1; }
                        sed -i "s/newTag: .*/newTag: $TAG/" k8s/overlays/prod/kustomization.yaml
                        kubectl apply -k k8s/overlays/prod
                        for d in db api web; do
                            if ! kubectl rollout status deployment/$d -n ticket-prod --timeout=180s; then
                                echo "Rollout of $d failed - rolling back prod"
                                kubectl rollout undo deployment/api -n ticket-prod || true
                                kubectl rollout undo deployment/web -n ticket-prod || true
                                exit 1
                            fi
                        done
                    '''
                }
            }
        }

        stage('Smoke test prod') {
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh 'sh scripts/smoke-test.sh prod read'
                }
            }
        }
    }

    post {
        success { echo "Released ${env.API_IMAGE}:${env.TAG} and ${env.WEB_IMAGE}:${env.TAG} to prod" }
        failure { echo 'Pipeline failed. Open the red stage and read its log.' }
        always  { sh 'docker logout || true' }
    }
}
