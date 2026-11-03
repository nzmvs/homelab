# Grafana

Grafana is enabled in the existing [monitoring HelmRelease](../infrastructure/monitoring/helm.yaml)
using the pinned kube-prometheus-stack chart. It runs in `monitoring` with
Service and Deployment name `monitoring-grafana`.

## LAN access

Open http://grafana.k8s.lan after deployment. Add `grafana.k8s.lan` to your home
DNS pointing to `192.168.0.40`, or add it to your workstation hosts file alongside
the other [LAN app names](homepage.md#lan-addresses). These changes do not edit
hosts files or DNS automatically.

The [Ingress](../infrastructure/monitoring/ingress.yaml) uses the existing
`monitoring-lan-only` Traefik middleware, restricting source addresses to
`192.168.0.0/24`. Its Homepage annotations add a Grafana card automatically.
The route uses HTTP, with anonymous access assigned the Grafana **Editor** role.
People who can reach it can explore metrics and create, change or delete
organization dashboards without signing in. Anonymous users are not Grafana
administrators. Account sign-up is disabled.

The chart generates an internal admin password in a Kubernetes Secret; no
admin password is supplied in Git or required for this initial workflow. The
admin account remains available for future settings/user administration. No
anonymous Admin role is granted. Access restrictions on the Ingress do not
restrict other pods from reaching the ClusterIP Service.

## Data sources and dashboards

The chart provisions the existing Prometheus as the default data source and
Alertmanager as another data source. Grafana queries these services inside the
cluster. Begin in **Explore**, select **Prometheus**, and query `up` or
`cnpg_collector_pg_wal_archive_status{value="ready"}` for currently collected data. Grafana does
not copy the Prometheus database into its own volume.

The chart's generic Kubernetes dashboards are disabled because the matching
cluster exporters/scrapers are disabled in this homelab. Enabling Grafana does
not turn those on. Dashboard and data-source sidecars watch ConfigMaps only in
`monitoring`. To provision a dashboard through Git, add a ConfigMap there with
label `grafana_dashboard: "1"` and dashboard JSON under `data`, and include it
in the monitoring Kustomization. Grafana UI-created dashboards are stored in
its database; export important ones to JSON and commit them for reproducibility.

Loki, Alloy and centralized log collection are not installed by this change.

## Storage

Grafana requests a 2Gi ReadWriteOnce PVC using `local-path-retain` for its SQLite
database, users and UI-created dashboards. Retain preserves the underlying PV
if the claim is deleted; reattachment requires manual recovery. It is node-local
storage and not an off-node backup. Requested sizes are not enforced quotas by
the local-path provisioner. No Grafana database backup is configured yet.

The Deployment uses `Recreate` so upgrades do not start two Grafana instances
sharing the SQLite database/PVC. Expect a short dashboard outage during an
upgrade. Prometheus and Alertmanager continue running separately.

## Validate and deploy

From the repository root:

```sh
go-task monitoring:check
```

Review and deploy through the normal Git/Flux workflow. This task renders the
pinned monitoring chart and checks the existing alert rules/configuration;
it does not deploy resources or establish live Grafana health.

## Verify after deployment

```sh
go-task monitoring:status
go-task homepage:verify
```

Confirm the Grafana pod is Ready and its retained PVC is Bound. The Homepage
verification includes Grafana's `/api/health` through its LAN Ingress and local
DNS resolution. Open its Homepage card, confirm no login is required, then
check the Prometheus and Alertmanager data sources.

If DNS is not yet configured, use the forwarding task:

```sh
go-task monitoring:grafana
```

Open http://localhost:3001. The task forwards only on localhost and runs until
Ctrl+C. It does not change LAN DNS or the Ingress allowlist.
