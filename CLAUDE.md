# Repository instructions

Keep [README.md](README.md) up to date with the cluster contents declared in this
repository. Whenever adding, removing, upgrading, configuring or moving a cluster
component, update its README entry, manifest links, versions, namespaces,
dependencies and relevant operational notes in the same change. Distinguish
configured functionality from planned work; do not claim live health without
checking it. Verify that relative documentation links resolve.

All Kubernetes cluster configuration changes must go through Git and Flux.
Do not apply, patch or delete live cluster resources directly; use kubectl for
read-only inspection and validation.

Keep README focused on declared architecture and stable operating guidance.
Update it for configuration or procedure changes, not rollout phases, status
transitions, command output or per-run resource IDs. Keep TODO focused on open
work; remove completed items instead of keeping completion narratives. Record
progress, dated evidence and outcomes in the global append-only CHANGELOG.
Runbooks contain repeatable procedures, not another progress log.

