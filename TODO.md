# TODO

| Item | State | Action |
| --- | --- | --- |
| `reclaimPolicy: Retain` | Deferred. `Delete` while testing. | Deleting a PVC runs `rm -rf` on the node. Set `storageClass.reclaimPolicy: Retain` under `values` in `infrastructure/local-path-provisioner.yaml` before real data lands. Retain also means manual cleanup of `/opt/local-path-provisioner`. |
| Notification alerts | Discussed, not scoped. | notification-controller already runs. Add a `Provider` and an `Alert` in `infrastructure/` to push reconcile failures to ntfy or Discord, so a failed backup reaches the phone. |
| db snapshots to R2 (Cloudflare) | Blocked on the R2 bucket and token. | Create the bucket and a bucket-scoped API token with Object Read and Write. Then add an `ObjectStore` with `destinationPath` and `endpointURL`, a `plugins` block on the Cluster with `isWALArchiver: true`, and a nightly `ScheduledBackup` with `method: plugin`. Replace the `sops-test` canary with the real credentials. Changing the Cluster spec restarts the single instance. |
