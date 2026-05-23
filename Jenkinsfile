pipeline {
    agent any

    parameters {
        string(name: 'PROJECT_DIR', defaultValue: '.', description: 'Project directory relative to the Jenkins workspace or absolute path for a mounted local project')
        string(name: 'INPUT_FILE', defaultValue: 'data/raw/psq_customer_base_v8_stress.csv', description: 'Input dataset path inside the repository')
        string(name: 'RULES_FILE', defaultValue: 'config/rules.yml', description: 'Rules YAML path inside the repository')
        string(name: 'OUTPUT_DIR', defaultValue: 'reports/ci', description: 'Directory for generated reports')
        booleanParam(name: 'RUN_UNIT_TESTS', defaultValue: true, description: 'Run the full pytest suite (unit, property, integration, cli, security, chaos, infra) in parallel by marker')
        booleanParam(name: 'RUN_PERF_BENCHMARKS', defaultValue: false, description: 'Run the perf-marked benchmarks and enforce the regression gate from tests/perf/baseline.json (set RUN_PERF=true in env to force on nightly schedule)')
        booleanParam(name: 'RUN_SONAR_SCAN', defaultValue: false, description: 'Run SonarQube analysis when the scanner and credentials are available')
        string(name: 'SONAR_HOST_URL', defaultValue: '', description: 'SonarQube or SonarQube Cloud URL')
        string(name: 'SONAR_TOKEN_CREDENTIALS_ID', defaultValue: '', description: 'Jenkins secret text credentials ID for the Sonar token')
        booleanParam(name: 'RUN_DATA_QUALITY_JOB', defaultValue: true, description: 'Run the batch validation job and archive the generated reports')
        booleanParam(name: 'RUN_HELM_VALIDATION', defaultValue: false, description: 'Render and lint the Helm chart for the target environment')
        string(name: 'HELM_VALUES_FILE', defaultValue: 'helm/data-quality-monitor/values-dev.yaml', description: 'Environment values file used for Helm validation')
        string(name: 'HELM_RELEASE_NAME', defaultValue: 'data-quality-monitor', description: 'Release name used for Helm templating')
        string(name: 'HELM_NAMESPACE', defaultValue: 'dq-monitor-dev', description: 'Namespace used for Helm templating')
        string(name: 'K8S_NAMESPACE', defaultValue: 'dq-monitor-dev', description: 'Kubernetes namespace used by local core-mode smoke tests and runner jobs')
        string(name: 'K8S_RUNNER_CRONJOB', defaultValue: 'data-quality-monitor-data-quality-monitor-runner', description: 'CronJob name used to create the manual Kubernetes data-quality job')
        string(name: 'K8S_DASHBOARD_RESOURCE', defaultValue: 'svc/data-quality-monitor-data-quality-monitor-dashboard', description: 'Kubernetes resource used for the dashboard port-forward smoke test')
        booleanParam(name: 'RUN_TERRAFORM_VALIDATE', defaultValue: false, description: 'Run Terraform init -backend=false and validate for the selected environments')
        string(name: 'TERRAFORM_ENVIRONMENTS', defaultValue: 'dev staging prod', description: 'Space separated Terraform environment folders to validate')
        string(name: 'REGISTRY_IMAGE', defaultValue: '', description: 'Optional registry/repository name, for example registry.example.com/data-quality-monitor')
        string(name: 'IMAGE_TAG_OVERRIDE', defaultValue: '', description: 'Optional prebuilt image tag to reuse instead of the current Jenkins build number')
        string(name: 'REGISTRY_CREDENTIALS_ID', defaultValue: '', description: 'Optional Jenkins credentials ID for the Docker registry')
        booleanParam(name: 'RUN_DOCKER_BUILD', defaultValue: true, description: 'Build the Docker image for this run')
        booleanParam(name: 'RUN_SECURITY_SCAN', defaultValue: false, description: 'Run Trivy filesystem and image scans')
        booleanParam(name: 'TRIVY_ALLOW_FINDINGS', defaultValue: false, description: 'When true, Trivy reports findings but does not fail the build. Default false so HIGH/CRITICAL vulnerabilities block the pipeline.')
        string(name: 'TRIVY_SEVERITY', defaultValue: 'HIGH,CRITICAL', description: 'Comma-separated severities Trivy treats as blocking when TRIVY_ALLOW_FINDINGS is false')
        booleanParam(name: 'RUN_DOCKER_PUBLISH', defaultValue: true, description: 'Push the Docker image after a successful build or when reusing an existing image tag')
        booleanParam(name: 'SKIP_CHECKOUT', defaultValue: false, description: 'Skip SCM checkout when the project directory is already mounted on the Jenkins agent')
        booleanParam(name: 'RUN_DEPLOY', defaultValue: false, description: 'Deploy to the Linux host using Ansible after a successful build')
        booleanParam(name: 'RUN_ANSIBLE_IDEMPOTENCY', defaultValue: true, description: 'After a successful deploy, run the playbook a second time and assert changed=0 on every host')
        string(name: 'INVENTORY_PATH', defaultValue: 'ansible/inventory.ini', description: 'Ansible inventory file')
        string(name: 'SSH_CREDENTIALS_ID', defaultValue: '', description: 'Optional Jenkins SSH credentials ID for Ansible deploy')
        string(name: 'ANSIBLE_EXTRA_VARS', defaultValue: '', description: 'Optional additional Ansible extra vars, for example dashboard_port=18501')
        booleanParam(name: 'RUN_GITOPS_UPDATE', defaultValue: false, description: 'Update the target Helm values file with the new image tag and push the change to Git')
        string(name: 'GITOPS_VALUES_FILE', defaultValue: 'helm/data-quality-monitor/values-dev.yaml', description: 'Helm values file updated for the target environment')
        string(name: 'GITOPS_TARGET_BRANCH', defaultValue: 'main', description: 'Git branch that Argo CD watches')
        string(name: 'GITOPS_PUSH_REMOTE', defaultValue: 'origin', description: 'Git remote used for the GitOps push')
        string(name: 'GITOPS_PUSH_CREDENTIALS_ID', defaultValue: '', description: 'Optional Jenkins SSH credentials ID used to push GitOps changes')
        string(name: 'GIT_USER_NAME', defaultValue: 'jenkins-bot', description: 'Git author name used for GitOps commits')
        string(name: 'GIT_USER_EMAIL', defaultValue: 'jenkins@example.local', description: 'Git author email used for GitOps commits')
        booleanParam(name: 'RUN_ARGOCD_SYNC', defaultValue: false, description: 'Ask Argo CD to sync after the GitOps commit was pushed')
        string(name: 'ARGOCD_APP_NAME', defaultValue: 'data-quality-monitor-dev', description: 'Argo CD application name to sync')
        string(name: 'ARGOCD_SYNC_MODE', defaultValue: 'server', description: 'Sync mode: server or core for local kubectl-based sync')
        string(name: 'ARGOCD_NAMESPACE', defaultValue: 'argocd', description: 'Namespace where the Argo CD Application lives when using core sync')
        string(name: 'ARGOCD_SERVER', defaultValue: '', description: 'Argo CD API server, for example argocd.example.com')
        string(name: 'ARGOCD_AUTH_TOKEN_CREDENTIALS_ID', defaultValue: '', description: 'Jenkins secret text credentials ID for the Argo CD auth token')
        string(name: 'DASHBOARD_URL', defaultValue: '', description: 'Optional classic dashboard URL for the smoke test after Ansible deploy')
        string(name: 'K8S_DASHBOARD_URL', defaultValue: '', description: 'Optional Kubernetes dashboard URL for the smoke test after Argo CD sync')
    }

    options {
        timestamps()
    }

    environment {
        IMAGE_NAME = 'data-quality-monitor'
    }

    stages {
        stage('Checkout') {
            when {
                expression {
                    return !params.SKIP_CHECKOUT
                }
            }
            steps {
                checkout scm
            }
        }

        stage('Validate Delivery Inputs') {
            steps {
                script {
                    def deliveryModes = []
                    if (params.RUN_DEPLOY) {
                        deliveryModes << 'Ansible'
                    }
                    if (params.RUN_GITOPS_UPDATE) {
                        deliveryModes << 'GitOps'
                    }

                    def enabledChecks = []
                    if (params.RUN_SONAR_SCAN) {
                        enabledChecks << 'Sonar'
                    }
                    if (params.RUN_HELM_VALIDATION) {
                        enabledChecks << 'Helm'
                    }
                    if (params.RUN_TERRAFORM_VALIDATE) {
                        enabledChecks << 'Terraform'
                    }
                    if (params.RUN_SECURITY_SCAN) {
                        enabledChecks << 'Trivy'
                    }
                    if (params.RUN_ARGOCD_SYNC) {
                        enabledChecks << "Argo(${params.ARGOCD_SYNC_MODE})"
                    }
                    if (params.DASHBOARD_URL?.trim()) {
                        enabledChecks << 'Classic smoke'
                    }
                    if (params.K8S_DASHBOARD_URL?.trim() || params.RUN_ARGOCD_SYNC) {
                        enabledChecks << 'K8s smoke'
                    }

                    if ((params.RUN_DEPLOY || params.RUN_GITOPS_UPDATE || params.RUN_ARGOCD_SYNC) && !params.REGISTRY_IMAGE?.trim()) {
                        error('REGISTRY_IMAGE is required for remote delivery because the target host or cluster must pull a pushed image.')
                    }

                    if (!params.RUN_DOCKER_BUILD && !params.IMAGE_TAG_OVERRIDE?.trim() && (params.RUN_DOCKER_PUBLISH || params.RUN_DEPLOY || params.RUN_GITOPS_UPDATE || params.RUN_SECURITY_SCAN)) {
                        error('IMAGE_TAG_OVERRIDE is required when RUN_DOCKER_BUILD=false and later stages still need a Docker image reference.')
                    }

                    if (params.RUN_GITOPS_UPDATE && !params.GITOPS_VALUES_FILE?.trim()) {
                        error('GITOPS_VALUES_FILE is required when RUN_GITOPS_UPDATE=true')
                    }

                    if (params.RUN_ARGOCD_SYNC && !params.RUN_GITOPS_UPDATE) {
                        error('RUN_GITOPS_UPDATE must be true when RUN_ARGOCD_SYNC=true')
                    }

                    if (params.RUN_ARGOCD_SYNC && params.ARGOCD_SYNC_MODE != 'core' && !params.ARGOCD_SERVER?.trim()) {
                        error('ARGOCD_SERVER is required when RUN_ARGOCD_SYNC=true')
                    }

                    if (params.RUN_ARGOCD_SYNC && params.ARGOCD_SYNC_MODE != 'core' && !params.ARGOCD_AUTH_TOKEN_CREDENTIALS_ID?.trim()) {
                        error('ARGOCD_AUTH_TOKEN_CREDENTIALS_ID is required when RUN_ARGOCD_SYNC=true')
                    }

                    if (params.RUN_GITOPS_UPDATE && !params.GITOPS_TARGET_BRANCH?.trim()) {
                        error('GITOPS_TARGET_BRANCH is required when RUN_GITOPS_UPDATE=true')
                    }

                    if ((params.RUN_ARGOCD_SYNC || params.K8S_DASHBOARD_URL?.trim()) && !params.K8S_NAMESPACE?.trim()) {
                        error('K8S_NAMESPACE is required for Kubernetes delivery and smoke tests')
                    }

                    if (params.RUN_ARGOCD_SYNC && params.ARGOCD_SYNC_MODE == 'core' && !params.K8S_RUNNER_CRONJOB?.trim()) {
                        error('K8S_RUNNER_CRONJOB is required when RUN_ARGOCD_SYNC=true and ARGOCD_SYNC_MODE=core')
                    }

                    def deliveryLabel = deliveryModes ? deliveryModes.join(' + ') : 'CI only'
                    def checksLabel = enabledChecks ? enabledChecks.join(', ') : 'core checks only'
                    currentBuild.description = "${deliveryLabel} | ${checksLabel}"
                }
            }
        }

        stage('Test Suite') {
            when {
                expression {
                    return params.RUN_UNIT_TESTS
                }
            }
            parallel {
                stage('Unit + Property') {
                    steps {
                        sh '''
                            cd "$PROJECT_DIR"
                            source scripts/ci/bootstrap_python_env.sh
                            python -m pytest -m "unit or property or not (unit or property or integration or cli or perf or security or infra or e2e or chaos)" \
                              --cov=src --cov=dashboard --cov-report=xml:coverage.xml
                        '''
                    }
                }
                stage('Integration + Golden') {
                    steps {
                        sh '''
                            cd "$PROJECT_DIR"
                            source scripts/ci/bootstrap_python_env.sh
                            python -m pytest -m integration -v
                        '''
                    }
                }
                stage('CLI Contract') {
                    steps {
                        sh '''
                            cd "$PROJECT_DIR"
                            source scripts/ci/bootstrap_python_env.sh
                            python -m pytest -m cli -v
                        '''
                    }
                }
                stage('Security') {
                    steps {
                        sh '''
                            cd "$PROJECT_DIR"
                            source scripts/ci/bootstrap_python_env.sh
                            python -m pytest -m security -v
                        '''
                    }
                }
                stage('Chaos') {
                    steps {
                        sh '''
                            cd "$PROJECT_DIR"
                            source scripts/ci/bootstrap_python_env.sh
                            python -m pytest -m chaos -v
                        '''
                    }
                }
                stage('Infra Validation') {
                    steps {
                        sh '''
                            cd "$PROJECT_DIR"
                            source scripts/ci/bootstrap_python_env.sh
                            python -m pytest -m infra -v
                        '''
                    }
                }
            }
        }

        stage('Performance Benchmarks') {
            when {
                expression {
                    return params.RUN_UNIT_TESTS && (env.RUN_PERF == 'true' || params.RUN_PERF_BENCHMARKS == true)
                }
            }
            steps {
                sh '''
                    cd "$PROJECT_DIR"
                    source scripts/ci/bootstrap_python_env.sh
                    python -m pytest -m perf -v --benchmark-disable-gc \
                      --benchmark-json=reports/perf-${BUILD_NUMBER}.json
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/perf-*.json', allowEmptyArchive: true
                }
            }
        }

        stage('SonarQube Analysis') {
            when {
                expression {
                    return params.RUN_SONAR_SCAN
                }
            }
            steps {
                script {
                    if (!params.SONAR_HOST_URL?.trim()) {
                        error('SONAR_HOST_URL is required when RUN_SONAR_SCAN=true')
                    }
                    if (!params.SONAR_TOKEN_CREDENTIALS_ID?.trim()) {
                        error('SONAR_TOKEN_CREDENTIALS_ID is required when RUN_SONAR_SCAN=true')
                    }
                }
                withCredentials([string(credentialsId: params.SONAR_TOKEN_CREDENTIALS_ID, variable: 'SONAR_TOKEN')]) {
                    withEnv(["SONAR_HOST_URL=${params.SONAR_HOST_URL}"]) {
                        sh '''
                            cd "$PROJECT_DIR"
                            chmod +x scripts/ci/run_sonar_scan.sh
                            ./scripts/ci/run_sonar_scan.sh
                        '''
                    }
                }
            }
        }

        stage('Data Quality Run') {
            when {
                expression {
                    return params.RUN_DATA_QUALITY_JOB
                }
            }
            steps {
                sh '''
                    cd "$PROJECT_DIR"
                    chmod +x scripts/ci/run_quality.sh
                    ./scripts/ci/run_quality.sh "$INPUT_FILE" "$RULES_FILE" "$OUTPUT_DIR"
                '''
                sh '''
                    rm -rf ci-artifacts
                    mkdir -p ci-artifacts
                    cp -R "$PROJECT_DIR/$OUTPUT_DIR"/. ci-artifacts/
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'ci-artifacts/**/*', fingerprint: true
                }
            }
        }

        stage('Stress Data Quality Matrix') {
            when {
                expression {
                    return params.RUN_DATA_QUALITY_JOB
                }
            }
            steps {
                sh '''
                    cd "$PROJECT_DIR"
                    chmod +x scripts/ci/run_stress_quality.sh
                    ./scripts/ci/run_stress_quality.sh \
                      "$INPUT_FILE" \
                      data/stress \
                      "$RULES_FILE" \
                      reports/stress
                '''
                sh '''
                    rm -rf ci-stress-artifacts
                    mkdir -p ci-stress-artifacts
                    cp -R "$PROJECT_DIR/reports/stress"/. ci-stress-artifacts/
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'ci-stress-artifacts/**/*', fingerprint: true
                }
            }
        }

        stage('Quality Improvement Ladder') {
            when {
                expression {
                    return params.RUN_DATA_QUALITY_JOB
                }
            }
            steps {
                sh '''
                    cd "$PROJECT_DIR"
                    chmod +x scripts/ci/run_quality_ladder.sh
                    ./scripts/ci/run_quality_ladder.sh \
                      "$INPUT_FILE" \
                      "$RULES_FILE" \
                      data/processed/quality_ladder \
                      reports/quality-ladder
                '''
                sh '''
                    rm -rf ci-quality-ladder-artifacts
                    mkdir -p ci-quality-ladder-artifacts
                    cp -R "$PROJECT_DIR/reports/quality-ladder"/. ci-quality-ladder-artifacts/
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'ci-quality-ladder-artifacts/**/*', fingerprint: true
                }
            }
        }

        stage('SQL Pipeline') {
            when {
                expression {
                    return params.RUN_DATA_QUALITY_JOB
                }
            }
            steps {
                sh '''
                    cd "$PROJECT_DIR"
                    chmod +x scripts/ci/run_sql_pipeline.sh
                    ./scripts/ci/run_sql_pipeline.sh \
                      data/raw/psq_customer_base_v8.csv \
                      data/db/dq.db
                '''
                sh '''
                    rm -rf ci-sql-artifacts
                    mkdir -p ci-sql-artifacts
                    cp "$PROJECT_DIR/data/db/dq.db" ci-sql-artifacts/
                    # Also export the match summary as a queryable CSV for the build dashboard.
                    python - <<'PY'
import sqlite3, csv
con = sqlite3.connect("ci-sql-artifacts/dq.db")
with open("ci-sql-artifacts/match_summary.csv", "w", newline="") as f:
    w = csv.writer(f)
    cur = con.execute("SELECT source, in_ricos_flag, merchants, active_merchants, pct_of_source FROM analytics_psq_match_summary ORDER BY source, in_ricos_flag")
    w.writerow([c[0] for c in cur.description])
    w.writerows(cur.fetchall())
PY
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'ci-sql-artifacts/**/*', fingerprint: true
                }
            }
        }

        stage('Helm Template Validation') {
            when {
                expression {
                    return params.RUN_HELM_VALIDATION
                }
            }
            steps {
                sh '''
                    cd "$PROJECT_DIR"
                    chmod +x scripts/ci/render_helm_chart.sh
                    ./scripts/ci/render_helm_chart.sh "helm/data-quality-monitor" "$HELM_VALUES_FILE" "$HELM_RELEASE_NAME" "$HELM_NAMESPACE"
                '''
            }
        }

        stage('Helm Matrix Render') {
            when {
                expression {
                    return params.RUN_HELM_VALIDATION
                }
            }
            steps {
                sh '''
                    cd "$PROJECT_DIR"
                    chmod +x scripts/ci/render_helm_matrix.sh scripts/ci/render_helm_chart.sh
                    ./scripts/ci/render_helm_matrix.sh "helm/data-quality-monitor" "$HELM_RELEASE_NAME" "$HELM_NAMESPACE"
                '''
            }
        }

        stage('Terraform Validation') {
            when {
                expression {
                    return params.RUN_TERRAFORM_VALIDATE
                }
            }
            steps {
                sh '''
                    cd "$PROJECT_DIR"
                    chmod +x scripts/ci/run_terraform_validate.sh
                    ./scripts/ci/run_terraform_validate.sh "$TERRAFORM_ENVIRONMENTS"
                '''
            }
        }

        stage('Compute Image Metadata') {
            steps {
                script {
                    def resolvedImageTag = params.IMAGE_TAG_OVERRIDE?.trim() ? params.IMAGE_TAG_OVERRIDE.trim() : (env.BUILD_NUMBER ?: 'manual')
                    if (!params.RUN_DOCKER_BUILD && !params.IMAGE_TAG_OVERRIDE?.trim() && (params.RUN_DOCKER_PUBLISH || params.RUN_DEPLOY || params.RUN_GITOPS_UPDATE || params.RUN_SECURITY_SCAN)) {
                        error('Cannot compute Docker image metadata: IMAGE_TAG_OVERRIDE is required when RUN_DOCKER_BUILD=false and downstream stages need an image.')
                    }
                    if (params.REGISTRY_IMAGE?.trim()) {
                        env.DOCKER_IMAGE = "${params.REGISTRY_IMAGE}:${resolvedImageTag}"
                    } else {
                        env.DOCKER_IMAGE = "${env.IMAGE_NAME}:${resolvedImageTag}"
                    }
                    env.IMAGE_TAG = "${resolvedImageTag}"
                }
            }
        }

        stage('Build Docker Image') {
            when {
                expression {
                    return params.RUN_DOCKER_BUILD
                }
            }
            steps {
                sh '''
                    cd "$PROJECT_DIR"
                    docker build -t "$DOCKER_IMAGE" .
                '''
            }
        }

        stage('Trivy Security Scan') {
            when {
                expression {
                    return params.RUN_SECURITY_SCAN
                }
            }
            steps {
                withEnv([
                    "TRIVY_ALLOW_FINDINGS=${params.TRIVY_ALLOW_FINDINGS}",
                    "TRIVY_SEVERITY=${params.TRIVY_SEVERITY}",
                ]) {
                    sh '''
                        cd "$PROJECT_DIR"
                        chmod +x scripts/ci/run_trivy_scan.sh
                        ./scripts/ci/run_trivy_scan.sh . "$DOCKER_IMAGE"
                    '''
                }
            }
        }

        stage('Publish Docker Image') {
            when {
                expression {
                    return params.REGISTRY_IMAGE?.trim() && params.RUN_DOCKER_PUBLISH
                }
            }
            steps {
                script {
                    if (params.REGISTRY_CREDENTIALS_ID?.trim()) {
                        def registryHost = ''
                        if (params.REGISTRY_IMAGE?.trim() && params.REGISTRY_IMAGE.contains('/')) {
                            def firstComponent = params.REGISTRY_IMAGE.tokenize('/')[0]
                            if (firstComponent == 'localhost' || firstComponent.contains('.') || firstComponent.contains(':')) {
                                registryHost = firstComponent
                            }
                        }
                        withCredentials([usernamePassword(credentialsId: params.REGISTRY_CREDENTIALS_ID, usernameVariable: 'REGISTRY_USERNAME', passwordVariable: 'REGISTRY_PASSWORD')]) {
                            withEnv(["REGISTRY_HOST=${registryHost}"]) {
                                sh '''
                                    if [ -n "$REGISTRY_HOST" ]; then
                                      echo "$REGISTRY_PASSWORD" | docker login "$REGISTRY_HOST" -u "$REGISTRY_USERNAME" --password-stdin
                                    fi
                                    docker push "$DOCKER_IMAGE"
                                    if [ -n "$REGISTRY_HOST" ]; then
                                      docker logout "$REGISTRY_HOST" || true
                                    fi
                                '''
                            }
                        }
                    } else {
                        sh 'docker push "$DOCKER_IMAGE"'
                    }
                }
            }
        }

        stage('Update GitOps Repository') {
            when {
                expression {
                    return params.RUN_GITOPS_UPDATE
                }
            }
            steps {
                script {
                    def gitopsCommand = '''
                        cd "$PROJECT_DIR"
                        # Re-sync the local working tree with the remote bare repo BEFORE
                        # editing the values file. Without this a delivery run can lose
                        # the tag bump on its next commit if the bare repo moved (eg.
                        # because the lab was re-bootstrapped between runs).
                        git fetch "$GITOPS_PUSH_REMOTE" "$GITOPS_TARGET_BRANCH" 2>/dev/null || true
                        git reset --hard "$GITOPS_PUSH_REMOTE/$GITOPS_TARGET_BRANCH" 2>/dev/null || true
                        if [ -x ./.venv/bin/python ]; then
                          PIPELINE_PYTHON=./.venv/bin/python
                        else
                          PIPELINE_PYTHON=python3
                        fi
                        "$PIPELINE_PYTHON" scripts/ci/update_helm_values.py \
                          --values-file "$GITOPS_VALUES_FILE" \
                          --image-repository "$REGISTRY_IMAGE" \
                          --image-tag "$IMAGE_TAG"
                        chmod +x scripts/ci/gitops_commit_and_push.sh
                        ./scripts/ci/gitops_commit_and_push.sh \
                          "$GITOPS_VALUES_FILE" \
                          "$GITOPS_TARGET_BRANCH" \
                          "$GIT_USER_NAME" \
                          "$GIT_USER_EMAIL" \
                          "$DOCKER_IMAGE" \
                          "$GITOPS_PUSH_REMOTE"
                    '''

                    if (params.GITOPS_PUSH_CREDENTIALS_ID?.trim()) {
                        sshagent(credentials: [params.GITOPS_PUSH_CREDENTIALS_ID]) {
                            sh gitopsCommand
                        }
                    } else {
                        sh gitopsCommand
                    }
                }
            }
        }

        stage('Deploy With Ansible') {
            when {
                expression {
                    return params.RUN_DEPLOY
                }
            }
            steps {
                script {
                    def parseExtraVars = { String raw ->
                        def parsed = [:]
                        if (!raw?.trim()) {
                            return parsed
                        }

                        raw.trim().split(/\s+/).each { token ->
                            if (!token) {
                                return
                            }
                            def separator = token.indexOf('=')
                            if (separator <= 0) {
                                error("ANSIBLE_EXTRA_VARS entries must be key=value tokens. Invalid token: ${token}")
                            }
                            def key = token.substring(0, separator)
                            def value = token.substring(separator + 1)
                            if (!(key ==~ /[A-Za-z_][A-Za-z0-9_]*/)) {
                                error("ANSIBLE_EXTRA_VARS contains an invalid variable name: ${key}")
                            }
                            parsed[key] = value
                        }
                        return parsed
                    }

                    def ansibleVars = [
                        docker_image: env.DOCKER_IMAGE,
                        dashboard_url: params.DASHBOARD_URL ?: ''
                    ] + parseExtraVars(params.ANSIBLE_EXTRA_VARS)

                    writeFile file: '.jenkins-ansible-extra-vars.json', text: groovy.json.JsonOutput.prettyPrint(groovy.json.JsonOutput.toJson(ansibleVars))

                    def deployCommand = '''
                        cd "$PROJECT_DIR"
                        ansible-playbook -i "$INVENTORY_PATH" ansible/playbook.yml \
                          --extra-vars @"$WORKSPACE/.jenkins-ansible-extra-vars.json"
                    '''
                    if (params.SSH_CREDENTIALS_ID?.trim()) {
                        sshagent(credentials: [params.SSH_CREDENTIALS_ID]) {
                            sh deployCommand
                        }
                    } else {
                        sh deployCommand
                    }
                }
            }
        }

        stage('Ansible Idempotency Check') {
            when {
                expression {
                    return params.RUN_DEPLOY && params.RUN_ANSIBLE_IDEMPOTENCY
                }
            }
            steps {
                script {
                    def idempotencyCommand = '''
                        cd "$PROJECT_DIR"
                        chmod +x scripts/ci/ansible_idempotency.sh
                        ./scripts/ci/ansible_idempotency.sh "$INVENTORY_PATH" "ansible/playbook.yml" "$WORKSPACE/.jenkins-ansible-extra-vars.json"
                    '''
                    if (params.SSH_CREDENTIALS_ID?.trim()) {
                        sshagent(credentials: [params.SSH_CREDENTIALS_ID]) {
                            sh idempotencyCommand
                        }
                    } else {
                        sh idempotencyCommand
                    }
                }
            }
        }

        stage('Sync Argo CD Application') {
            when {
                expression {
                    return params.RUN_ARGOCD_SYNC
                }
            }
            steps {
                script {
                    if (params.ARGOCD_SYNC_MODE == 'core') {
                        withEnv(["ARGOCD_SYNC_MODE=${params.ARGOCD_SYNC_MODE}", "ARGOCD_NAMESPACE=${params.ARGOCD_NAMESPACE}"]) {
                            sh '''
                                cd "$PROJECT_DIR"
                                chmod +x scripts/ci/argocd_sync.sh
                                ./scripts/ci/argocd_sync.sh "$ARGOCD_APP_NAME" "" "300"
                            '''
                        }
                    } else {
                        withCredentials([string(credentialsId: params.ARGOCD_AUTH_TOKEN_CREDENTIALS_ID, variable: 'ARGOCD_AUTH_TOKEN')]) {
                            withEnv(["ARGOCD_SYNC_MODE=${params.ARGOCD_SYNC_MODE}", "ARGOCD_NAMESPACE=${params.ARGOCD_NAMESPACE}"]) {
                                sh '''
                                    cd "$PROJECT_DIR"
                                    chmod +x scripts/ci/argocd_sync.sh
                                    ./scripts/ci/argocd_sync.sh "$ARGOCD_APP_NAME" "$ARGOCD_SERVER" "300"
                                '''
                            }
                        }
                    }
                }
            }
        }

        stage('Run Kubernetes Data Quality Job') {
            when {
                expression {
                    return params.RUN_ARGOCD_SYNC && params.ARGOCD_SYNC_MODE == 'core'
                }
            }
            steps {
                sh '''
                    set -eu
                    JOB_NAME="data-quality-monitor-manual-${BUILD_NUMBER}"
                    NAMESPACE="$K8S_NAMESPACE"
                    CRONJOB_NAME="$K8S_RUNNER_CRONJOB"

                    for _ in $(seq 1 60); do
                      CURRENT_IMAGE="$(kubectl -n "$NAMESPACE" get cronjob "$CRONJOB_NAME" -o jsonpath='{.spec.jobTemplate.spec.template.spec.containers[0].image}')"
                      echo "CronJob image is ${CURRENT_IMAGE}; expecting ${DOCKER_IMAGE}"
                      if [ "$CURRENT_IMAGE" = "$DOCKER_IMAGE" ]; then
                        break
                      fi
                      sleep 2
                    done

                    CURRENT_IMAGE="$(kubectl -n "$NAMESPACE" get cronjob "$CRONJOB_NAME" -o jsonpath='{.spec.jobTemplate.spec.template.spec.containers[0].image}')"
                    if [ "$CURRENT_IMAGE" != "$DOCKER_IMAGE" ]; then
                      echo "CronJob did not converge to ${DOCKER_IMAGE}; current image is ${CURRENT_IMAGE}" >&2
                      exit 1
                    fi

                    kubectl -n "$NAMESPACE" delete job "$JOB_NAME" --ignore-not-found=true
                    kubectl -n "$NAMESPACE" create job "$JOB_NAME" --from="cronjob/$CRONJOB_NAME"

                    if ! kubectl -n "$NAMESPACE" wait --for=condition=complete "job/$JOB_NAME" --timeout=240s; then
                      kubectl -n "$NAMESPACE" logs "job/$JOB_NAME" --all-containers=true || true
                      exit 1
                    fi

                    kubectl -n "$NAMESPACE" logs "job/$JOB_NAME" --all-containers=true
                '''
            }
        }

        stage('Smoke Test Classic') {
            when {
                expression {
                    return params.RUN_DEPLOY && params.DASHBOARD_URL?.trim()
                }
            }
            steps {
                sh '''
                    cd "$PROJECT_DIR"
                    chmod +x scripts/ci/smoke_test.sh
                    ./scripts/ci/smoke_test.sh "$DASHBOARD_URL"
                '''
            }
        }

        stage('Smoke Test Kubernetes') {
            when {
                expression {
                    return params.RUN_ARGOCD_SYNC && (params.K8S_DASHBOARD_URL?.trim() || params.ARGOCD_SYNC_MODE == 'core' || params.DASHBOARD_URL?.trim())
                }
            }
            steps {
                script {
                    if (params.ARGOCD_SYNC_MODE == 'core') {
                        withEnv([
                            "K8S_SMOKE_NAMESPACE=${params.K8S_NAMESPACE}",
                            "K8S_SMOKE_RESOURCE=${params.K8S_DASHBOARD_RESOURCE}",
                            'K8S_SMOKE_LOCAL_PORT=18051',
                            'K8S_SMOKE_REMOTE_PORT=8501',
                        ]) {
                            sh '''
                                cd "$PROJECT_DIR"
                                chmod +x scripts/ci/smoke_test.sh
                                ./scripts/ci/smoke_test.sh "http://127.0.0.1:18051"
                            '''
                        }
                    } else {
                        withEnv(["RESOLVED_K8S_DASHBOARD_URL=${params.K8S_DASHBOARD_URL?.trim() ? params.K8S_DASHBOARD_URL.trim() : params.DASHBOARD_URL.trim()}"]) {
                            sh '''
                                cd "$PROJECT_DIR"
                                chmod +x scripts/ci/smoke_test.sh
                                ./scripts/ci/smoke_test.sh "$RESOLVED_K8S_DASHBOARD_URL"
                            '''
                        }
                    }
                }
            }
        }
    }

    post {
        always {
            sh 'docker image inspect "$DOCKER_IMAGE" >/dev/null 2>&1 || true'
        }
    }
}
