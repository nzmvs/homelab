---
okf_version: "0.2"
---
# Homelab knowledge

[OKF v0.2](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md)
map of declared configuration, not live health. Distribute with this repository:
`../` source links resolve outside the bundle. Update affected concepts when
sources change; procedures stay in `docs/`.

- [Architecture](architecture.md) - Reconciliation order and platform dependencies.
- [Access](access.md) - HTTP entrypoints, discovery and the LAN trust boundary.
- [PostgreSQL](postgres.md) - Database identity, connectivity and retained local storage.
- [Backups](backups.md) - Remote recovery through Barman base backups and WAL.
- [Monitoring](monitoring.md) - Focused PostgreSQL monitoring and dashboard persistence.
- [Alerts](alerts.md) - Backup failure detection and separate Telegram delivery paths.
- [Operations](operations.md) - Repository entrypoints for changes, credentials and validation.
