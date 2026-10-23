# Fresh homelab database bootstrap

All cluster changes go through Git and Flux. The user runs deployment commands;
the agent prepares files only. Use Cloudflare MCP for R2 inspection and cleanup.
The running database has not been replaced by these local edits.

## Choose the application password

From the repository root, run:

```sh
python scripts/create-postgres-secret.py --replace
```

Enter your password twice at the hidden prompts. The helper updates only the
SOPS-encrypted `pg-homelab` Secret locally, with username `homelab`; it handles
base64 encoding and never writes the plaintext password to disk.

## Current progress

Stage 1 completed through Flux at revision `af9ddf91`. The user verified no old
Cluster, pods, PVCs or PVs remained. Cloudflare MCP removed 13 objects from `pg/`
and confirmed zero remaining objects. Local files now include the stage-2 Cluster
and ScheduledBackup; commit/push and live verification are pending.

## Stage 1: remove the old database

The stage-1 PostgreSQL Kustomization included namespace, encrypted
`pg-homelab` credentials, R2 credentials and ObjectStore, but excludes the Cluster
and ScheduledBackup. The Cluster file on disk defines the future `homelab`
database owned by `homelab`, with a 20Gi request on `local-path-retain`.

Review and deploy this stage via Git/Flux. Removing the old Cluster prunes its
owned resources; the existing PVC was observed to be owned by that Cluster and
its PV has Delete policy. Do not re-enable the Cluster until the old resources
are actually gone. Keep the namespace and backup configuration.

Read-only checks (run from the repository root):

```sh
kubectl --kubeconfig ~/.kube/rke2-home.yaml -n flux-system get kustomization apps infrastructure
kubectl --kubeconfig ~/.kube/rke2-home.yaml -n postgres get clusters,pods,pvc
kubectl --kubeconfig ~/.kube/rke2-home.yaml get pv
kubectl --kubeconfig ~/.kube/rke2-home.yaml get storageclass
```

Verify `pg`, its pods and old `pg-1` PVC/PV are gone, and that
`local-path-retain` exists with Retain policy. Do not delete resources directly
with kubectl. Stop and inspect ownership/finalizers if teardown is incomplete.

## Clear the old test archive

Only after teardown has completed and nothing is archiving, use Cloudflare MCP
to list and delete objects under `pg/` in `homelab-postgres-backups`. The user
approved discarding these empty-database test backups. Keep the bucket and any
unrelated prefixes; verify `pg/` is empty before continuing. Reuse the existing
ObjectStore, credentials and archive name; no new serverName is required.

## Stage 2: bootstrap fresh

These two resources are now re-added to `apps/postgres/kustomization.yaml`:

```yaml
  - cluster.yaml
  - scheduled-backup.yaml
```

Review, validate, commit and push that change for Flux to deploy. Never push
stage 2 before teardown and archive cleanup have been verified.

```sh
kubectl kustomize infrastructure >/dev/null
kubectl kustomize apps >/dev/null
kubectl kustomize clusters/homelab >/dev/null
git diff --check
```

Verify the new Cluster is Ready, its new PV uses Retain, and the new database
`homelab` is owned by `homelab`. Check continuous archiving and a completed backup;
then confirm new backup/WAL objects in R2. Retain is not a backup, and local-path
does not enforce the 20Gi request as a filesystem quota.

Connection after stage 2: `192.168.0.40:30432`, database/user `homelab`.
The password is in Secret `postgres/pg-homelab` (encrypted in the repository).
