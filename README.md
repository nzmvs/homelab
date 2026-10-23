# Homelab

Kubernetes cluster configuration managed through [Flux](https://fluxcd.io/).
This inventory describes the desired state in this repository, rather than a
live health report. Follow-up work is tracked in [TODO.md](TODO.md).

## Cluster contents

| Component | Purpose | Namespace | Upstream |
| --- | --- | --- | --- |
| [Flux](clusters/homelab/flux-system/) | GitOps | `flux-system` | [Documentation](https://fluxcd.io/flux/) |
| [Local Path Provisioner](infrastructure/local-path-provisioner/helm.yaml) | Local storage provisioner | `local-path-storage` | [Project](https://github.com/rancher/local-path-provisioner) |
| [cert-manager](infrastructure/cert-manager/helm.yaml) | Certificate manager | `cert-manager` | [Documentation](https://cert-manager.io/docs/) |
| [CloudNativePG](infrastructure/cloudnative-pg/helm.yaml) | PostgreSQL operator | `cnpg-system` | [Documentation](https://cloudnative-pg.io/documentation/) |
| [Barman Cloud plugin](infrastructure/plugin-barman-cloud/helm.yaml) | PostgreSQL backup and recovery | `cnpg-system` | [Documentation](https://cloudnative-pg.io/plugin-barman-cloud/docs/) |
| [PostgreSQL](apps/postgres/cluster.yaml) | Database (stage 2; deployment pending) | `postgres` | [CloudNativePG](https://cloudnative-pg.io/documentation/) |

Infrastructure HelmRelease and source objects live in `flux-system`; the table
lists the namespaces where the charts install their workloads. The PostgreSQL
application declares its own namespace, while infrastructure Helm releases
create their target namespaces as configured.

PostgreSQL declares WAL archiving through the Barman plugin to the private
Standard R2 bucket `homelab-postgres-backups`. The
[ObjectStore](apps/postgres/object-store.yaml) sets gzip compression and a
seven-day recovery window. The [schedule](apps/postgres/scheduled-backup.yaml)
requests a backup on creation and nightly at 02:00 in the operator’s timezone. Credentials are stored in
a SOPS-encrypted Secret. The configuration has been deployed. R2 listing confirms a compressed base
backup, its metadata and archived WAL files. The user accepted the empty-database restore check on 2026-10-23; populated-record
recovery remains untested. Enabling the plugin
restarts the single PostgreSQL instance.
The Retain policy changes below are pending deployment through Git and Flux.
[local-path-retain](infrastructure/local-path-provisioner/storage-class-retain.yaml)
is a new default StorageClass using the existing local-path provisioner with
`reclaimPolicy: Retain`. The chart-managed `local-path` class remains available
with its existing `Delete` policy, but its default-class annotation is disabled
through Helm values. A new class avoids changing an immutable reclaim policy.
CNPG selects `local-path-retain` for newly created claims. Since the current
database is empty, the intended transition is a fresh PostgreSQL bootstrap on
this class through a staged Git/Flux change. Merely changing the Cluster storage
class does not replace its existing PVC: the running `pg-1` volume remains on
`local-path` with `Delete` until that transition. No existing-PV overlay is used.
The database/PVC replacement has not been performed. Before rebootstrap, account
for CNPG's PVC ownership/retention behavior. The user approved discarding the old
empty-database test backups: after the old cluster has stopped archiving, remove
only its `pg/` archive prefix from the R2 bucket, then bootstrap against that
empty prefix using the existing archive name. Cleanup has not been performed;
do not delete bucket contents while the old cluster is still writing backups/WAL.
Retain preserves storage after PVC deletion, requires manual recovery/cleanup,
and does not replace the R2 backups.

The PostgreSQL claim requests `20Gi`. Local Path Provisioner does not enforce
capacity limits on its hostPath directories: the database shares the node
filesystem with the OS and other workloads. Monitor filesystem free space as
well as database size and WAL growth; changing the request does not reserve disk
space. Read-only checks on 2026-10-23 found `app` at about 7.6 MiB, the PGDATA
directory at 384 MiB, and about 203 GiB available on the shared filesystem.

The earlier empty-database restore drill is documented in the
[backup runbook](docs/postgres-backups.md); its temporary app has been removed
from the repository.

## PostgreSQL rebootstrap

Stage 1 was deployed through Flux: the user verified the old Cluster, pods,
PVCs and PV were gone and `local-path-retain` was the default Retain class.
Cloudflare MCP deleted the 13 old test archive objects under `pg/` and verified
that prefix empty. The local PostgreSQL Kustomization is now prepared for
**stage 2**, with the Cluster and ScheduledBackup re-enabled. Commit and push
this stage for Flux to bootstrap database/user `homelab` on new Retain storage.
Stage 2 has not been deployed. See the [runbook](docs/postgres-rebootstrap.md).

## PostgreSQL application credentials

The new application login (`homelab`, database `homelab`) is declared in the
[SOPS-encrypted pg-homelab Secret](apps/postgres/pg-homelab.sops.yaml).
The Cluster references it under `bootstrap.initdb.secret`; Flux decrypts it
using the existing SOPS setup. The username matches the bootstrap owner, and
the password is newly generated. Superuser password access remains disabled.
This change is pending deployment through Git and Flux.
Set your chosen password with the hidden-input
[helper](scripts/create-postgres-secret.py):

```sh
python scripts/create-postgres-secret.py --replace
```

It prompts twice, performs base64 encoding and SOPS encryption in memory, and
writes only ciphertext. The existing Secret is replaced only after successful
encryption. This changes local files; deployment remains through Git and Flux.

## PostgreSQL LAN access

This configuration is pending deployment through Git and Flux.

The [PostgreSQL Cluster](apps/postgres/cluster.yaml) declares the CNPG-managed
`pg-lan` NodePort Service in namespace `postgres`. It follows the current primary
and exposes TCP `30432` on the nodes, forwarding to PostgreSQL port `5432`.
For the current home node, connect to `192.168.0.40:30432` with database `homelab`
and user `homelab`, using the new password from `pg-homelab`. Internal clients can
continue using `pg-rw:5432`. LAN reachability depends on node firewall and routing.
A Cilium LoadBalancer with a dedicated LAN IP is planned; see [TODO.md](TODO.md).

## Reconciliation

The [Flux Git source](clusters/homelab/flux-system/gotk-sync.yaml) tracks the
`main` branch of this repository every minute. Its root Kustomization reconciles
`clusters/homelab` every ten minutes.

The [cluster-root Kustomize file](clusters/homelab/kustomization.yaml) explicitly
includes Flux bootstrap resources and the infrastructure/apps Flux Kustomizations.
Those Flux objects then reconcile their own repository paths.

- [Infrastructure](clusters/homelab/infrastructure.yaml) reconciles
  [infrastructure/](infrastructure/kustomization.yaml) every ten minutes and
  waits for readiness.
- [Apps](clusters/homelab/apps.yaml) reconciles
  [apps/](apps/kustomization.yaml) every ten minutes, depends on infrastructure,
  and enables SOPS decryption using the `sops-age` Secret.
- Both Kustomizations enable pruning of resources removed from their manifests.
- Helm releases reconcile hourly; Helm/Git chart sources refresh daily.

## Repository conventions

- [clusters/homelab/](clusters/homelab/) wires Flux to infrastructure and apps.
  Preserve generated Flux bootstrap files and their formatting.
- [infrastructure/](infrastructure/) groups each component into a directory with
  `helm.yaml` and a child `kustomization.yaml`. The parent lists those directories.
  Related chart sources and releases share `helm.yaml`; Barman reuses the
  CloudNativePG HelmRepository across component directories.
- [apps/](apps/) groups application manifests into component directories with
  child Kustomizations. Use descriptive resource filenames such as
  `namespace.yaml` and `cluster.yaml`.
- Keep explicit chart versions and source tags. Preserve component-specific
  source references, dependencies, intervals and namespace ownership.
- [.sops.yaml](.sops.yaml) defines age encryption for `data` and `stringData` in
  `*.sops.yaml` files. Keep plaintext credentials and private keys out of Git.
- [renovate.json](renovate.json) configures Flux dependency updates, with
  dashboard approval required for major updates.

## Local validation

To create the R2 credential Secret, run
`python scripts/create-r2-secret.py` in a regular terminal and enter the two S3
keys at its hidden prompts. The [helper](scripts/create-r2-secret.py) writes only
SOPS ciphertext to `apps/postgres/r2-credentials.sops.yaml`; it does not deploy
the Secret. The PostgreSQL Kustomization includes the encrypted Secret for Flux
to decrypt. See [backup verification and recovery](docs/postgres-backups.md).

Run from the repository root:

```sh
kubectl kustomize clusters/homelab
kubectl kustomize infrastructure
kubectl kustomize apps
git diff --check
```

These checks render manifests locally; they do not deploy resources or establish
live cluster health.

Keep this README synchronized with component additions, removals, upgrades,
configuration changes and manifest moves.
