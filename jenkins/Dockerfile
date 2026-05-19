FROM docker:27-cli AS dockercli
FROM alpine/helm:3.16.4 AS helmbin
FROM aquasec/trivy:0.59.1 AS trivybin
FROM hashicorp/terraform:1.9.8 AS terraformbin
FROM quay.io/argoproj/argocd:v2.13.3 AS argocdbin
FROM sonarsource/sonar-scanner-cli:latest AS sonarbin

FROM jenkins/jenkins:lts-jdk21

USER root

COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=dockercli /usr/local/libexec/docker/cli-plugins /usr/local/libexec/docker/cli-plugins
COPY --from=helmbin /usr/bin/helm /usr/local/bin/helm
COPY --from=trivybin /usr/local/bin/trivy /usr/local/bin/trivy
COPY --from=terraformbin /bin/terraform /usr/local/bin/terraform
COPY --from=argocdbin /usr/local/bin/argocd /usr/local/bin/argocd
COPY --from=sonarbin /opt/sonar-scanner /opt/sonar-scanner
RUN ln -s /opt/sonar-scanner/bin/sonar-scanner /usr/local/bin/sonar-scanner

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ansible \
        curl \
        git \
        kubernetes-client \
        openssh-client \
        python3 \
        python3-pip \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

USER jenkins

COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt
