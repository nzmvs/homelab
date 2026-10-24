#!/usr/bin/env python3
"""Send one Telegram test message using the saved Provider and encrypted token."""

import base64
import json
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request

import yaml


def main():
    root = Path(__file__).resolve().parents[1]
    token = ''

    def report(value):
        # Telegram puts the credential in the request URL; never print it.
        text = str(value)
        if token:
            text = text.replace(token, '<REDACTED>')
        print(text, file=sys.stderr)

    try:
        provider = yaml.safe_load(
            (root / 'infrastructure/notifications/provider.yaml').read_text())
        result = subprocess.run(
            ['sops', '--decrypt', str(root / 'infrastructure/notifications/telegram-token.sops.yaml')],
            capture_output=True, text=True,
        )
        if result.returncode:
            report(f'SOPS failed (exit {result.returncode}):\n{result.stderr}')
            return 1
        secret = yaml.safe_load(result.stdout)
        if 'token' in secret.get('stringData', {}):
            token = secret['stringData']['token']
        else:
            token = base64.b64decode(secret['data']['token'], validate=True).decode()
        if not token:
            raise ValueError('The saved bot token is empty.')
        request = urllib.request.Request(
            f'https://api.telegram.org/bot{token}/sendMessage',
            data=json.dumps({
                'chat_id': provider['spec']['channel'],
                'text': 'Homelab test: Telegram alerts are working!',
            }).encode(),
            headers={'Content-Type': 'application/json'},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
        if not payload.get('ok'):
            report('Telegram rejected the request:\n' + json.dumps(payload, indent=2))
            return 1
        print(f"Test message sent (message ID: {payload['result']['message_id']}).")
        return 0
    except urllib.error.HTTPError as error:
        report(f'{type(error).__name__}: {error}')
        report(f'Request URL: {error.url}')
        report(f'Response headers:\n{error.headers}')
        try:
            report('Response body:\n' + error.read().decode('utf-8', errors='replace'))
        except Exception as body_error:
            report(f'Unable to read response body: {type(body_error).__name__}: {body_error}')
        return 1
    except Exception as error:
        report(f'{type(error).__name__}: {error}')
        if isinstance(error, urllib.error.URLError):
            report(f'Underlying error: {type(error.reason).__name__}: {error.reason}')
        report('Delivery is unconfirmed; no automatic retry was performed.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
