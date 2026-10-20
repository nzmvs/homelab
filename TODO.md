# TODO

| Item | State | Action |
| --- | --- | --- |
| `reclaimPolicy: Retain` | Deferred. `Delete` while testing. | Deleting a PVC runs `rm -rf` on the node. Set `storageClass.reclaimPolicy: Retain` under `values` in `infrastructure/local-path-provisioner.yaml` before real data lands. Retain also means manual cleanup of `/opt/local-path-provisioner`. |
| Notification alerts | Discussed, not scoped. | notification-controller already runs. Add a `Provider` and an `Alert` in `infrastructure/` to push reconcile failures to ntfy or Discord, so a failed backup reaches the phone. |
| db snapshots to R2 (Cloudflare) | Blocked on the R2 bucket and token. | Create the bucket and a bucket-scoped API token with Object Read and Write. Then add an `ObjectStore` with `destinationPath` and `endpointURL`, a `plugins` block on the Cluster with `isWALArchiver: true`, and a nightly `ScheduledBackup` with `method: plugin`. Replace the `sops-test` canary with the real credentials. Changing the Cluster spec restarts the single instance. |
| Explicit cluster-root Kustomization | Recommended; prioritize. | Add `clusters/homelab/kustomization.yaml` listing `flux-system`, `infrastructure.yaml` and `apps.yaml`, so local Kustomize builds use an explicit entry point. |
| Document manifest conventions | Recommended; prioritize. | Add a short README covering component layout, file boundaries, naming, reconciliation intervals, version pinning and namespace ownership. Explain that apps declare namespaces while infrastructure Helm releases create theirs. Preserve generated Flux formatting and source/dependency differences required by each component. |
| Separate Barman manifest | Recommended. | Move the Barman plugin HelmRelease from `infrastructure/cloudnative-pg.yaml` into its own file and include it in `infrastructure/kustomization.yaml`, preserving its source reference and dependencies. |
| Component directory layout | Consider as the repo grows. | Use one directory per component consistently across apps and infrastructure when the added structure becomes useful; avoid a large restructure at the current size. |
