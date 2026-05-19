#!/usr/bin/env bash
set -euo pipefail

SONAR_HOST_URL="${SONAR_HOST_URL:-}"
SONAR_TOKEN="${SONAR_TOKEN:-}"
SONAR_SCANNER_WORKDIR="${SONAR_SCANNER_WORKDIR:-.tmp/sonar-scannerwork}"
COVERAGE_REPORT_PATH="${COVERAGE_REPORT_PATH:-}"
SONAR_CLEAN_SCAN="${SONAR_CLEAN_SCAN:-true}"
ORIGINAL_PROJECT_DIR="$(pwd)"
ANALYSIS_DIR=""

cleanup() {
  if [[ -n "$ANALYSIS_DIR" && -d "$ANALYSIS_DIR" ]]; then
    rm -rf "$ANALYSIS_DIR"
  fi
}
trap cleanup EXIT

if [[ -z "$SONAR_HOST_URL" || -z "$SONAR_TOKEN" ]]; then
  echo "SONAR_HOST_URL and SONAR_TOKEN must be set for SonarQube analysis." >&2
  exit 1
fi

if ! command -v sonar-scanner >/dev/null 2>&1; then
  echo "sonar-scanner is required. Install it on the Jenkins agent before enabling this stage." >&2
  exit 1
fi

if [[ "$SONAR_CLEAN_SCAN" == "true" ]]; then
  ANALYSIS_DIR="$(mktemp -d)"
  cp -R "${ORIGINAL_PROJECT_DIR}/src" "${ANALYSIS_DIR}/src"
  cp -R "${ORIGINAL_PROJECT_DIR}/dashboard" "${ANALYSIS_DIR}/dashboard"
  cp -R "${ORIGINAL_PROJECT_DIR}/tests" "${ANALYSIS_DIR}/tests"
  cp "${ORIGINAL_PROJECT_DIR}/sonar-project.properties" "${ANALYSIS_DIR}/sonar-project.properties"

  if [[ -f "${ORIGINAL_PROJECT_DIR}/coverage.xml" ]]; then
    cp "${ORIGINAL_PROJECT_DIR}/coverage.xml" "${ANALYSIS_DIR}/coverage.xml"
    COVERAGE_REPORT_PATH="coverage.xml"
  fi

  cd "$ANALYSIS_DIR"
  SONAR_SCANNER_WORKDIR=".scannerwork"
fi

scanner_args=(
  "-Dsonar.host.url=${SONAR_HOST_URL}"
  "-Dsonar.token=${SONAR_TOKEN}"
  "-Dsonar.scm.disabled=true"
  "-Dsonar.working.directory=${SONAR_SCANNER_WORKDIR}"
)

if [[ -z "$COVERAGE_REPORT_PATH" && -f "coverage.xml" ]]; then
  COVERAGE_REPORT_PATH="$(pwd)/coverage.xml"
fi

if [[ -n "$COVERAGE_REPORT_PATH" ]]; then
  scanner_args+=("-Dsonar.python.coverage.reportPaths=${COVERAGE_REPORT_PATH}")
fi

sonar-scanner "${scanner_args[@]}"
