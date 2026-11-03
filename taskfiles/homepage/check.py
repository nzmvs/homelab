#!/usr/bin/env python3
"""Smoke-test the rendered Homepage image locally without cluster credentials."""
from http.client import HTTPException
from pathlib import Path
import subprocess
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

import yaml

ROOT = Path(__file__).resolve().parents[2]


def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=True, **kwargs).stdout


def main():
    objects = list(yaml.safe_load_all(run('kubectl', 'kustomize', str(ROOT / 'apps/homepage'))))
    deployment = next(obj for obj in objects if obj['kind'] == 'Deployment')
    configmap = next(obj for obj in objects if obj['kind'] == 'ConfigMap')
    spec = deployment['spec']['template']['spec']
    container = spec['containers'][0]
    image = container['image']
    ingress = next(obj for obj in objects if obj['kind'] == 'Ingress')
    host = ingress['spec']['rules'][0]['host']
    title = yaml.safe_load(configmap['data']['settings.yaml'])['title']
    health_path = container['readinessProbe']['httpGet']['path']
    security = spec['securityContext']
    user = f"{security['runAsUser']}:{security['runAsGroup']}"
    allowed = next(env['value'] for env in container['env'] if env['name'] == 'HOMEPAGE_ALLOWED_HOSTS')
    # Pod-IP substitution is performed by Kubernetes; use loopback for this test.
    allowed = allowed.replace('$(MY_POD_IP)', '127.0.0.1')
    name = 'homepage-check-' + uuid4().hex[:12]
    with tempfile.TemporaryDirectory(prefix='homepage-check-') as temporary:
        base = Path(temporary)
        base.chmod(0o755)
        source, config = base / 'source', base / 'config'
        source.mkdir(mode=0o755)
        config.mkdir(mode=0o777)
        config.chmod(0o777)
        for filename, content in configmap['data'].items():
            if filename.endswith('.yaml'):
                yaml.safe_load(content)
            (source / filename).write_text(content)
        # This test exercises startup, config loading and host validation offline.
        # It does not simulate Kubernetes API discovery or expose real tokens.
        (source / 'kubernetes.yaml').write_text('mode: disabled\n')
        source_mount = f'type=bind,src={source},dst=/config,readonly'
        config_mount = f'type=bind,src={config},dst=/app/config'
        init = spec['initContainers'][0]
        run('docker', 'run', '--rm', '--user', user, '--read-only',
            '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '--mount', source_mount, '--mount', config_mount,
            '--entrypoint', init['command'][0], init['image'], *init['command'][1:])
        started = False
        try:
            run('docker', 'run', '--rm', '--detach', '--name', name,
                '--user', user, '--read-only', '--cap-drop=ALL',
                '--security-opt=no-new-privileges', '--mount', config_mount,
                '--tmpfs', f"/tmp:uid={security['runAsUser']},gid={security['runAsGroup']}",
                '--tmpfs', f"/app/.next/cache:uid={security['runAsUser']},gid={security['runAsGroup']}",
                '--publish', '127.0.0.1::3000',
                '--env', 'HOSTNAME=0.0.0.0',
                '--env', 'HOMEPAGE_ALLOWED_HOSTS=' + allowed,
                image)
            started = True
            port = run('docker', 'port', name, '3000/tcp').strip().rsplit(':', 1)[1]
            endpoint = 'http://127.0.0.1:' + port
            deadline = time.monotonic() + 60
            while True:
                try:
                    request = Request(endpoint + health_path, headers={'Host': '127.0.0.1:3000'})
                    with urlopen(request, timeout=3) as response:
                        if response.status == 200:
                            break
                except (URLError, TimeoutError, ConnectionError, HTTPException):
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError('Homepage did not become healthy within 60 seconds')
                time.sleep(1)
            request = Request(endpoint, headers={'Host': host})
            with urlopen(request, timeout=15) as response:
                html = response.read().decode()
                if response.status != 200 or title not in html:
                    raise RuntimeError('Homepage did not render the configured page')
            request = Request(endpoint, headers={'Host': 'untrusted.example'})
            try:
                with urlopen(request, timeout=15):
                    raise RuntimeError('Homepage accepted an unconfigured Host header')
            except HTTPError as error:
                if error.code != 400:
                    raise
            log_result = subprocess.run(['docker', 'logs', name], capture_output=True, text=True, check=True)
            logs = log_result.stdout + log_result.stderr
            if 'EROFS' in logs or 'EACCES' in logs:
                raise RuntimeError('Homepage reported filesystem permission errors')
            print(f'{image}: startup, health, page rendering and host validation passed.')
            print('Kubernetes discovery, RBAC, LAN DNS and Ingress require post-deployment verification.')
        except Exception:
            if started:
                print(run('docker', 'logs', name))
            raise
        finally:
            if started:
                run('docker', 'stop', '--time', '5', name)
            # The non-root container may own its generated log/cache files.
            run('docker', 'run', '--rm', '--mount', config_mount, '--entrypoint', 'sh',
                image, '-c', 'rm -rf /app/config/* /app/config/.[!.]* /app/config/..?*')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr or error.stdout or str(error))
