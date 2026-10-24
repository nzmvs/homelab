#!/usr/bin/env python3
"""Reuse the saved Telegram destination/token in an encrypted Alertmanager config."""

import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import yaml


def main():
    root = Path(__file__).resolve().parents[2]
    directory = root / 'infrastructure/monitoring'
    destination = directory / 'alertmanager-config.sops.yaml'
    provider = yaml.safe_load(
        (root / 'infrastructure/notifications/provider.yaml').read_text())
    try:
        chat_id = int(provider['spec']['channel'])
    except (ValueError, TypeError):
        sys.exit('Alertmanager requires a numeric chat ID. Re-run Telegram setup with chat discovery first.')
    result = subprocess.run(
        ['sops', '--decrypt', str(root / 'infrastructure/notifications/telegram-token.sops.yaml')],
        capture_output=True,
    )
    if result.returncode:
        sys.exit('Cannot decrypt the existing Telegram Secret; nothing written.')
    saved = yaml.safe_load(result.stdout)
    if 'token' in saved.get('stringData', {}):
        token = saved['stringData']['token']
    else:
        token = base64.b64decode(saved['data']['token'], validate=True).decode()
    if not token:
        sys.exit('Telegram token is empty; nothing written.')
    config = {
        'global': {'resolve_timeout': '5m'},
        'route': {
            'receiver': 'discard',
            'group_by': ['alertname', 'service'],
            'group_wait': '30s', 'group_interval': '5m', 'repeat_interval': '6h',
            'routes': [{'receiver': 'telegram', 'matchers': ['service="pg-backups"']}],
        },
        'receivers': [
            {'name': 'discard'},
            {'name': 'telegram', 'telegram_configs': [{
                'bot_token': token, 'chat_id': chat_id,
                'send_resolved': True, 'parse_mode': '',
                'message': '{{ range .Alerts }}[{{ .Status | toUpper }}] {{ .Annotations.summary }}\n{{ .Annotations.description }}\n{{ end }}',
            }]},
        ],
    }
    secret = {
        'apiVersion': 'v1', 'kind': 'Secret',
        'metadata': {'name': 'alertmanager-telegram', 'namespace': 'monitoring'},
        'type': 'Opaque',
        'stringData': {'alertmanager.yaml': yaml.safe_dump(config, sort_keys=False)},
    }
    encrypted = subprocess.run(
        ['sops', '--encrypt', '--config', str(root / '.sops.yaml'),
         '--filename-override', str(destination), '--input-type', 'json',
         '--output-type', 'yaml', '/dev/stdin'],
        input=json.dumps(secret).encode(), capture_output=True,
    )
    if encrypted.returncode or b'alertmanager.yaml: ENC[AES256_GCM,' not in encrypted.stdout:
        sys.exit('SOPS encryption failed; existing file unchanged.')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as output:
            temporary = Path(output.name)
            output.write(encrypted.stdout)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print('Saved encrypted Alertmanager configuration using existing Telegram settings.')
    print('No messages sent or resources deployed. Re-run after changing the bot or destination.')


if __name__ == '__main__':
    main()
