---
type: Access Boundary
title: Access
description: HTTP entrypoints, discovery and the LAN trust boundary.
generated: {by: codex/gpt-6-astra, at: 2026-11-08T00:56:41Z}
sources:
  - resource: ../docs/homepage.md
  - resource: ../apps/homepage/ingress.yaml
  - resource: ../apps/homepage/lan-access.yaml
  - resource: ../apps/homepage/rbac.yaml
  - resource: ../infrastructure/monitoring/ingress.yaml
  - resource: ../infrastructure/monitoring/lan-access.yaml
  - resource: ../infrastructure/monitoring/helm.yaml
  - resource: ../apps/postgres/cluster.yaml
---
# Trust boundary

Client hosts entries map `homepage`, `prometheus`, `alertmanager` and `grafana`
under `k8s.lan` to `192.168.0.40`. Traefik serves HTTP with namespace-local
allowlists for `192.168.0.0/24`. These UIs require no login; Grafana grants
anonymous Editor access.

This ingress restriction does not cover the [PostgreSQL](postgres.md) NodePort,
whose Service declares no source-CIDR restriction.

Homepage discovers annotated [monitoring](monitoring.md) Ingresses. Its read-only
RBAC supports cluster and metrics-server widgets. See [client setup](../docs/homepage.md#lan-addresses).
