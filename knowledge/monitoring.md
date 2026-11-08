---
type: Monitoring System
title: Monitoring
description: Focused PostgreSQL monitoring and dashboard persistence.
generated: {by: codex/gpt-6-astra, at: 2026-11-08T01:03:03Z}
sources:
  - resource: ../infrastructure/monitoring/helm.yaml
  - resource: ../apps/postgres/pod-monitor.yaml
  - resource: ../docs/grafana.md
---
# Coverage and state

The Prometheus stack selects PodMonitors and rules labeled `release: monitoring`.
[PostgreSQL](postgres.md) is scraped every 60s; rules evaluate every 60s.
Default Kubernetes rules, exporters and control-plane scrapes are disabled.
[Backup alerts](alerts.md) are the configured monitoring purpose.

Prometheus retains up to 3d/4GB on a 5Gi `local-path` claim; Alertmanager uses
1Gi on the same class. Grafana keeps settings/dashboards on 2Gi
`local-path-retain`, with no configured backup. Recreate causes dashboard downtime
during upgrades. [Dashboard procedures](../docs/grafana.md) and [LAN access](access.md).
