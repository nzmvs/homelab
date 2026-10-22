# TODO

| Item | State | Action |
| --- | --- | --- |
| `reclaimPolicy: Retain` | Deferred. `Delete` while testing. | Deleting a PVC runs `rm -rf` on the node. Set `storageClass.reclaimPolicy: Retain` under `values` in `infrastructure/local-path-provisioner/helm.yaml` before real data lands. Retain also means manual cleanup of `/opt/local-path-provisioner`. |
| Notification alerts | Discussed, not scoped. | notification-controller already runs. Add a `Provider` and an `Alert` in `infrastructure/` to push reconcile failures to ntfy or Discord, so a failed backup reaches the phone. |
| db snapshots to R2 (Cloudflare) | Manifests prepared; deployment and backup/restore verification pending. | Private Standard bucket `homelab-postgres-backups` and encrypted credentials exist. PostgreSQL manifests declare Barman WAL archiving, immediate/nightly backups at 02:00 in the operator’s timezone and a seven-day recovery window. Deploy via Flux, verify a completed backup and perform the [restore drill](docs/postgres-backups.md). Enabling the plugin restarts the single instance. |
| Explicit cluster-root Kustomization | Done. | `clusters/homelab/kustomization.yaml` lists `flux-system`, `infrastructure.yaml` and `apps.yaml`; local builds have an explicit entry point. |
| Document manifest conventions | Done. | [README.md](README.md) documents cluster contents, component layout, namespace ownership, dependencies, reconciliation intervals, versions and validation. |
| Separate Barman manifest | Done. | Barman HelmRelease lives in `infrastructure/plugin-barman-cloud/helm.yaml`; its chart source and dependencies are preserved. |
| Component directory layout | Done. | Apps and infrastructure use component directories with child Kustomizations; infrastructure renders unchanged. |
| Create an Open Knowledge Format (OKF) description of the homelab | Open. | Document cluster components, relationships and operational context using the [Open Knowledge Format specification](https://github.com/GoogleCloudPlatform/open-knowledge-format). Link the resulting knowledge bundle from README.md. |
