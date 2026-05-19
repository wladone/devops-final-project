#!/usr/bin/env bash
set -euo pipefail

VALUES_FILE="${1:?Values file is required}"
TARGET_BRANCH="${2:?Target branch is required}"
GIT_USER_NAME="${3:?Git user name is required}"
GIT_USER_EMAIL="${4:?Git user email is required}"
DEPLOYED_IMAGE="${5:?Deployed image is required}"
PUSH_REMOTE="${6:-origin}"

git config user.name "$GIT_USER_NAME"
git config user.email "$GIT_USER_EMAIL"

git add "$VALUES_FILE"

if git diff --cached --quiet; then
  echo "No GitOps changes detected in $VALUES_FILE."
  exit 0
fi

git commit -m "chore(gitops): deploy $DEPLOYED_IMAGE"
git push "$PUSH_REMOTE" "HEAD:$TARGET_BRANCH"
