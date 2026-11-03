# Homepage landing page

[Homepage](https://gethomepage.dev/installation/k8s/) runs in namespace
`homepage`, managed by the existing apps Flux Kustomization. The image version
is pinned in [its Kustomization](../apps/homepage/kustomization.yaml).

## LAN addresses

Configure these records in your home DNS, all pointing to `192.168.0.40`:

| Name | URL | Purpose |
| --- | --- | --- |
| `homepage.k8s.lan` | http://homepage.k8s.lan | Landing page and Kubernetes status |
| `prometheus.k8s.lan` | http://prometheus.k8s.lan | Metrics and queries |
| `alertmanager.k8s.lan` | http://alertmanager.k8s.lan | Alerts and silences |

For a single computer, an alternative is to add the following to its hosts file:

```text
192.168.0.40 homepage.k8s.lan prometheus.k8s.lan alertmanager.k8s.lan
```

A hosts entry on this workstation does not configure your phone. For phone
access, use home DNS that resolves these names. No DNS records or hosts files
are changed by these manifests or tasks.

The existing RKE2 Traefik DaemonSet exposes host port 80 on the node. These
Ingresses use its `web` entrypoint and namespace-local `lan-only` middleware,
which permits source addresses in `192.168.0.0/24`. The namespace-local copies
avoid enabling Traefik cross-namespace middleware references. Keep their ranges
consistent if the LAN changes. Requests use the immediate client address, not
an arbitrary forwarded header. If a proxy or NAT changes that address, inspect
that network path before adjusting the allowlist.

This is HTTP on the home LAN. No public DNS, router port forwarding, TLS
certificate or Tailscale route is configured. Homepage has no login; Prometheus
and Alertmanager are also unauthenticated here, including Alertmanager silence
controls. The source-address rule restricts these routes to the trusted LAN;
it does not add encryption or user authentication. Keep internet port forwarding
disabled. Direct access from outside home is not part of this setup.

## Kubernetes access and configuration

The dedicated [ServiceAccount](../apps/homepage/service-account.yaml) uses
Kubernetes' automatically mounted, short-lived projected token. No manually
created service-account-token Secret or administrator kubeconfig is stored.
Its [ClusterRole](../apps/homepage/rbac.yaml) only grants `get`/`list` on
namespaces, pods, nodes, standard Ingresses and node/pod metrics. It cannot
read Secrets or change cluster resources. Cluster-wide reads support the
cluster widget and app discovery across namespaces.

The metrics widget uses the existing RKE2 metrics-server, not Prometheus.
Discovery uses standard Ingress annotations; Traefik IngressRoute and Gateway
API discovery are disabled. Monitoring owns [its two annotated Ingresses](../infrastructure/monitoring/ingress.yaml),
so links are declared beside the applications that provide them.

Homepage settings, bookmarks and widgets are separate files in
[`apps/homepage/config/`](../apps/homepage/config/). The ConfigMap generator
adds a content hash to its name, updating the Deployment reference when config
changes. An init container copies the mounted ConfigMap to writable ephemeral
storage; Homepage can create runtime files without changing the Git-managed
source. Restarts recreate that directory from Git. No PVC is required.

Both containers run as UID/GID 1000, with privilege escalation disabled,
capabilities dropped and a read-only root filesystem. Runtime configuration,
cache and temporary files use `emptyDir` volumes. Host validation explicitly
allows the LAN name, localhost forwarding and the pod IP used by health probes.

## Validate and deploy

From the repository root:

```sh
go-task homepage:check
```

This renders all manifests and checks whitespace, then runs the pinned image
in disposable local Docker containers. The smoke test reads the rendered
ConfigMap and Deployment, exercises the config-copy init command, and checks
startup, HTTP health, page rendering and rejection of an unknown Host header.
It temporarily disables Kubernetes integration only in the test copy: no
cluster token is passed to Docker. It needs Docker, Python/PyYAML, kubectl and
network access for the image. It does not validate live discovery, DNS, RBAC
or Ingress routing. The test cleans up its containers and temporary files.

Review the changes, commit/push and let Flux reconcile. No task applies,
commits, pushes or triggers reconciliation. Infrastructure creates the two
monitoring routes; apps creates Homepage after infrastructure is ready. Traefik
and its Middleware CRD are prerequisites supplied by this cluster's RKE2 setup.

## Verify after deployment

```sh
go-task homepage:status
go-task homepage:logs
go-task homepage:verify
```

Check that the Homepage Deployment is available and logs have no Kubernetes
permission errors. Open the LAN URL, confirm the Kubernetes widget loads and
both monitoring cards open the correct application.

`homepage:verify` checks Deployment availability, selected ServiceAccount
permissions, all three HTTP health endpoints through their actual LAN Ingresses,
and name resolution on the machine running the task. It reads the configured
routes rather than duplicating their hostnames in the task. HTTP routing is
checked with a Host header against the node IP, so a DNS failure is reported
separately. Run from the home LAN with an identity permitted to inspect the
ServiceAccount's permissions; it uses Kubernetes impersonation for those checks.
This does not test remote DNS, an outside-LAN denial or actual file delivery.

For local troubleshooting without DNS or Ingress:

```sh
go-task homepage:open
```

Open http://localhost:3000 and stop the forwarding with Ctrl+C. The monitoring
cards still point to LAN hostnames; this fallback does not tunnel those apps.
Use `KUBE_CONTEXT=...` to override the context for live tasks.

## Add another application

Add a standard Ingress in the app's own namespace with a reachable LAN hostname,
its namespace-local LAN middleware, and these annotations:

```yaml
gethomepage.dev/enabled: "true"
gethomepage.dev/name: My application
gethomepage.dev/group: Applications
gethomepage.dev/icon: homepage.png
gethomepage.dev/description: What this application does
```

Configure its LAN DNS record too. Homepage discovers the link; it does not
create network access or authenticate users to the target application. For
custom pod labels, set `gethomepage.dev/pod-selector` to the appropriate selector.
Keep credentials out of Ingress annotations and plaintext configuration.

## Remove

Remove `homepage` from `apps/kustomization.yaml` and its manifests through
Git/Flux. Remove the monitoring Ingress/middleware resources from their own
Kustomization as well if those LAN endpoints are no longer wanted. Flux prunes
the resources. Remove obsolete LAN DNS records separately; no persistent
Homepage data volume needs cleanup.
