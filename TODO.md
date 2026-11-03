# TODO

Outstanding work only. Completed outcomes and verification belong in
`~/Work/CHANGELOG.md` and Git history.

| Item | Remaining work |
| --- | --- |
| Create an Open Knowledge Format (OKF) description of the homelab | Document cluster components, relationships and operational context using the [Open Knowledge Format specification](https://github.com/GoogleCloudPlatform/open-knowledge-format). Link the resulting knowledge bundle from README.md. |
| Populated-data restore test | Once application data exists, follow the [restore runbook](docs/postgres-backups.md#restore-drill) and compare known tables and records, then remove the temporary cluster through GitOps. |
| Cilium LoadBalancer for LAN services | Configure a DHCP-excluded LAN IP pool and L2 announcement policy; verify installed Cilium version and kube-proxy replacement prerequisites, then migrate PostgreSQL LAN access from NodePort to a CNPG-managed LoadBalancer Service. |
