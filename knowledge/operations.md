---
type: Repository Workflow
title: Operations
description: Repository entrypoints for changes, credentials and validation.
generated: {by: codex/gpt-6-astra, at: 2026-11-08T00:56:41Z}
sources:
  - resource: ../AGENTS.md
  - resource: ../Taskfile.yml
  - resource: ../taskfiles/validate/Taskfile.yml
  - resource: ../taskfiles/knowledge/Taskfile.yml
  - resource: ../.sops.yaml
  - resource: ../docs/telegram-alerts.md
---
# Entry points

[Repository policy](../AGENTS.md) governs Git/Flux changes and deployment ownership.
`go-task --list` exposes modular runbooks; `go-task validate` renders manifests.
`go-task knowledge:check` checks this bundle. Live task defaults target context `homelab`.

SOPS encrypts Secret `data`/`stringData` with age; credential helpers prepare
local encrypted manifests. [Telegram rotation](../docs/telegram-alerts.md) must
refresh the separate [alert pipelines](alerts.md).

Consult the [recovery runbook](../docs/postgres-backups.md) before database recovery;
[architecture](architecture.md) explains reconciliation dependencies. Keep procedures
there and update linked concepts when their sources change.
