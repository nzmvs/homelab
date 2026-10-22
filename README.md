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
| [PostgreSQL](apps/postgres/cluster.yaml) | Database | `postgres` | [CloudNativePG](https://cloudnative-pg.io/documentation/) |

Infrastructure HelmRelease and source objects live in `flux-system`; the table
lists the namespaces where the charts install their workloads. The PostgreSQL
application declares its own namespace, while infrastructure Helm releases
create their target namespaces as configured.

PostgreSQL declares WAL archiving through the Barman plugin to the private
Standard R2 bucket `homelab-postgres-backups`. The
[ObjectStore](apps/postgres/object-store.yaml) sets gzip compression and a
seven-day recovery window. The [schedule](apps/postgres/scheduled-backup.yaml)
requests a backup on creation and nightly at 02:00 in the operator’s timezone. Credentials are stored in
a SOPS-encrypted Secret. These manifests are prepared locally; deployment,
successful backup and restore verification remain pending. Enabling the plugin
restarts the single PostgreSQL instance.
Local-path storage currently uses the chart's default reclaim policy rather
than an explicit `Retain` override; see the storage task in [TODO.md](TODO.md).

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
