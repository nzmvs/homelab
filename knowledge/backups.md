---
type: Recovery Design
title: Backups
description: Remote recovery through Barman base backups and WAL.
generated: {by: codex/gpt-6-astra, at: 2026-11-08T00:56:41Z}
sources:
  - resource: ../apps/postgres/cluster.yaml
  - resource: ../apps/postgres/object-store.yaml
  - resource: ../apps/postgres/scheduled-backup.yaml
  - resource: ../docs/postgres-backups.md
  - resource: ../docs/postgres-rebootstrap.md
---
# Recovery chain

[PostgreSQL](postgres.md) uses Barman ObjectStore `r2-backups`, credential Secret
`r2-credentials`, and R2 bucket `homelab-postgres-backups`, archive `pg`.
Continuous WAL plus base backups support a seven-day recovery window.
`pg-nightly` schedules 02:00 in the operator's timezone, including an immediate
initial backup; no timezone is pinned.

The [restore drill](../docs/postgres-backups.md#restore-drill) reads the archive into
a separate Cluster without archiving back. Successful restoration needs its own
verification. Fresh-bootstrap instructions exclude the current Retain-backed database.
[Alerts](alerts.md) detect backup and archiving failures.
