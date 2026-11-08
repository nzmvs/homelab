# Fresh database bootstrap

**Only for an explicitly disposable, empty database on Delete-policy storage.**
This is not recovery for the current Retain-backed `pg`. Use the
[restore runbook](postgres-backups.md#restore-drill) for recovery.

## Prepare

```sh
go-task postgres:password
go-task postgres:storage
```

Confirm the old PVC belongs to the disposable Cluster and its PV has Delete
policy. Prepare `cluster.yaml` for database/user `homelab`, 20Gi on
`local-path-retain`.

## 1. Teardown

Exclude `cluster.yaml` and `scheduled-backup.yaml` from
`apps/postgres/kustomization.yaml`; retain the namespace, encrypted application
and R2 credentials, and ObjectStore. Validate and deploy through Git/Flux.

Run `go-task postgres:storage`. Verify the old Cluster, pods and PVC/PV are
gone and `local-path-retain` exists. Stop on incomplete teardown/finalizers.

## 2. Clear the disposable archive

With explicit approval and no active archiver, use Cloudflare MCP to delete
only `pg/` under `homelab-postgres-backups`. Preserve the bucket and unrelated
prefixes. Verify the prefix is empty before continuing.

## 3. Bootstrap

Re-include `cluster.yaml` and `scheduled-backup.yaml`. Run `go-task validate`,
then deploy through Git/Flux only after teardown and archive cleanup pass.

Run `go-task postgres:status` and `go-task postgres:storage`. Verify Cluster
Ready, new PV Retain, database/owner `homelab`, successful archiving and a
completed backup with new R2 objects.

Connect at `192.168.0.40:30432`; credentials: `postgres/pg-homelab`.
