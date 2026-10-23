# TODO

| Item | State | Action |
| --- | --- | --- |
| `reclaimPolicy: Retain` | Deferred. `Delete` while testing. | Deleting a PVC runs `rm -rf` on the node. Set `storageClass.reclaimPolicy: Retain` under `values` in `infrastructure/local-path-provisioner/helm.yaml` before real data lands. Retain also means manual cleanup of `/opt/local-path-provisioner`. |
| Notification alerts | Discussed, not scoped. | notification-controller already runs. Add a `Provider` and an `Alert` in `infrastructure/` to push reconcile failures to ntfy or Discord, so a failed backup reaches the phone. |
| db snapshots to R2 (Cloudflare) | Done; restore check accepted for current empty homelab database. | Backup and WAL objects verified in R2. User reports restored cluster running; source and restore both list `app` and `postgres`, and `app` has no user tables in either. User accepted this scope on 2026-10-23; recovery of populated tables/records remains untested. |
| Explicit cluster-root Kustomization | Done. | `clusters/homelab/kustomization.yaml` lists `flux-system`, `infrastructure.yaml` and `apps.yaml`; local builds have an explicit entry point. |
| Document manifest conventions | Done. | [README.md](README.md) documents cluster contents, component layout, namespace ownership, dependencies, reconciliation intervals, versions and validation. |
| Separate Barman manifest | Done. | Barman HelmRelease lives in `infrastructure/plugin-barman-cloud/helm.yaml`; its chart source and dependencies are preserved. |
| Component directory layout | Done. | Apps and infrastructure use component directories with child Kustomizations; infrastructure renders unchanged. |
| Create an Open Knowledge Format (OKF) description of the homelab | Open. | Document cluster components, relationships and operational context using the [Open Knowledge Format specification](https://github.com/GoogleCloudPlatform/open-knowledge-format). Link the resulting knowledge bundle from README.md. |
| Clean up restore drill app | Open. | Remove `apps/pg-restore` and its parent Kustomization entry through GitOps, then verify only restore-test resources/PVCs are removed; preserve `pg` and its backups. |
| Cilium LoadBalancer for LAN services | Open. | Configure a DHCP-excluded LAN IP pool and L2 announcement policy; verify installed Cilium version and kube-proxy replacement prerequisites, then migrate PostgreSQL LAN access from NodePort to a CNPG-managed LoadBalancer Service. |
