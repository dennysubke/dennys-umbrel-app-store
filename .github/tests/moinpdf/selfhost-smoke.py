"""Run inside the documents service: exercise the real HTTP proxy and translator."""
import hashlib
import json
import zipfile
import io
import os
import re
import wave
from pathlib import Path

import pymupdf
import requests

base = os.getenv('MOINPDF_TEST_URL', 'http://app:8080')
session = requests.Session()
session.trust_env = False
if os.getenv('MOINPDF_TEST_COOKIES'):
    for cookie in json.loads(Path(os.environ['MOINPDF_TEST_COOKIES']).read_text()):
        session.cookies.set(cookie['name'], cookie['value'], domain='localhost.local' if cookie['domain'] == 'localhost' else cookie['domain'], path=cookie['path'])
if os.getenv('MOINPDF_TEST_PASSWORD'):
    session.auth = (os.getenv('MOINPDF_TEST_USERNAME', 'moinpdf'), os.environ['MOINPDF_TEST_PASSWORD'])
home = session.get(base + '/', timeout=10)
home.raise_for_status()
assert 'id="root"' in home.text and '/assets/' in home.text
repo = Path(os.getenv('MOINPDF_TEST_REPO', '/repo'))
version = re.search(r'^version: [\"]?([^\"\s]+)', (repo / 'denny-moinpdf/umbrel-app.yml').read_text(), re.M).group(1)
asset_checksums = json.loads((Path(__file__).parent / 'asset-checksums.json').read_text())['sha256']
media = session.get(base + '/medienbereich.html', timeout=10)
media.raise_for_status()
assert f'MoinPDF v{version}' in media.text, 'Docker media page is older than the release'
assert 'media-hero-note' not in media.text
assert 'no-cache' in media.headers.get('cache-control', '')
video_path = re.search(r'<source src="([^\"]+)" type="video/mp4"', media.text).group(1)
for path in ('/favicon.png', '/favicon.ico', '/apple-touch-icon.png', video_path):
    asset = session.get(base + path, timeout=30)
    asset.raise_for_status()
    assert hashlib.sha256(asset.content).hexdigest() == asset_checksums[path], path
    if not path.endswith('.mp4'):
        assert 'no-cache' in asset.headers.get('cache-control', ''), path
assert '/favicon.png?v=' in home.text and '/favicon.png?v=' in media.text
video_range = session.get(base + video_path, headers={'Range': 'bytes=0-31'}, timeout=10)
assert video_range.status_code == 206 and len(video_range.content) == 32
assert video_range.content[4:8] == b'ftyp'
assert video_range.headers['content-type'].startswith('video/mp4')
for path in ['/vendor/pdf/pdf.worker.min.mjs', '/vendor/ocr/worker.min.js',
             '/vendor/languages/deu.traineddata.gz', '/vendor/languages/eng.traineddata.gz',
             '/vendor/qpdf/qpdf.wasm', '/vendor/invoice-font/NotoSans-Regular.ttf']:
    response = session.get(base + path, timeout=30)
    response.raise_for_status()
    assert len(response.content) > 1000, path

api = base + '/api/documents'
website_api = base + '/api/website'
assert session.get(website_api + '/v1/capabilities', timeout=10).status_code == 403
assert session.options(website_api + '/v1/website', headers={'Origin': 'https://foreign.example',
    'Access-Control-Request-Headers': 'X-MoinPDF-Client'}, timeout=10).status_code == 403
assert session.get(api + '/v1/capabilities', timeout=10).status_code == 403
assert session.options(api + '/v1/office', headers={'Origin': 'https://foreign.example',
    'Access-Control-Request-Headers': 'X-MoinPDF-Client'}, timeout=10).status_code == 403
session.headers['X-MoinPDF-Client'] = 'web'
capabilities = session.get(api + '/v1/capabilities', timeout=10)
capabilities.raise_for_status()
features = capabilities.json()['capabilities']
assert features and all(features.values()), features
assert session.get(api + '/v1/capabilities', headers={'Sec-Fetch-Site': 'cross-site'}, timeout=10).status_code == 403
# A supplied credential never replaces the internal proxy credential.
assert session.get(api + '/v1/capabilities', headers={'Authorization': 'Bearer invalid'}, timeout=10).status_code == 200
assert session.get(base + '/v1/capabilities', timeout=10).status_code == 404

# Exercise the new service through Umbrel and the app's authenticated proxy.
website_capabilities = session.get(website_api + '/v1/capabilities', timeout=10)
website_capabilities.raise_for_status()
assert website_capabilities.json()['capabilities']['website'] is True
assert website_capabilities.headers['cache-control'] == 'no-store'
assert session.get(website_api + '/v1/capabilities',
    headers={'Sec-Fetch-Site': 'cross-site'}, timeout=10).status_code == 403
for blocked in ('http://127.0.0.1/', 'file:///etc/passwd', 'https://user:password@example.com/'):
    rejected = session.post(website_api + '/v1/website', data={'url': blocked}, timeout=15)
    assert rejected.status_code == 422, (blocked, rejected.status_code)
website = session.post(website_api + '/v1/website', data={
    'url': 'https://example.com/',
    'options': json.dumps({'paper': 'A4', 'landscape': False, 'background': True, 'media': 'print'})
}, timeout=90)
website.raise_for_status()
assert website.headers['content-type'].startswith('application/pdf')
assert website.headers['cache-control'] == 'no-store'
assert 'content-disposition' in website.headers
with pymupdf.open(stream=website.content, filetype='pdf') as rendered:
    assert len(rendered) >= 1
    assert 'Example Domain' in ''.join(page.get_text() for page in rendered)
print('PASS: website capability, request isolation, private-URL rejection and real public HTTPS page rendered to PDF.', flush=True)

pdf = pymupdf.open()
page = pdf.new_page()
page.insert_text((50, 60), 'Guten Morgen. Das ist ein Test. Vielen Dank.', fontsize=14)
content = pdf.tobytes()
pdf.close()
result = session.post(api + '/v1/documents/translate',
    files={'file': ('test.pdf', content, 'application/pdf')},
    data={'options': json.dumps({'language': 'de', 'target': 'en'})}, timeout=200)
result.raise_for_status()
with pymupdf.open(stream=result.content, filetype='pdf') as document:
    text = ''.join(page.get_text() for page in document)
    assert 'Guten Morgen' in text, text
    assert 'good morning' in text.lower() and 'thank' in text.lower(), text

office = io.BytesIO()
with zipfile.ZipFile(office, 'w', zipfile.ZIP_DEFLATED) as document:
    document.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    document.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    document.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>MoinPDF test document</w:t></w:r></w:p><w:sectPr/></w:body></w:document>')
result = session.post(api + '/v1/office', files={'file': ('sample.docx', office.getvalue())}, timeout=200)
result.raise_for_status()
assert result.content.startswith(b'%PDF-'), result.content[:80]
with pymupdf.open(stream=result.content, filetype='pdf') as converted:
    assert 'MoinPDF test document' in ''.join(page.get_text() for page in converted)
assert 'content-disposition' in result.headers
assert result.headers['cache-control'] == 'no-store'

audio = session.post(api + '/v1/audio', data={'request': json.dumps({
    'voice': 'thorsten', 'speed': 1, 'sections': [{'title': 'Stimmprobe', 'text': 'Moin! Die lokale Sprachausgabe funktioniert.'}]
})}, timeout=200)
audio.raise_for_status()
assert audio.headers['content-type'].startswith('audio/wav')
assert audio.headers['cache-control'] == 'no-store'
with wave.open(io.BytesIO(audio.content), 'rb') as wav:
    assert wav.getframerate() == 22050 and wav.getnchannels() == 1
    assert wav.getnframes() > 22050
print('PASS: app, local assets, all server capabilities, request isolation, real website PDF, German/English PDF translation, Office conversion and local speech through the authenticated HTTP proxy.')
