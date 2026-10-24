#!/usr/bin/env python3
"""Prepare Telegram Flux alerts locally, prompting for credentials privately."""

import argparse
import getpass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

import yaml


def discover_channel(token):
    print('Open your bot in Telegram and press Start (or send it a new message).')
    input('Press Enter here when done: ')
    while True:
        try:
            # Do not advance the update offset or expose token-bearing URLs/errors.
            with urllib.request.urlopen(
                'https://api.telegram.org/bot' + token + '/getUpdates', timeout=15
            ) as response:
                payload = json.load(response)
            if not payload.get('ok'):
                raise ValueError('API rejected request')
            chats = {}
            for update in payload['result']:
                for key in ('message', 'channel_post'):
                    chat = update.get(key, {}).get('chat', {})
                    if isinstance(chat.get('id'), int):
                        chats[str(chat['id'])] = chat
        except urllib.error.HTTPError as error:
            if error.code == 409:
                sys.exit('Chat lookup conflicts with an existing webhook or update consumer. '
                         'Use a dedicated bot or --chat-id. Nothing written.')
            sys.exit('Telegram lookup failed; check the token and connectivity. Nothing written.')
        except Exception:
            sys.exit('Telegram lookup failed; check the token and connectivity. Nothing written.')
        if chats:
            choices = list(chats)
            for index, chat_id in enumerate(choices, 1):
                chat = chats[chat_id]
                label = chat.get('title') or chat.get('first_name') or chat.get('username') or 'Chat'
                print(f"{index}. {json.dumps(label)} ({chat.get('type', 'chat')}, {chat_id})")
            if len(choices) == 1:
                if input('Use this chat for alerts? [Y/n]: ').strip().lower() in ('', 'y', 'yes'):
                    return choices[0]
                sys.exit('Cancelled; nothing written.')
            selection = input('Choose destination number: ').strip()
            if selection.isdigit() and 1 <= int(selection) <= len(choices):
                return choices[int(selection) - 1]
            print('Choose one of the listed numbers.')
        else:
            print('No chats found yet. Send a fresh message to the bot in Telegram.')
            if input('Press Enter to retry, or q to cancel: ').strip().lower() == 'q':
                sys.exit('Cancelled; nothing written.')


def atomic_write(path, content):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replace', action='store_true',
                        help='replace existing Telegram credentials and destination')
    parser.add_argument('--chat-id', help='use a known chat ID or @channel instead of discovery')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    directory = root / 'infrastructure/notifications'
    destination = directory / 'telegram-token.sops.yaml'
    provider_path = directory / 'provider.yaml'
    parent = root / 'infrastructure/kustomization.yaml'
    original = parent.read_text()
    if destination.exists() or provider_path.exists():
        if not args.replace:
            sys.exit('Telegram configuration exists; pass --replace to update it.')
    if '  # - notifications\n' not in original and '  - notifications\n' not in original:
        sys.exit('Notifications entry missing from infrastructure Kustomization; nothing written.')
    if not sys.stdin.isatty():
        sys.exit('Run interactively in your terminal so the token stays hidden.')
    token = getpass.getpass('Telegram bot token (hidden): ').strip()
    if not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]+', token):
        sys.exit('Invalid bot token format; nothing written.')
    channel = args.chat_id.strip() if args.chat_id else discover_channel(token)
    if not re.fullmatch(r'-?[0-9]+(?::[0-9]+)?|@[A-Za-z0-9_]+', channel):
        sys.exit('Invalid destination format; nothing written.')
    secret = {
        'apiVersion': 'v1', 'kind': 'Secret',
        'metadata': {'name': 'telegram-token', 'namespace': 'flux-system'},
        'type': 'Opaque', 'stringData': {'token': token},
    }
    result = subprocess.run(
        ['sops', '--encrypt', '--config', str(root / '.sops.yaml'),
         '--filename-override', str(destination), '--input-type', 'json',
         '--output-type', 'yaml', '/dev/stdin'],
        input=json.dumps(secret).encode(), capture_output=True,
    )
    if result.returncode or b'token: ENC[AES256_GCM,' not in result.stdout:
        sys.exit('SOPS encryption failed; configuration unchanged.')
    provider = {
        'apiVersion': 'notification.toolkit.fluxcd.io/v1beta3', 'kind': 'Provider',
        'metadata': {'name': 'telegram', 'namespace': 'flux-system'},
        'spec': {'type': 'telegram', 'channel': channel,
                 'secretRef': {'name': 'telegram-token'}},
    }
    # Only ciphertext is written for the token.
    atomic_write(destination, result.stdout)
    atomic_write(provider_path, yaml.safe_dump(provider, sort_keys=False).encode())
    # Enable the component last, after all referenced files exist.
    atomic_write(parent, original.replace('  # - notifications\n',
                                          '  - notifications\n').encode())
    print('Prepared Telegram Provider, encrypted Secret and Flux error Alert.')
    print('No messages sent or resources deployed. Review, commit and deploy through Flux.')


if __name__ == '__main__':
    main()
