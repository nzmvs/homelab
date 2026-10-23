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

The initial `immediate` backup can race with the first plugin-attach pod rollout
and fail with `requested plugin is not available`. On 2026-10-22, logs showed
the backup starting before that rollout and the replacement pod subsequently
becoming healthy with two containers. Once the Cluster and plugin sidecar are
ready, create a fresh backup instead of reusing the failed Backup object:

```sh
kubectl create -f - <<'YAML'
apiVersion: postgresql.cnpg.io/v1
kind: Backup
metadata:
  generateName: pg-manual-
  namespace: postgres
spec:
  cluster:
    name: pg
  method: plugin
  pluginConfiguration:
    name: barman-cloud.cloudnative-pg.io
YAML
kubectl get backups -n postgres -w
```

The generated name makes each explicit retry a new request; the nightly schedule
remains unchanged. A ready pod alone does not prove R2 access or backup success.

## Restore drill

The [pg-restore app](../apps/pg-restore/cluster.yaml) is included in the
[parent apps Kustomization](../apps/kustomization.yaml). After committing and
pushing, Flux creates a separate Cluster named `pg-restore` in `postgres`.
It preserves `pg` and its PVC, reuses `r2-backups` and its encrypted credentials,
and allocates another `20Gi` local-path volume. Its PostgreSQL 18.4 image matches
the source image observed during backup setup.

```sh
kubectl get clusters -n postgres
kubectl wait --for=condition=Ready cluster.postgresql.cnpg.io/pg-restore \
  -n postgres --timeout=10m
kubectl get pods,pvc -n postgres -l cnpg.io/cluster=pg-restore
```

This restores the latest available backup and WAL without enabling WAL writes
from the restored cluster into the original archive. Compare known tables and
records with the source database, and record the restore duration. After verification, remove `pg-restore` from `apps/kustomization.yaml` and
remove its app directory, then commit and push so Flux prunes the temporary
Cluster. Inspect PVCs labeled `cnpg.io/cluster=pg-restore` afterward and clean up
only those test claims if they remain, accounting for the reclaim policy.
Deleting the live Cluster while its app is still included in Git will cause
Flux to recreate it. Never substitute `pg` as the drill Cluster name.

## References

- [Barman plugin usage and recovery](https://cloudnative-pg.io/plugin-barman-cloud/docs/usage/)
- [Retention policies](https://cloudnative-pg.io/plugin-barman-cloud/docs/retention/)
- [CloudNativePG scheduled backups](https://cloudnative-pg.io/docs/current/backup/)
