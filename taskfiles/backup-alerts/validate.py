#!/usr/bin/env python3
"""Validate backup rules/scenarios and encrypted Alertmanager config using Docker."""

from pathlib import Path
import subprocess
import sys
import tempfile

import yaml


def main():
    root = Path(__file__).resolve().parents[2]
    rule = yaml.safe_load((root / 'apps/postgres/backup-alerts.yaml').read_text())
    rules = rule['spec']['groups'][0]['rules']
    metric_labels = '{namespace="postgres",cluster="pg",pod="pg-1"}'
    healthy = {
        'barman_cloud_cloudnative_pg_io_last_available_backup_timestamp': 99999,
        'barman_cloud_cloudnative_pg_io_last_failed_backup_timestamp': 0,
        'cnpg_pg_stat_archiver_last_archived_time': 99999,
        'cnpg_pg_stat_archiver_last_failed_time': -1,
        'cnpg_pg_stat_archiver_seconds_since_last_archival': 30,
    }
    ready = 'cnpg_collector_pg_wal_archive_status{namespace="postgres",cluster="pg",pod="pg-1",value="ready"}'
    up = 'up{namespace="postgres",cluster="pg",pod="pg-1",monitored_service="pg-backups"}'

    def case(name, changes=None, missing=(), pending=0, scrape=1, expected=(), eval_time='20m'):
        metrics = healthy | (changes or {})
        series = [{'series': key + metric_labels, 'values': f'{value}+0x1800'}
                  for key, value in metrics.items() if key not in missing]
        series += [{'series': ready, 'values': f'{pending}+0x1800'},
                   {'series': up, 'values': f'{scrape}+0x1800'}]
        checks = []
        for item in rules:
            exp = []
            if item['alert'] in expected:
                labels = dict(item['labels'])
                if item['alert'] == 'PostgreSQLBackupMetricsMissing':
                    labels.update(namespace='postgres', cluster='pg')
                exp.append({'exp_labels': labels, 'exp_annotations': item['annotations']})
            checks.append({'eval_time': eval_time, 'alertname': item['alert'], 'exp_alerts': exp})
        return {'name': name, 'interval': '1m', 'input_series': series, 'alert_rule_test': checks}

    tests = [
        case('Healthy and idle database; no pending WAL'),
        case('Failed backup after success',
             {'barman_cloud_cloudnative_pg_io_last_failed_backup_timestamp': 100000},
             expected=('PostgreSQLBackupFailed',)),
        case('Success after an older failure clears the failure',
             {'barman_cloud_cloudnative_pg_io_last_failed_backup_timestamp': 99998}),
        case('Overdue base backup',
             {'barman_cloud_cloudnative_pg_io_last_available_backup_timestamp': 1},
             expected=('PostgreSQLBackupOverdue',), eval_time='30h'),
        case('No successful base backup yet',
             {'barman_cloud_cloudnative_pg_io_last_available_backup_timestamp': 0,
              'barman_cloud_cloudnative_pg_io_last_failed_backup_timestamp': 0},
             expected=('PostgreSQLBackupOverdue',), eval_time='30h'),
        case('WAL failure without recovery',
             {'cnpg_pg_stat_archiver_last_failed_time': 100000},
             expected=('PostgreSQLWALArchivingFailed',)),
        case('Pending WAL with stale archiving',
             {'cnpg_pg_stat_archiver_seconds_since_last_archival': 1200}, pending=2,
             expected=('PostgreSQLWALArchivingStalled',)),
        case('Pending WAL without any successful archival',
             {'cnpg_pg_stat_archiver_seconds_since_last_archival': -1}, pending=2,
             expected=('PostgreSQLWALArchivingStalled',)),
        case('Missing backup metric is not treated as healthy',
             missing=('barman_cloud_cloudnative_pg_io_last_available_backup_timestamp',),
             expected=('PostgreSQLBackupMetricsMissing',)),
        case('Exporter scrape fails', scrape=0, expected=('PostgreSQLMetricsUnavailable',)),
    ]
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary)
        path.chmod(0o755)  # promtool runs as an unprivileged container user.
        (path / 'rules.yaml').write_text(yaml.safe_dump(rule['spec']))
        (path / 'tests.yaml').write_text(yaml.safe_dump({
            'rule_files': ['rules.yaml'], 'evaluation_interval': '1m', 'tests': tests,
        }))
        subprocess.run([
            'docker', 'run', '--rm', '-v', f'{path}:/checks:ro', '-w', '/checks',
            '--entrypoint', '/bin/promtool', 'quay.io/prometheus/prometheus:v3.15.0-distroless',
            'test', 'rules', 'tests.yaml',
        ], check=True)
    decrypted = subprocess.run([
        'sops', '--decrypt', str(root / 'infrastructure/monitoring/alertmanager-config.sops.yaml'),
    ], capture_output=True, check=True)
    config = yaml.safe_load(decrypted.stdout)['stringData']['alertmanager.yaml']
    telegram = yaml.safe_load(config)['receivers'][1]['telegram_configs'][0]
    result = subprocess.run([
        'docker', 'run', '--rm', '-i', '--entrypoint', '/bin/amtool',
        'quay.io/prometheus/alertmanager:v0.34.1', 'check-config', '/dev/stdin',
    ], input=config.encode(), capture_output=True)
    for output in (result.stdout, result.stderr):
        print(output.decode(errors='replace').replace(telegram['bot_token'], '<REDACTED>'), end='')
    if result.returncode:
        sys.exit(result.returncode)
    print('Backup rule scenarios and Alertmanager config validated; no messages sent.')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(f'Validation command failed (exit {error.returncode}).')
