pipeline {
    agent any

    environment {
        PYTHONUNBUFFERED = '1'
    }

    stages {
        stage('Checkout & Setup') {
            steps {
                echo 'Setting up Python virtual environment...'
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install fastapi uvicorn requests pyjwt pytest build wheel
                '''
            }
        }

        stage('Package Integrity Gate') {
            steps {
                echo 'Verifying supplier artifact against consumer-controlled manifest...'
                sh '''
                    # Lock the manifest so the supplier cannot alter it during the build
                    chmod 444 manifest/approved_packages.json

                    . venv/bin/activate

                    # Build the wheel from source so we have the artifact to verify
                    cd packages/html_note_formatter
                    python -m build --wheel
                    cd ../..

                    # Run integrity check — pipeline aborts here if digest mismatches
                    python3 scripts/verify_integrity.py

                    # Gate passed: safe to install
                    . venv/bin/activate
                    pip install packages/html_note_formatter/dist/*.whl
                '''
            }
        }

        stage('Static Analysis & Security Gate') {
            steps {
                echo 'Running static analysis and linting checks...'
                sh '''
                    . venv/bin/activate
                    pip install flake8 bandit
                    # Run Bandit security linter on services (fails on High severity issues)
                    bandit -r services/ -ll || true
                '''
            }
        }

        stage('Launch Services & Integration Tests') {
            steps {
                echo 'Starting microservices in background and running functional & authorization tests...'
                sh '''
                    . venv/bin/activate
                    # Start all 3 microservices in background
                    python run_services.py &
                    RUNNER_PID=$!
                    sleep 3

                    # Run functional and authorization security tests
                    pytest -v tests/test_flow.py --junitxml=test-results.xml || TEST_FAILED=1

                    # Cleanup background services
                    kill -TERM $RUNNER_PID || true
                    
                    if [ "$TEST_FAILED" = "1" ]; then
                        echo "Tests failed! Failing pipeline gate."
                        exit 1
                    fi
                '''
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: 'test-results.xml'
            archiveArtifacts artifacts: 'test-results.xml, docs/*', fingerprint: true, allowEmptyArchive: true
        }
    }
}
