# Grafana

http://grafana.k8s.lan, with [LAN hosts setup](homepage.md#lan-addresses).
Anonymous **Editor** access permits dashboard creation, editing and deletion;
admin access is separate. The chart generates the admin credential internally.

## Check

```sh
go-task monitoring:check    # local chart and alert checks
go-task monitoring:status
go-task homepage:verify     # includes Grafana /api/health
```

Confirm the Grafana pod is Ready and PVC Bound. Fallback:
`go-task monitoring:grafana`, then http://localhost:3001.

## Dashboards

Prometheus is the default data source; Alertmanager is also provisioned.
In **Explore**, query `up` or `cnpg_collector_pg_wal_archive_status{value="ready"}`.
Generic Kubernetes dashboards are disabled alongside their exporters/scrapers.

Dashboard/data-source sidecars watch ConfigMaps in `monitoring`. Provision
Git-managed dashboards there with label `grafana_dashboard: "1"` and JSON in
`data`; include them in the monitoring Kustomization. Export UI-created
dashboards to JSON before committing them.

[Grafana configuration](../infrastructure/monitoring/helm.yaml) uses a retained
2Gi PVC for SQLite/settings and a `Recreate` deployment strategy. Upgrades briefly
interrupt Grafana. Storage is node-local, has no enforced quota and has no
configured backup; it does not hold Prometheus metrics.
