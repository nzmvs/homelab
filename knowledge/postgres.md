---
type: Database
title: PostgreSQL
description: Database identity, connectivity and retained local storage.
generated: {by: codex/gpt-6-astra, at: 2026-11-08T00:56:41Z}
sources:
  - resource: ../apps/postgres/cluster.yaml
  - resource: ../infrastructure/local-path-provisioner/storage-class-retain.yaml
  - resource: ../README.md
  - resource: ../docs/postgres-backups.md
---
# Database and storage

CloudNativePG Cluster `postgres/pg` declares one instance, database/owner
`homelab`, and credential Secret `pg-homelab`. Clients use
`pg-rw.postgres.svc.cluster.local:5432` or `192.168.0.40:30432` through the
`pg-lan` NodePort; see the [access boundary](access.md).

Its 20Gi claim uses node-local `local-path-retain`: released volumes are retained,
but capacity is not an enforced disk quota. One instance provides no replica
failover. [Barman backups](backups.md) supply remote recovery;
[monitoring](monitoring.md) observes backup and WAL metrics.
