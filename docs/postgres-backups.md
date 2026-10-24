# PostgreSQL backups

The manifests configure Barman WAL archiving and compressed base backups in
`s3://homelab-postgres-backups/`, under the server name `pg`. The schedule requests
an immediate backup and subsequent backups at 02:00 in the operator’s timezone. Retention is a seven-day
recovery window, not a fixed count of seven backups.

Verify backup and WAL objects in R2, then test recovery using the drill below.
Record the date, source backup and comparison results in the global changelog.
A successful empty-database restore does not prove recovery of application records.

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
k get cluster pg -n postgres
k get objectstore r2-backups -n postgres
k get scheduledbackup pg-nightly -n postgres
k get backups -n postgres
k describe cluster pg -n postgres
```

Check that the Cluster returns to Ready, WAL archiving succeeds and at least one
Backup reaches `completed`. Also verify backup objects exist in the R2 bucket.
Investigate events and logs if credentials, archiving or backups fail. Never
paste decrypted Secrets into logs or chat.

The initial `immediate` backup can race with the first plugin-attach pod rollout
and fail with `requested plugin is not available`. If a retry is needed, declare a uniquely named
`Backup` manifest in Git and include it in Kustomize for Flux to reconcile;
do not create it directly with kubectl. Confirm the plugin sidecar is ready
first. A ready pod alone does not prove R2 access or backup success.

## Restore drill

To run a drill, create `apps/pg-restore/cluster.yaml` using the template below,
add a child `kustomization.yaml` listing `cluster.yaml`, and add `pg-restore` to
[parent apps Kustomization](../apps/kustomization.yaml). Review, commit and push
for Flux to deploy. The temporary app is not part of the permanent inventory.
Use the same PostgreSQL major version as the source and check its image tag
before deploying the template.

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

Flux will create a separate `pg-restore` Cluster in namespace `postgres`, reusing
`r2-backups` and reading archive server `pg`. The template pins PostgreSQL 18.4;
adjust it if the source version changes. There is no top-level `plugins` archiver
configuration or backup schedule, so the drill does not write WAL or backups to
the source archive. Recovery uses the latest usable base backup and available WAL.
The source Cluster, its Retain PVC and its NodePort Service are unchanged.

The temporary drill requests another `20Gi` on the existing **Delete-policy**
`local-path` class so its volume can be cleaned up with the temporary cluster.
Production `pg` continues to use `local-path-retain`. Actual disk consumption
uses the shared filesystem; 20Gi is not an enforced quota.

After Flux deployment, run:

```sh
k -n postgres get clusters,pods,pvc
k -n postgres wait --for=condition=Ready cluster.postgresql.cnpg.io/pg-restore --timeout=10m
k -n postgres exec pg-1 -c postgres -- psql -X -U postgres -d homelab -c "SELECT current_database(), pg_get_userbyid(datdba) AS owner FROM pg_database WHERE datname=current_database();"
k -n postgres exec pg-restore-1 -c postgres -- psql -X -U postgres -d homelab -c "SELECT current_database(), pg_get_userbyid(datdba) AS owner FROM pg_database WHERE datname=current_database();"
```

Both database/owner results should be `homelab`. Compare any known application
tables and records as well; Ready status and matching empty database metadata
establish only a limited restore check. Record what was actually verified.
These SQL queries inspect the source and restored databases without modifying them.

After verification, remove `pg-restore` from `apps/kustomization.yaml` and remove
its app directory, then commit/push for Flux to prune the temporary Cluster.
Verify only the drill pod/PVC/PV is removed and production `pg` remains healthy.
Do not delete resources directly with kubectl. Never substitute `pg` for
`pg-restore` in cleanup. No R2 deletion is needed for this restore drill.

## References

- [Barman plugin usage and recovery](https://cloudnative-pg.io/plugin-barman-cloud/docs/usage/)
- [Retention policies](https://cloudnative-pg.io/plugin-barman-cloud/docs/retention/)
- [CloudNativePG scheduled backups](https://cloudnative-pg.io/docs/current/backup/)
