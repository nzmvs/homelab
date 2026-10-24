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

## PostgreSQL

Cluster `pg` bootstraps database `homelab`, owned by login `homelab`.
The [application Secret](apps/postgres/pg-homelab.sops.yaml) is SOPS-encrypted
and referenced by `bootstrap.initdb.secret`. Superuser password access is disabled
by default. Set the application password locally with the
[hidden-input helper](taskfiles/postgres/create-secret.py), then deploy through Git
and Flux:

```sh
go-task postgres:password
```

The helper confirms the password, handles base64 encoding and writes only SOPS
ciphertext. It does not deploy resources.

### Access

| Client | Host | Port |
| --- | --- | --- |
| LAN | `192.168.0.40` | `30432` |
| Same Kubernetes namespace | `pg-rw` | `5432` |
| Other Kubernetes namespaces | `pg-rw.postgres.svc.cluster.local` | `5432` |

Use database/user `homelab` and the password in `pg-homelab`.
The CNPG-managed `pg-lan` NodePort Service follows the current primary.
LAN access depends on node firewall and routing.

### Storage

[local-path-retain](infrastructure/local-path-provisioner/storage-class-retain.yaml)
is the default StorageClass and uses Retain. PostgreSQL explicitly selects it
with a `20Gi` request. Retained data requires manual recovery or cleanup after
PVC deletion; Retain does not replace backups.

The chart-managed `local-path` class uses Delete and is not the default. A
temporary restore drill can select it for disposable test storage. Both
classes use the same provisioner and `/opt/local-path-provisioner` on the node.
Local Path Provisioner does not enforce capacity quotas: `20Gi` neither reserves
space nor limits directory growth. Monitor shared filesystem space, database size
and WAL growth.

### Backups and recovery

The [ObjectStore](apps/postgres/object-store.yaml) configures compressed base
backups and WAL archiving to `s3://homelab-postgres-backups/`, archive name `pg`,
with a seven-day recovery window. The [schedule](apps/postgres/scheduled-backup.yaml)
requests a backup on creation and at 02:00 in the operator's timezone.
R2 credentials are [SOPS-encrypted](apps/postgres/r2-credentials.sops.yaml).

Use the [backup runbook](docs/postgres-backups.md) to verify backup/WAL objects,
restore into the separate `pg-restore` cluster, compare data and remove the drill
through GitOps. The drill has no WAL archiver or LAN Service. The separate
[rebootstrap runbook](docs/postgres-rebootstrap.md) describes the disposable
Delete-to-Retain migration procedure.

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

## Notifications

[Telegram alerts](docs/telegram-alerts.md) forward Flux informational and error events
using the existing notification-controller. Run the documented setup helper to
discover the destination chat, create the Provider and SOPS-encrypted bot token,
and enable the
[notification manifests](infrastructure/notifications/). Infrastructure enables
SOPS decryption using `flux-system/sops-age`. Notification delivery requires
credentials, deployment and verification; PostgreSQL backup monitoring remains
separate work.

Run `go-task telegram:test` to send a test message using the saved
configuration and inspect request errors. See the [setup guide](docs/telegram-alerts.md).

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

## Runbook tasks

[Taskfile.yml](Taskfile.yml) exposes repeatable runbook commands using the
installed `go-task` executable. The root file composes the following modules:

| Included Taskfile | Responsibility |
| --- | --- |
| [validate/Taskfile.yml](taskfiles/validate/Taskfile.yml) | Local manifest and whitespace checks |
| [telegram/Taskfile.yml](taskfiles/telegram/Taskfile.yml) | Bot setup, delivery test and Flux notification inspection |
| [postgres/Taskfile.yml](taskfiles/postgres/Taskfile.yml) | Credentials, backup/storage status and restore verification |

Each module keeps its supporting Python files beside its Taskfile. Taskfiles
orchestrate commands; adjacent Python files own credential handling, rendering
and validation logic. The command names remain the public interface.

Taskfiles use native `includes` namespaces. The root retains shared context
configuration and entrypoints. Shared `KUBECTL_COMMAND` selects and shell-quotes
the context. Each include receives a `KUBE` command and a separate `NAMESPACE`
value. Tasks compose `{{.KUBE}} -n {{.NAMESPACE}}` for their usual namespace,
specify another namespace explicitly when needed, or omit `-n` for cluster-wide
operations. Namespace values remain configuration rather than additional command
aliases. Include variables preserve scope and context overrides. Commands and helpers execute from the repository
root, including when invoked from a subdirectory. Use leading `:` for calls
from a module to another root namespace.

Run from the repository root or a subdirectory:

```sh
go-task --list
go-task --dry validate
go-task validate
```

The default task lists commands. `validate` renders manifests locally and checks
diff whitespace. Python helpers retain credential handling and test logic. Credential tasks write local encrypted files; `telegram:test` sends one
message.

Live inspection tasks explicitly use context `homelab`. Override it when
needed, for example `go-task telegram:status KUBE_CONTEXT=homelab`.
Requirements depend on the task: kubectl/Git for local rendering and inspection, and Python/PyYAML/SOPS for
credential helpers. Tasks do not commit, push, reconcile, apply or delete cluster
resources; follow the runbooks for deployment and cleanup.

## Local validation

To create the R2 credential Secret, run
`go-task postgres:r2-credentials` in a regular terminal and enter the two S3
keys at its hidden prompts. The [helper](taskfiles/postgres/create-r2-secret.py) writes only
SOPS ciphertext to `apps/postgres/r2-credentials.sops.yaml`; it does not deploy
the Secret. The PostgreSQL Kustomization includes the encrypted Secret for Flux
to decrypt. See [backup verification and recovery](docs/postgres-backups.md).

Run from the repository root:

```sh
go-task validate
```

These checks render manifests locally; they do not deploy resources or establish
live cluster health.

Keep this README synchronized with configuration changes. Record rollout
progress and verification history in the global changelog.
