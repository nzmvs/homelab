# Homelab

RKE2 + Flux. [Infrastructure](clusters/homelab/infrastructure.yaml) reconciles before
[apps](clusters/homelab/apps.yaml).

| Component | Namespace |
| --- | --- |
| [Flux](clusters/homelab/flux-system/) | `flux-system` |
| [Local Path Provisioner](infrastructure/local-path-provisioner/) | `local-path-storage` |
| [cert-manager](infrastructure/cert-manager/helm.yaml) | `cert-manager` |
| [CloudNativePG](infrastructure/cloudnative-pg/helm.yaml) + [Barman](infrastructure/plugin-barman-cloud/helm.yaml) | `cnpg-system` |
| [PostgreSQL](apps/postgres/cluster.yaml) | `postgres` |
| [Homepage](apps/homepage/) | `homepage` |
| [Prometheus / Alertmanager / Grafana](infrastructure/monitoring/helm.yaml) | `monitoring` |

## Access

[Homepage](http://homepage.k8s.lan) links to the monitoring UIs.
[Hosts-file setup](docs/homepage.md#lan-addresses).
HTTP, restricted to `192.168.0.0/24`; Grafana allows anonymous editing.

PostgreSQL: `192.168.0.40:30432` or `pg-rw.postgres.svc.cluster.local:5432`.
Database/user: `homelab`; Secret: `postgres/pg-homelab`.

## Runbooks

- [PostgreSQL backups and restore](docs/postgres-backups.md) · [Rebootstrap](docs/postgres-rebootstrap.md)
- [Backup alerts](docs/backup-alerts.md) · [Grafana](docs/grafana.md)
- [Homepage](docs/homepage.md) · [Telegram](docs/telegram-alerts.md)

## Runbook tasks

```sh
go-task --list
go-task validate
go-task monitoring:check
```

Default context: `homelab`; override with `KUBE_CONTEXT=...`. Preview: `--dry`.
Requires kubectl, Helm, Python/PyYAML and SOPS; Docker for image/alert checks.
