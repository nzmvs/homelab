# PostgreSQL backups

The manifests configure Barman WAL archiving and compressed base backups in
`s3://homelab-postgres-backups/`, under the server name `pg`. The schedule requests
an immediate backup and subsequent backups at 02:00 in the operator’s timezone. Retention is a seven-day
recovery window, not a fixed count of seven backups. Until backup and restore
checks succeed, recovery has not been proven.

The schedule uses six cron fields (`0 0 2 * * *`), including seconds. Do not
prepend `CRON_TZ`: the installed admission validator rejects it. Confirm the
actual next execution time through `ScheduledBackup.status.nextScheduleTime`;
the schedule itself does not explicitly set a timezone.

## Deployment and verification

After reviewing, committing and pushing the manifests for Flux reconciliation,
expect the single-instance database to restart as the plugin sidecar is added.
Flux decrypts `r2-credentials.sops.yaml` using its existing `sops-age` Secret.
Do not apply the encrypted file directly with kubectl.

```sh
kubectl get cluster pg -n postgres
kubectl get objectstore r2-backups -n postgres
kubectl get scheduledbackup pg-nightly -n postgres
kubectl get backups -n postgres
kubectl describe cluster pg -n postgres
```

Check that the Cluster returns to Ready, WAL archiving succeeds and at least one
Backup reaches `completed`. Also verify backup objects exist in the R2 bucket.
Investigate events and logs if credentials, archiving or backups fail. Never
paste decrypted Secrets into logs or chat.

## Restore drill

Restore into a new Cluster, preserving `pg` and its PVC. Save the following
manifest outside the reconciled app tree and apply it explicitly when ready.
It uses another local-path volume of `20Gi` and runs another PostgreSQL instance.

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: pg-restore
  namespace: postgres
spec:
  instances: 1
  bootstrap:
    recovery:
      source: pg-backup-source
  externalClusters:
    - name: pg-backup-source
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

This restores the latest available backup and WAL without enabling WAL writes
from the restored cluster into the original archive. Compare known tables and
records with the source database, and record the restore duration. Remove only
the disposable restore Cluster after verification, accounting for its PVCs and
the storage reclaim policy. Never substitute `pg` as the drill Cluster name.

## References

- [Barman plugin usage and recovery](https://cloudnative-pg.io/plugin-barman-cloud/docs/usage/)
- [Retention policies](https://cloudnative-pg.io/plugin-barman-cloud/docs/retention/)
- [CloudNativePG scheduled backups](https://cloudnative-pg.io/docs/current/backup/)
