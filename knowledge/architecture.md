---
type: Architecture
title: Architecture
description: Reconciliation order and platform dependencies.
generated: {by: codex/gpt-6-astra, at: 2026-11-08T00:56:41Z}
sources:
  - resource: ../README.md
  - resource: ../clusters/homelab/flux-system/gotk-sync.yaml
  - resource: ../clusters/homelab/infrastructure.yaml
  - resource: ../clusters/homelab/apps.yaml
  - resource: ../infrastructure/plugin-barman-cloud/helm.yaml
  - resource: ../docs/homepage.md
---
# Dependency chain

Flux tracks `main` of `nzmvs/homelab` and reconciles `clusters/homelab`.
Infrastructure readiness gates apps: [PostgreSQL](postgres.md) and
[Homepage](access.md). Barman explicitly depends on cert-manager and
CloudNativePG; [monitoring](monitoring.md) belongs to infrastructure.

RKE2 is the documented platform. Traefik ingress and metrics-server are
assumed dependencies whose installation is outside this repository.
Both infrastructure and apps decrypt SOPS resources through `flux-system/sops-age`;
[operations](operations.md) owns the change workflow.
