# Homepage

## LAN addresses

Add to each client's hosts file:

```text
192.168.0.40 k8s.lan homepage.k8s.lan prometheus.k8s.lan alertmanager.k8s.lan grafana.k8s.lan
```

Open http://homepage.k8s.lan. Traefik serves HTTP on port 80 and allows
`192.168.0.0/24` through namespace-local `lan-only` middleware. If the LAN
changes, update both [Homepage](../apps/homepage/lan-access.yaml) and
[monitoring](../infrastructure/monitoring/lan-access.yaml) allowlists.
A 403 warrants checking the client address seen by Traefik, including NAT/proxies.

These pages require no login; [Grafana](grafana.md) allows anonymous editing.
Hosts entries apply only to the client being edited.

## Check

```sh
go-task homepage:check       # local container smoke test; Kubernetes integration disabled
go-task homepage:status
go-task homepage:logs
go-task homepage:verify      # live RBAC, Ingress health and local name resolution
```

Run live verification from the LAN with permission to impersonate Homepage's
ServiceAccount. Confirm the cluster widget and application links in the browser;
the check does not test outside-LAN denial.

Fallback: `go-task homepage:open`, then http://localhost:3000. App links still
require their LAN hostnames.

## Configuration and discovery

Edit [config files](../apps/homepage/config/). Changes roll the Deployment;
runtime files are ephemeral. Kubernetes integration uses the
[read-only ServiceAccount](../apps/homepage/rbac.yaml); the widget reads
metrics-server, not Prometheus.

To add an app, follow the [monitoring Ingresses](../infrastructure/monitoring/ingress.yaml):
standard Ingress, namespace-local LAN middleware and `gethomepage.dev/enabled`,
`name` and `group` annotations. Add the hostname to client hosts files.
Use `gethomepage.dev/pod-selector` for nonstandard pod labels.
Traefik IngressRoute and Gateway API discovery are disabled.
