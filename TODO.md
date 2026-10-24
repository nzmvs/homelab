# TODO

Outstanding work only. Completed outcomes and verification belong in
`~/Work/CHANGELOG.md` and Git history.

| Item | Remaining work |
| --- | --- |
| Notification alerts | notification-controller already runs. Add a `Provider` and an `Alert` in `infrastructure/` to push reconcile failures to ntfy or Discord, so a failed backup reaches the phone. |
| Create an Open Knowledge Format (OKF) description of the homelab | Document cluster components, relationships and operational context using the [Open Knowledge Format specification](https://github.com/GoogleCloudPlatform/open-knowledge-format). Link the resulting knowledge bundle from README.md. |
| Restore drill for fresh homelab database | Deploy pg-restore through Flux, verify homelab database/owner and any known records, then remove only the drill app through GitOps and verify its Delete-policy storage is cleaned up. Source pg and R2 archive remain unchanged. |
| Cilium LoadBalancer for LAN services | Configure a DHCP-excluded LAN IP pool and L2 announcement policy; verify installed Cilium version and kube-proxy replacement prerequisites, then migrate PostgreSQL LAN access from NodePort to a CNPG-managed LoadBalancer Service. |
