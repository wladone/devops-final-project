#!/usr/bin/env bash
# Run the Ansible playbook twice and assert the second pass reports changed=0.
# A non-idempotent task (e.g. a shell step without changed_when) shows up here
# as a real regression instead of in production after a re-deploy.
set -euo pipefail

INVENTORY_PATH="${1:?inventory path required}"
PLAYBOOK_PATH="${2:-ansible/playbook.yml}"
EXTRA_VARS_FILE="${3:-}"

ansible_args=("-i" "$INVENTORY_PATH" "$PLAYBOOK_PATH")
if [[ -n "$EXTRA_VARS_FILE" && -f "$EXTRA_VARS_FILE" ]]; then
  ansible_args+=("--extra-vars" "@${EXTRA_VARS_FILE}")
fi

echo "===> First pass (establishing baseline state)"
ansible-playbook "${ansible_args[@]}"

second_log="$(mktemp)"
trap 'rm -f "$second_log"' EXIT

echo "===> Second pass (must report changed=0 for every host)"
ansible-playbook "${ansible_args[@]}" | tee "$second_log"

# Ansible's recap lines look like:
# host : ok=12   changed=0    unreachable=0    failed=0   ...
# Any host with changed > 0 on the second pass means a task is not idempotent.
non_idempotent_hosts="$(grep -E '^[^ ]+ +: +ok=' "$second_log" | awk '
  {
    for (i = 1; i <= NF; i++) {
      if ($i ~ /^changed=/) {
        split($i, kv, "=")
        if (kv[2] != "0") {
          print $1
        }
      }
    }
  }
')"

if [[ -n "$non_idempotent_hosts" ]]; then
  echo "FAIL: idempotency violated on:" >&2
  echo "$non_idempotent_hosts" >&2
  exit 1
fi

echo "Ansible playbook is idempotent (changed=0 on second pass)."
