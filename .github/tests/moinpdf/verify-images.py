"""Verify the public, digest-pinned images used by this store package."""
import json
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parents[3]
package = root / 'denny-moinpdf'
manifest = (package / 'umbrel-app.yml').read_text()
version = re.search(r'^version: "?(\d+\.\d+\.\d+)"?$', manifest, re.M).group(1)
compose = (package / 'docker-compose.yml').read_text()
sources = set()
for name in ('web', 'documents', 'translation', 'website'):
    references = set(re.findall(rf'ghcr\.io/moinpdf/moinpdf-{name}:[^\s]+', compose))
    assert len(references) == 1, f'{name}: expected one unique image reference'
    reference = references.pop()
    match = re.fullmatch(rf'ghcr\.io/moinpdf/moinpdf-{name}:{re.escape(version)}-([0-9a-f]{{12}})@sha256:[0-9a-f]{{64}}', reference)
    assert match, f'{name}: version, source tag or digest is missing'
    sources.add(match.group(1))
    index = json.loads(subprocess.check_output(
        ['docker', 'buildx', 'imagetools', 'inspect', reference, '--raw'], text=True))
    platforms = {(entry['platform']['os'], entry['platform']['architecture'])
                 for entry in index.get('manifests', []) if 'platform' in entry}
    assert {('linux', 'amd64'), ('linux', 'arm64')} <= platforms, f'{name}: missing platform'
    print(f'PASS: {name}, version {version}, public digest and both platform manifests.', flush=True)
source = json.loads((Path(__file__).parent / 'asset-checksums.json').read_text())['source']
assert sources == {source[:12]}, 'All four images and asset checks must come from the released source commit'
