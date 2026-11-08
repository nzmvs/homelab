# Homelab

- Use `homelab` as the central task project label.
- Change Kubernetes configuration only through Git/Flux, including authorized
  deployments; never apply, patch or delete live resources directly.
- Live inspection, port-forwarding and diagnostics are allowed when they do
  not modify workloads or application data.
- Prepare and validate locally. Leave deployment to the user unless explicitly
  delegated. Commits, pushes, reconciliations and other remote mutations
  require explicit authorization.
- Expose repeatable runbook commands through modular go-task files, with
  helper scripts beside their Taskfile.
- Use Cloudflare MCP for R2 operations, not rclone.
- Keep README as a component/access index and procedures in `docs/`.
  Update affected documentation and verify links with configuration changes.
