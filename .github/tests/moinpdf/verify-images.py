"""Verify release assets, registry digests and both native image configurations."""
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def fetch(url, headers=None):
    for attempt in range(3):
        try:
            request = Request(url, headers={'User-Agent': 'MoinPDF-Umbrel-verification', **(headers or {})})
            with urlopen(request, timeout=60) as response:
                return response.read()
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 * (attempt + 1))


def verified_json(raw, digest):
    assert 'sha256:' + hashlib.sha256(raw).hexdigest() == digest, f'Digest mismatch: {digest}'
    return json.loads(raw)


root = Path(__file__).resolve().parents[3]
package = root / 'denny-moinpdf'
manifest = (package / 'umbrel-app.yml').read_text()
version = re.search(r'^version: "?(\d+\.\d+\.\d+)"?$', manifest, re.M).group(1)
compose = (package / 'docker-compose.yml').read_text()
source = json.loads((Path(__file__).parent / 'asset-checksums.json').read_text())['source']
release_url = f'https://api.github.com/repos/MoinPDF/moinpdf/releases/tags/v{version}'
release = json.loads(fetch(release_url))
assert release['tag_name'] == f'v{version}' and not release['draft'] and not release['prerelease']
assets = {asset['name']: asset for asset in release['assets']}
evidence = {'version': version, 'source': source, 'release': release['html_url'], 'images': {}}

for name in ('web', 'documents', 'translation', 'website'):
    references = set(re.findall(rf'ghcr\.io/moinpdf/moinpdf-{name}:[^\s]+', compose))
    assert len(references) == 1, f'{name}: expected one unique image reference'
    reference = references.pop()
    expected_image = f'ghcr.io/moinpdf/moinpdf-{name}:{version}-{source[:12]}'
    image, digest = reference.split('@')
    assert image == expected_image and re.fullmatch(r'sha256:[0-9a-f]{64}', digest)

    asset = assets[f'{name}.json']
    published = verified_json(fetch(asset['browser_download_url']), asset['digest'])
    assert published['source'] == source and published['image'] == image and published['digest'] == digest
    assert set(published['platforms']) == {'linux/amd64', 'linux/arm64'}

    repository = f'moinpdf/moinpdf-{name}'
    token_url = 'https://ghcr.io/token?' + urlencode({
        'service': 'ghcr.io', 'scope': f'repository:{repository}:pull',
    })
    token = json.loads(fetch(token_url))['token']
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': ','.join([
            'application/vnd.oci.image.index.v1+json',
            'application/vnd.oci.image.manifest.v1+json',
            'application/vnd.docker.distribution.manifest.list.v2+json',
            'application/vnd.docker.distribution.manifest.v2+json',
        ]),
    }
    registry = f'https://ghcr.io/v2/{repository}'
    index = verified_json(fetch(f'{registry}/manifests/{digest}', headers), digest)
    assert verified_json(fetch(f'{registry}/manifests/{version}-{source[:12]}', headers), digest) == index
    platforms = {}
    for architecture in ('amd64', 'arm64'):
        entries = [entry for entry in index['manifests']
                   if entry.get('platform', {}).get('os') == 'linux'
                   and entry['platform'].get('architecture') == architecture]
        assert len(entries) == 1, f'{name}: expected exactly one linux/{architecture} manifest'
        platform_digest = entries[0]['digest']
        platform_manifest = verified_json(fetch(f'{registry}/manifests/{platform_digest}', headers), platform_digest)
        config_digest = platform_manifest['config']['digest']
        config = verified_json(fetch(f'{registry}/blobs/{config_digest}', headers), config_digest)
        assert (config['os'], config['architecture']) == ('linux', architecture)
        labels = config['config']['Labels']
        assert labels['org.opencontainers.image.revision'] == source, f'{name}/{architecture}: wrong source'
        assert labels['org.opencontainers.image.source'] == 'https://github.com/MoinPDF/moinpdf'
        platforms[f'linux/{architecture}'] = platform_digest
        print(f'PASS: {name} linux/{architecture}: {platform_digest}; released source verified.', flush=True)
    evidence['images'][name] = {'image': image, 'digest': digest, 'platforms': platforms}

output = root / 'umbrel-evidence'
output.mkdir(exist_ok=True)
(output / 'image-digests.json').write_text(json.dumps(evidence, indent=2) + '\n')
print(f'PASS: all four public {version} images match official release assets, tags and SHA-256 digests.', flush=True)
