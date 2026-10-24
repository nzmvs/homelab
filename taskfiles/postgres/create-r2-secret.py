#!/usr/bin/env python3
"""Prompt locally for R2 credentials and write only SOPS ciphertext."""

import getpass
import json
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[2]
    destination = root / "apps/postgres/r2-credentials.sops.yaml"
    if destination.exists():
        sys.exit(f"Already exists: {destination}; use sops to edit it.")
    if not sys.stdin.isatty():
        sys.exit("Run interactively in your terminal so credentials stay hidden.")
    access_key = getpass.getpass("R2 Access Key ID (hidden): ").strip()
    secret_key = getpass.getpass("R2 Secret Access Key (hidden): ").strip()
    if not access_key or not secret_key:
        sys.exit("Both credentials are required; nothing written.")
    secret = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": "r2-credentials", "namespace": "postgres"},
        "type": "Opaque",
        "stringData": {
            "ACCESS_KEY_ID": access_key,
            "ACCESS_SECRET_KEY": secret_key,
        },
    }
    # Pass plaintext through stdin, never through argv or a plaintext file.
    encrypted = subprocess.run(
        [
            "sops", "--encrypt", "--config", str(root / ".sops.yaml"),
            "--filename-override", str(destination),
            "--input-type", "json", "--output-type", "yaml", "/dev/stdin",
        ],
        input=json.dumps(secret).encode(), capture_output=True,
    )
    if encrypted.returncode:
        sys.exit("SOPS encryption failed; nothing written. Check SOPS and .sops.yaml.")
    if encrypted.stdout.count(b"ENC[AES256_GCM,") < 2:
        sys.exit("Encrypted credential fields were not found; nothing written.")
    with destination.open("xb") as output:
        output.write(encrypted.stdout)
    print(f"Created encrypted Secret: {destination}")
    print("Not deployed or added to Kustomize yet.")


if __name__ == "__main__":
    main()
