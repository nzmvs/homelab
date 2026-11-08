# PostgreSQL backup alerts

[Rules](../apps/postgres/backup-alerts.yaml) and the
[PodMonitor](../apps/postgres/pod-monitor.yaml) target `postgres/pg`.
Scrape/evaluation interval: 60s. Selected rules require `release: monitoring`.

## Thresholds

| Alert | Condition | Hold |
| --- | --- | --- |
| PostgreSQLBackupFailed | Latest failure newer than latest success | 5m |
| PostgreSQLBackupOverdue | Latest success older than 26h, or zero | 5m |
| PostgreSQLWALArchivingFailed | Latest archive failure newer than success | 10m |
| PostgreSQLWALArchivingStalled | Pending WAL; no success for 10m or never | 10m |
| PostgreSQLBackupMetricsMissing | Required backup/WAL metric absent | 15m |
| PostgreSQLMetricsUnavailable | All targets down or absent | 5m |

Telegram routing requires `service: pg-backups`. Initial wait: 30s; group
interval: 5m; repeat: 6h. Recovery messages are enabled; routine backup success
messages are not. These delays follow scrape/evaluation and rule hold times.

## Validate and inspect

```sh
go-task monitoring:check    # render + promtool scenarios + amtool config check
go-task monitoring:verify   # live targets, rules, metrics and delivery counters
go-task monitoring:status
go-task monitoring:logs     # Alertmanager
```

The live check uses the Kubernetes service proxy. Delivery counters do not
prove phone receipt. An empty alert list is meaningful only with healthy
scrapes and rule evaluation. The stack cannot notify during a complete host
or network outage.

[LAN UIs](homepage.md#lan-addresses), or forward locally:

```sh
go-task monitoring:prometheus     # localhost:9090
go-task monitoring:alertmanager   # localhost:9093
```

Check `/targets` and `/rules` in Prometheus. Useful queries:

```promql
barman_cloud_cloudnative_pg_io_last_available_backup_timestamp{namespace="postgres",cluster="pg"}
barman_cloud_cloudnative_pg_io_last_failed_backup_timestamp{namespace="postgres",cluster="pg"}
cnpg_pg_stat_archiver_last_archived_time{namespace="postgres",cluster="pg"}
cnpg_pg_stat_archiver_last_failed_time{namespace="postgres",cluster="pg"}
cnpg_collector_pg_wal_archive_status{namespace="postgres",cluster="pg",value="ready"}
```

## Credentials

After changing the [Telegram bot/destination](telegram-alerts.md), run
`go-task monitoring:credentials` and deploy the updated SOPS file through Flux.
Alertmanager's configuration includes the token and numeric chat ID, encrypted
in [alertmanager-config.sops.yaml](../infrastructure/monitoring/alertmanager-config.sops.yaml).

## End-to-end test

Each step edits local manifests. Validate, review and deploy each stage through
Git/Flux before proceeding:

1. `go-task backup-alerts:test -- fire`. Wait for the TEST firing message
   (usually 2–3 minutes after discovery; rule hold: 1m).
2. `go-task backup-alerts:test -- resolve`. Confirm RESOLVED; grouping can add
   up to five minutes after Prometheus observes the change.
3. `go-task backup-alerts:test -- remove`. Verify the temporary rule disappears
   and its alert clears. Keep the real backup rules.

Run `go-task validate` after each edit. The temporary rule is
`PostgreSQLBackupAlertTest`, in `apps/postgres/backup-alert-test.yaml`.
Removing it directly after firing is also supported; explicit resolution makes
the recovery test easier to observe.

Do not break R2 credentials or WAL archiving to test delivery.
`telegram:test` exercises only direct bot delivery, not this pipeline.
For real failures, use the [backup runbook](postgres-backups.md).
