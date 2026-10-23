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

The agent prepares and validates local files; the user runs deployment commands.
Do not commit, push, trigger reconciliations or perform remote mutations without
explicit user authorization. Use the connected Cloudflare MCP for R2 operations
rather than rclone.
