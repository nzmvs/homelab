#!/usr/bin/env python3
"""Prompt for the homelab login password and write only SOPS ciphertext."""

import argparse
import base64
import getpass
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace", action="store_true",
                        help="replace the existing encrypted homelab login")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    destination = root / "apps/postgres/pg-homelab.sops.yaml"
    if destination.exists() and not args.replace:
        sys.exit("Secret already exists; pass --replace to set a new password.")
    if not sys.stdin.isatty():
        sys.exit("Run interactively in your terminal so the password stays hidden.")
    password = getpass.getpass("Password for homelab (hidden): ")
    confirmation = getpass.getpass("Confirm password (hidden): ")
    if not password:
        sys.exit("Password cannot be empty; nothing written.")
    if password != confirmation:
        sys.exit("Passwords do not match; nothing written.")
    secret = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": "pg-homelab", "namespace": "postgres",
            "labels": {"cnpg.io/reload": "true"},
        },
        "type": "kubernetes.io/basic-auth",
        "data": {
            "username": base64.b64encode(b"homelab").decode(),
            "password": base64.b64encode(password.encode()).decode(),
        },
    }
    # Plaintext is sent only through stdin; never argv, stdout or a disk file.
    result = subprocess.run(
        ["sops", "--encrypt", "--config", str(root / ".sops.yaml"),
         "--filename-override", str(destination), "--input-type", "json",
         "--output-type", "yaml", "/dev/stdin"],
        input=json.dumps(secret).encode(), capture_output=True,
    )
    if result.returncode:
        sys.exit("SOPS encryption failed; existing Secret unchanged.")
    if not all((key + ": ENC[AES256_GCM,").encode() in result.stdout
               for key in ("username", "password")):
        sys.exit("Encrypted credential fields not found; existing Secret unchanged.")
    # The temporary file contains ciphertext only; replace atomically.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write(result.stdout)
            output.flush()
            os.fsync(output.fileno())
        if args.replace:
            os.replace(temporary, destination)
        else:
            os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(f"Saved encrypted Secret: {destination}")
    print("Database/user: homelab. Not committed or deployed; deployment uses Flux.")


if __name__ == "__main__":
    main()
