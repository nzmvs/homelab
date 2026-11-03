#!/usr/bin/env python3
"""Read-only check of Homepage readiness, LAN routes and service-account access."""
import argparse
import json
from pathlib import Path
import shlex
import socket
import subprocess
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener

import yaml

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kube', required=True)
    parser.add_argument('--namespace', required=True)
    args = parser.parse_args()
    kube = shlex.split(args.kube)

    def get(*arguments):
        result = subprocess.run([*kube, *arguments, '--request-timeout=10s', '-o', 'json'],
                                capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    deployment = get('-n', args.namespace, 'get', 'deployment', 'homepage')
    if deployment.get('status', {}).get('availableReplicas', 0) < 1:
        raise RuntimeError('Homepage is not available; inspect homepage:status and homepage:logs')
    account = deployment['spec']['template']['spec']['serviceAccountName']
    identity = f'system:serviceaccount:{args.namespace}:{account}'
    for verb, resource, expected in [('list', 'pods', True), ('list', 'nodes', True),
                                     ('list', 'ingresses.networking.k8s.io', True),
                                     ('list', 'nodes.metrics.k8s.io', True),
                                     ('get', 'secrets', False), ('delete', 'pods', False)]:
        result = subprocess.run([*kube, 'auth', 'can-i', verb, resource, '--as', identity,
                                 '-n', args.namespace, '--request-timeout=10s'],
                                capture_output=True, text=True)
        answer = result.stdout.strip()
        if result.returncode not in (0, 1) or answer not in ('yes', 'no'):
            raise RuntimeError(result.stderr.strip() or 'Cannot inspect ServiceAccount permissions')
        if (answer == 'yes') != expected:
            raise RuntimeError(f'Unexpected permission: {identity} {verb} {resource}: {answer}')
    print('Homepage available; read-only ServiceAccount checks passed.')
    nodes = get('get', 'nodes')['items']
    node_address = next(address['address'] for node in nodes
                        for address in node['status']['addresses'] if address['type'] == 'InternalIP')
    opener = build_opener(ProxyHandler({}))
    checks = [('apps/homepage/ingress.yaml', '/api/healthcheck'),
              ('infrastructure/monitoring/ingress.yaml', '/-/ready')]
    failures = []
    for filename, health_path in checks:
        for desired in yaml.safe_load_all((ROOT / filename).read_text()):
            metadata = desired['metadata']
            live = get('-n', metadata['namespace'], 'get', 'ingress', metadata['name'])
            host = live['spec']['rules'][0]['host']
            path = '/api/health' if metadata['name'] == 'grafana' else health_path
            try:
                request = Request(f'http://{node_address}{path}', headers={'Host': host})
                with opener.open(request, timeout=10) as response:
                    if response.status != 200:
                        raise RuntimeError(f'HTTP {response.status}')
                print(f'{host}: LAN Ingress health passed (without DNS).')
                addresses = {item[4][0] for item in socket.getaddrinfo(host, 80, socket.AF_INET)}
                if node_address not in addresses:
                    raise RuntimeError(f'DNS does not resolve to {node_address}')
                print(f'{host}: local DNS resolves to the node.')
            except (URLError, OSError, RuntimeError) as error:
                failures.append(f'{host}: {error}')
    if failures:
        raise RuntimeError('\n'.join(failures))
    print('Open the landing page to confirm discovered cards and Kubernetes widget data.')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr or str(error))
    except (RuntimeError, StopIteration) as error:
        raise SystemExit(str(error) or 'No node InternalIP found')
