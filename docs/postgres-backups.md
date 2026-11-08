# PostgreSQL backups

R2: `s3://homelab-postgres-backups/`, archive `pg`. Base backups run at 02:00
in the operator's timezone, with continuous WAL archiving and a seven-day
recovery window (not seven backup files).

The six-field schedule includes seconds. Do not prepend `CRON_TZ`; the admission
validator rejects it. Check `ScheduledBackup.status.nextScheduleTime` for actual
execution time.

## Deployment and verification

```sh
go-task postgres:r2-credentials   # initial encrypted credentials; refuses overwrite
go-task validate
go-task postgres:status
```

Deploy through Git/Flux. Adding the Barman sidecar restarts the single-instance
database. Verify Cluster Ready, successful WAL archiving, a completed Backup
and objects in R2 (use Cloudflare MCP).

An initial immediate backup can fail with `requested plugin is not available`
during sidecar rollout. Once the sidecar is ready, add a uniquely named `Backup`
manifest through Git/Flux to retry.

## Restore drill

Create `apps/pg-restore/cluster.yaml` below and a child Kustomization listing it;
include `pg-restore` in [apps](../apps/kustomization.yaml). Match the source
PostgreSQL major version; update the example image tag before deployment if needed.

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: pg-restore
  namespace: postgres
spec:
  instances: 1
  imageName: ghcr.io/cloudnative-pg/postgresql:18.4-system-trixie
  bootstrap:
    recovery:
      source: pg-archive
  externalClusters:
    - name: pg-archive
      plugin:
        name: barman-cloud.cloudnative-pg.io
        parameters:
          barmanObjectName: r2-backups
          serverName: pg
  storage:
    size: 20Gi
    storageClass: local-path
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      memory: 1Gi
```

Keep the drill free of archiver `plugins` and backup schedules: it must only
read archive `pg`. The template restores the latest usable backup and WAL onto
**Delete-policy** storage. Check shared disk space; 20Gi is not an enforced quota.

After Git/Flux deployment:

```sh
go-task postgres:restore:verify
```

Expect database/owner `homelab` in both clusters. Also compare known application
tables and records; an empty-database restore is only a limited check. Record
the source backup and comparison results.

Remove only `pg-restore` from the apps Kustomization and its directory, then
deploy cleanup through Git/Flux. Verify the drill pod/PVC/PV is removed and
production `pg` remains healthy. Never substitute `pg` in cleanup or delete
source R2 objects.

[Barman recovery reference](https://cloudnative-pg.io/plugin-barman-cloud/docs/usage/).
