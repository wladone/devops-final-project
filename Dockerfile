FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV DEBIAN_FRONTEND=noninteractive

# Pull the latest patched Debian packages so the Trivy gate does not flag
# fixed OS-level CVEs (libcap2, libudev1, etc.) on every build.
RUN apt-get update \
    && apt-get -y upgrade \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Application code + runtime data.
COPY src ./src
COPY dashboard ./dashboard
COPY config ./config
COPY data ./data
COPY reports ./reports
COPY scripts/data ./scripts/data

# Capability evidence — the dashboard's "Configured DevOps Surface" and
# "Environment Readiness" panels stat these paths to prove the project
# carries its own infra/config alongside the app. Read-only at runtime.
COPY Jenkinsfile ./Jenkinsfile
COPY Dockerfile ./Dockerfile
COPY docker-compose.yml ./docker-compose.yml
COPY sonar-project.properties ./sonar-project.properties
COPY ansible ./ansible
COPY helm ./helm
COPY argocd ./argocd
COPY terraform ./terraform
COPY monitoring ./monitoring
COPY security ./security
COPY docs ./docs

EXPOSE 8501

CMD ["python", "src/main.py", "--input", "data/raw/psq_customer_base_v8_stress.csv", "--rules", "config/rules.yml", "--output-dir", "reports/latest"]
