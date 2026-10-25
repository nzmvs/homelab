# PostgreSQL backup alerts

Run commands from the repository root using `go-task`; see the
[task guide](../README.md#runbook-tasks) for prerequisites, previews and context selection.

Prometheus scrapes the `pg` instance metrics every minute through a
[PodMonitor](../apps/postgres/pod-monitor.yaml). The
[rules](../apps/postgres/backup-alerts.yaml) evaluate every minute and
Alertmanager sends firing and resolved notifications to the existing Telegram
destination. Flux notifications continue to report reconciliation events.

## Components and thresholds

The [monitoring HelmRelease](../infrastructure/monitoring/helm.yaml) pins
`kube-prometheus-stack` chart `92.11.0` (Prometheus Operator `v0.94.1`). It installs
Prometheus, Alertmanager and the operator in `monitoring`. Grafana, node exporter,
kube-state-metrics, cluster component scrapers and default alert rules are
disabled. Only rules labeled `release: monitoring` are selected.

| Alert | Condition | Hold time |
| --- | --- | --- |
| PostgreSQLBackupFailed | Latest failed backup timestamp is newer than latest success | 5 minutes |
| PostgreSQLBackupOverdue | Latest successful backup is older than 26 hours, or timestamp is zero | 5 minutes |
| PostgreSQLWALArchivingFailed | Latest archive failure is newer than latest success | 10 minutes |
| PostgreSQLWALArchivingStalled | WAL is pending, with no success for over 10 minutes or no success ever | 10 minutes |
| PostgreSQLBackupMetricsMissing | A required backup or WAL metric is absent | 15 minutes |
| PostgreSQLMetricsUnavailable | All `pg` scrape targets are down, or no target exists | 5 minutes |

The nightly backup has a two-hour allowance beyond the daily interval. WAL
staleness requires pending WAL, avoiding alerts solely because a database is
idle. A newer successful backup clears the backup failure alert; historical
failures remain visible in Kubernetes Backup resources. Rules are scoped to the
single `postgres/pg` cluster; reassess primary/replica aggregation before adding
instances or clusters.

Alertmanager groups by alert name/service, waits 30 seconds before initial
delivery, groups changes over five minutes and repeats ongoing problems every
six hours. These times are additional to scrape/evaluation and hold times.
Only alerts labeled `service: pg-backups` go to Telegram. Resolved notifications
are enabled. These rules do not send routine backup success notifications.

Prometheus stores up to three days/4GB of metrics on a 5Gi `local-path` PVC;
Alertmanager uses a 1Gi `local-path` PVC for notification state. These use the
Delete storage class. As with other local-path volumes, requested sizes do not
enforce filesystem quotas. The UIs use internal ClusterIP Services only.
Monitor memory usage after deployment; the initial Prometheus request/limit is
512Mi/1Gi. This stack cannot notify if the entire host, cluster or network fails;
an external heartbeat monitor is needed for that.

## Telegram credentials

`infrastructure/monitoring/alertmanager-config.sops.yaml` holds the complete
Alertmanager configuration encrypted by SOPS, including the bot token and
numeric chat ID. It reuses the saved Flux Telegram settings, without sharing
Secrets across namespaces. The infrastructure Flux Kustomization decrypts it
with its existing `sops-age` key.

After changing the bot token or destination, regenerate the local file:

```sh
go-task monitoring:credentials
```

Review and deploy through Git/Flux. The helper does not send messages or deploy
resources. Alertmanager requires a numeric chat ID; Telegram setup discovery
can obtain one if the saved Flux Provider uses a channel handle instead.

## Validate and deploy

From the repository root:

```sh
go-task monitoring:check
```

The validation script requires Docker and network access to pull the pinned
Prometheus/Alertmanager images. It runs ten rule scenarios with `promtool` and
checks the decrypted Alertmanager config with `amtool` over stdin, without
writing plaintext credentials to disk or sending messages.

The aggregate task runs these checks sequentially; they are also available
individually:

```sh
go-task validate
go-task monitoring:render
go-task backup-alerts:validate
```

`monitoring:render` reads the chart version and values from the HelmRelease.
It requires Helm and network access to download the chart.

Commit/push and let Flux deploy. Infrastructure waits for the monitoring
HelmRelease before the dependent apps Kustomization creates PodMonitor and
PrometheusRule resources, so their CRDs must be installed first.

## Verify after deployment

Run the read-only live verification first:

```sh
go-task monitoring:verify
```

This queries Prometheus and Alertmanager through the Kubernetes service proxy;
no port-forward is needed. It checks PostgreSQL targets, expected rules, required
backup/WAL metrics, synthetic test state and cumulative Telegram counters.
A nonzero exit means a scrape, rule state/health or required metric needs
attention. Counters alone do not prove phone receipt or recovery delivery.

For visual inspection, open the UIs using the tasks below.

The UI forwarding and log tasks require the monitoring HelmRelease to have
deployed its Services and workloads. Local manifests alone do not create them.
If a task reports monitoring unavailable, inspect Flux deployment status before
retrying; the task does not install the stack.

```sh
go-task monitoring:status
go-task monitoring:prometheus
```

Open `http://localhost:9090/targets` and confirm the `pg` target is UP. Check the
rules page for evaluation errors. Query these metrics and confirm nonzero
backup success time and sensible WAL values:

```promql
barman_cloud_cloudnative_pg_io_last_available_backup_timestamp{namespace="postgres",cluster="pg"}
barman_cloud_cloudnative_pg_io_last_failed_backup_timestamp{namespace="postgres",cluster="pg"}
cnpg_pg_stat_archiver_last_archived_time{namespace="postgres",cluster="pg"}
cnpg_pg_stat_archiver_last_failed_time{namespace="postgres",cluster="pg"}
cnpg_collector_pg_wal_archive_status{namespace="postgres",cluster="pg",value="ready"}
```

In another terminal, forward Alertmanager with
`go-task monitoring:alertmanager` and
open `http://localhost:9093`. Check its logs for delivery failures:

```sh
go-task monitoring:logs
```

Test the full notification pipeline through local GitOps files:

```sh
go-task backup-alerts:test -- fire
go-task validate
```

This creates `apps/postgres/backup-alert-test.yaml` and includes it in the
PostgreSQL Kustomization. Review, commit and push for Flux to deploy. The
synthetic `PostgreSQLBackupAlertTest` rule has a one-minute hold time and routes
through the same `service: pg-backups` receiver. Allow roughly two to three
minutes after rule discovery for a clearly marked TEST firing message.

After confirming the firing message, remove the temporary rule:

```sh
go-task backup-alerts:test -- remove
go-task validate
```

Review, commit and push cleanup through Git/Flux. Verify that the test
PrometheusRule is removed and the test alert clears in Prometheus/Alertmanager.
The real backup rules stay in place.

For an explicit recovery-notification test before cleanup, optionally run
`go-task backup-alerts:test -- resolve`, review/commit/push, and confirm the
RESOLVED message. This changes the expression to false while preserving the
rule's identity. Grouping can add up to five minutes after Prometheus observes
the change. Then run `remove` and deploy cleanup as above.

These tasks only edit local files; they do not deploy or send messages
themselves. Do not break R2 credentials or disable WAL archiving to test
delivery. `go-task telegram:test` only verifies direct bot delivery, not this
pipeline.

For real failures, follow the [backup runbook](postgres-backups.md) to inspect
Backup resources and R2 archives. An empty alert list is meaningful only after
scrapes and rule evaluation have been verified.

References:
[Barman metrics](https://cloudnative-pg.io/plugin-barman-cloud/docs/observability/),
[CNPG monitoring](https://cloudnative-pg.io/docs/1.30/monitoring/),
[chart source](https://github.com/prometheus-community/helm-charts/tree/kube-prometheus-stack-92.11.0/charts/kube-prometheus-stack),
[Alertmanager Telegram configuration](https://prometheus.io/docs/alerting/latest/configuration/#telegram_config).
