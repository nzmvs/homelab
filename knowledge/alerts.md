---
type: Alert Pipeline
title: Alerts
description: Backup failure detection and separate Telegram delivery paths.
generated: {by: codex/gpt-6-astra, at: 2026-11-08T00:56:41Z}
sources:
  - resource: ../apps/postgres/backup-alerts.yaml
  - resource: ../apps/postgres/pod-monitor.yaml
  - resource: ../taskfiles/monitoring/create-secret.py
  - resource: ../infrastructure/notifications/alert.yaml
  - resource: ../docs/backup-alerts.md
  - resource: ../docs/telegram-alerts.md
---
# Detection and delivery

Six [PostgreSQL](postgres.md) rules cover failed/overdue backups, failed/stalled
WAL archiving, missing metrics and unavailable scrape targets. Stalled archiving
requires pending WAL; silence alone does not establish healthy [backups](backups.md).

The Alertmanager configuration generator routes `service: pg-backups` to
Telegram with recovery messages. Flux events use a separate Telegram Provider
and credential configuration. Rotation must update both paths.

[Thresholds and delivery tests](../docs/backup-alerts.md) distinguish successful
scraping from phone receipt. This in-cluster pipeline cannot report a complete
host or network outage.
