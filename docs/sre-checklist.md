# SRE Checklist

- Immutable image tags are used.
- No production deploy relies on `latest`.
- Resource requests and limits are defined.
- Liveness and readiness probes are defined.
- Deployments are version-controlled and reproducible.
- Secrets are not hardcoded in Git.
- CI runs tests before image publication.
- Security scans are part of the release flow.
- Monitoring and alerts exist for availability and job failures.
- Rollback steps are documented and tested.
