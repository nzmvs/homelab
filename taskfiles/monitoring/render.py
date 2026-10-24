#!/usr/bin/env python3
"""Render monitoring using the chart version and values in its HelmRelease."""
from pathlib import Path
import subprocess
import tempfile
import yaml

def main():
    root = Path(__file__).resolve().parents[2]
    with (root / 'infrastructure/monitoring/helm.yaml').open() as source:
        documents = list(yaml.safe_load_all(source))
    release = next(item for item in documents if item.get('kind') == 'HelmRelease')
    chart = release['spec']['chart']['spec']
    repository = next(item['spec']['url'] for item in documents
                      if item.get('kind') == 'HelmRepository'
                      and item['metadata']['name'] == chart['sourceRef']['name'])
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as values:
        yaml.safe_dump(release['spec']['values'], values)
        values.flush()
        subprocess.run([
            'helm', 'template', release['spec']['releaseName'], chart['chart'],
            '--repo', repository, '--version', chart['version'],
            '--namespace', release['spec']['targetNamespace'], '--values', values.name,
        ], stdout=subprocess.DEVNULL, check=True)
    print('Monitoring chart rendered successfully.')

if __name__ == '__main__':
    main()
