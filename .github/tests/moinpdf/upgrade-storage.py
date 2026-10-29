"""Check every persistent bind mount across the disposable native app update."""
import json
from pathlib import Path
import subprocess
import sys

mode = sys.argv[1]
assert mode in ('before', 'after')
root = '/home/umbrel/umbrel/app-data/denny-moinpdf/data'
directories = ('caddy-data', 'caddy-config', 'trust', 'translation-models',
               'translation-cache', 'document-jobs')
snapshot = Path('/tmp/moinpdf-upgrade-storage.json')
metadata = {}
for name in directories:
    directory = f'{root}/{name}'
    marker = f'{directory}/moinpdf-ci-upgrade-marker.txt'
    if mode == 'before':
        subprocess.run([
            'docker', 'exec', 'moinpdf-umbrel-test', 'sh', '-ec',
            'test -d "$1"; test ! -e "$2"; '
            'printf "Synthetic MoinPDF upgrade fixture\\n" > "$2"; '
            'chown 1000:1000 "$2"; chmod 640 "$2"',
            'fixture', directory, marker,
        ], check=True)
    metadata[name] = subprocess.check_output([
        'docker', 'exec', 'moinpdf-umbrel-test', 'sh', '-ec',
        'stat -c "%u:%g:%a" "$1" "$2"; sha256sum "$2"',
        'fixture', directory, marker,
    ], text=True)

if mode == 'before':
    snapshot.write_text(json.dumps(metadata))
else:
    assert metadata == json.loads(snapshot.read_text()), 'Persistent contents, owners or permissions changed'
    output = Path('umbrel-evidence/upgrade-storage.json')
    output.write_text(json.dumps({'from': '0.25.2', 'status': 'passed',
                                 'checks': ['file-bytes', 'file-owner-mode', 'directory-owner-mode'],
                                 'directories': list(directories)}, indent=2) + '\n')
    subprocess.run(['docker', 'exec', 'moinpdf-umbrel-test', 'rm', '--',
                    *(f'{root}/{name}/moinpdf-ci-upgrade-marker.txt' for name in directories)], check=True)
    snapshot.unlink()
    print('PASS: all six persistent directories retain existing file bytes, ownership and permissions.', flush=True)
