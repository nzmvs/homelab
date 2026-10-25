#!/usr/bin/env python3
"""Prepare, resolve or remove a synthetic backup alert through local GitOps files."""
import argparse
from pathlib import Path
import re
import sys
import yaml

RESOURCE = 'backup-alert-test.yaml'
ALERT = 'PostgreSQLBackupAlertTest'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['fire', 'resolve', 'remove'])
    args = parser.parse_args()
    directory = Path(__file__).resolve().parents[2] / 'apps/postgres'
    path = directory / RESOURCE
    kustomization = directory / 'kustomization.yaml'
    original = kustomization.read_text()
    resources = yaml.safe_load(original).get('resources', [])
    if not isinstance(resources, list) or resources.count(RESOURCE) > 1:
        sys.exit('Unexpected Kustomization resources; nothing changed.')
    if path.exists():
        existing = yaml.safe_load(path.read_text())
        if (existing.get('kind') != 'PrometheusRule'
                or existing.get('metadata', {}).get('name') != 'pg-backup-alert-test'):
            sys.exit('Test file contains another resource; nothing changed.')
    if args.action == 'remove':
        updated = re.sub(r'^\s*- backup-alert-test\.yaml\s*\n', '', original, flags=re.MULTILINE)
        if RESOURCE in resources and updated == original:
            sys.exit('Cannot safely remove test resource entry; nothing changed.')
        kustomization.write_text(updated)
        path.unlink(missing_ok=True)
    else:
        if args.action == 'resolve' and not path.exists():
            sys.exit('No test exists. Prepare it with fire first.')
        rule = {
            'apiVersion': 'monitoring.coreos.com/v1', 'kind': 'PrometheusRule',
            'metadata': {'name': 'pg-backup-alert-test', 'namespace': 'postgres',
                         'labels': {'release': 'monitoring'}},
            'spec': {'groups': [{'name': 'pg-backup-alert-test', 'rules': [{
                'alert': ALERT,
                'expr': 'vector(1) == ' + ('1' if args.action == 'fire' else '0'),
                'for': '1m',
                'labels': {'severity': 'info', 'service': 'pg-backups'},
                'annotations': {
                    'summary': 'TEST: PostgreSQL backup alert delivery',
                    'description': 'Synthetic monitoring test. No actual backup failure.',
                },
            }]}]},
        }
        updated = original
        if RESOURCE not in resources:
            if 'resources:\n' not in original:
                sys.exit('Cannot safely add test resource entry; nothing changed.')
            updated = original.replace('resources:\n', 'resources:\n  - ' + RESOURCE + '\n', 1)
        path.write_text(yaml.safe_dump(rule, sort_keys=False))
        kustomization.write_text(updated)
    print('Prepared test action: ' + args.action)
    print('Local files only. Review, commit and push for Flux to deploy.')

if __name__ == '__main__':
    main()
