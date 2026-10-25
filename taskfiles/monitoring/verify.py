#!/usr/bin/env python3
"""Read-only PostgreSQL monitoring checks via the Kubernetes service proxy."""
import argparse
import json
import math
from pathlib import Path
import shlex
import subprocess
import sys
from urllib.parse import quote, urlencode
import yaml

class Client:
    def __init__(self, kube, namespace):
        self.command = shlex.split(kube)
        self.namespace = namespace
        if not self.command:
            raise ValueError('KUBE command is empty')

    def request(self, service, port, path, raw=False):
        endpoint = ('/api/v1/namespaces/' + quote(self.namespace, safe='')
                    + '/services/' + service + ':' + str(port) + '/proxy' + path)
        result = subprocess.run(self.command + [
            '--request-timeout=20s',
            'get', '--raw', endpoint,
        ], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or 'Kubernetes API request failed')
        return result.stdout if raw else json.loads(result.stdout)

    def prometheus(self, path):
        result = self.request('monitoring-prometheus', 9090, path)
        if result.get('status') != 'success':
            raise RuntimeError(result.get('error', 'Prometheus API error'))
        return result['data']

def verify(client, expected):
    healthy = True
    targets = [t for t in client.prometheus('/api/v1/targets')['activeTargets']
               if t.get('labels', {}).get('monitored_service') == 'pg-backups']
    if not targets:
        print('FAIL: no PostgreSQL scrape target found.')
        healthy = False
    for target in targets:
        print('PostgreSQL target: ' + target.get('health', 'unknown'))
        if target.get('health') != 'up':
            print('  ' + target.get('lastError', 'No error detail'))
            healthy = False
    rules = {r['name']: r for g in client.prometheus('/api/v1/rules')['groups']
             for r in g['rules'] if 'name' in r}
    for name in expected:
        rule = rules.get(name)
        if rule is None:
            print('FAIL: missing rule ' + name)
            healthy = False
            continue
        print(name + ': ' + rule.get('state', 'unknown') + ', health=' + rule.get('health', 'unknown'))
        if rule.get('health') != 'ok' or rule.get('state') != 'inactive':
            healthy = False
        if rule.get('lastError'):
            print('  ' + rule['lastError'])
    test = rules.get('PostgreSQLBackupAlertTest')
    print('Synthetic test: ' + (test.get('state', 'unknown') if test else 'not loaded'))
    selector = '{namespace="postgres",cluster="pg"}'
    queries = {
        'Backup age (hours)': '(time() - max(barman_cloud_cloudnative_pg_io_last_available_backup_timestamp' + selector + ')) / 3600',
        'Last successful backup (Unix time)': 'max(barman_cloud_cloudnative_pg_io_last_available_backup_timestamp' + selector + ')',
        'Last failed backup (Unix time; 0 means none)': 'max(barman_cloud_cloudnative_pg_io_last_failed_backup_timestamp' + selector + ')',
        'Pending WAL segments': 'max(cnpg_collector_pg_wal_archive_status{namespace="postgres",cluster="pg",value="ready"})',
        'Last WAL archive (Unix time)': 'max(cnpg_pg_stat_archiver_last_archived_time' + selector + ')',
        'Last WAL failure (Unix time; -1 means none)': 'max(cnpg_pg_stat_archiver_last_failed_time' + selector + ')',
    }
    for label, query in queries.items():
        result = client.prometheus('/api/v1/query?' + urlencode({'query': query}))['result']
        if not result or not math.isfinite(float(result[0]['value'][1])):
            print('FAIL: missing or invalid metric: ' + label)
            healthy = False
        else:
            value = float(result[0]['value'][1])
            print(label + ': ' + (f'{value:.2f}' if 'hours' in label else str(value)))
    metrics = client.request('monitoring-alertmanager', 9093, '/metrics', raw=True)
    for name, label in [
        ('alertmanager_notifications_total', 'Telegram attempts'),
        ('alertmanager_notifications_failed_total', 'Telegram failures'),
    ]:
        values = [float(line.rsplit(' ', 1)[1]) for line in metrics.splitlines()
                  if line.startswith(name + '{') and 'integration="telegram"' in line]
        print(label + ' (cumulative): ' + (str(sum(values)) if values else 'not exposed'))
    alerts = client.request('monitoring-alertmanager', 9093, '/api/v2/alerts')
    selected = [a for a in alerts if a.get('labels', {}).get('service') == 'pg-backups']
    print('Alertmanager backup alerts: ' + (', '.join(
        a['labels'].get('alertname', 'unknown') + ' (' + a.get('status', {}).get('state', 'unknown') + ')'
        for a in selected) or 'none'))
    print('Counters alone do not prove phone receipt or identify a resolved notification.')
    return 0 if healthy else 1

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kube', default='kubectl --context homelab')
    parser.add_argument('--namespace', default='monitoring')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    try:
        config = yaml.safe_load((root / 'apps/postgres/backup-alerts.yaml').read_text())
        expected = [r['alert'] for group in config['spec']['groups'] for r in group['rules']]
        return verify(Client(args.kube, args.namespace), expected)
    except (RuntimeError, ValueError, KeyError, OSError) as error:
        print(type(error).__name__ + ': ' + str(error), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
