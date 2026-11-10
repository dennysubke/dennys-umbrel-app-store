"""Verify released 0.31 converters on both native architectures via Umbrel.

Fictional documents only. Independently reopen generated Office, Kindle and
comic files; never require the optional proprietary RAR creation executable.
"""
import io
import json
import os
from pathlib import Path
import platform
import struct
import zipfile
import zlib

import pymupdf
import requests

base = os.environ['MOINPDF_TEST_URL'].rstrip('/')
session = requests.Session()
session.trust_env = False
for cookie in json.loads(Path(os.environ['MOINPDF_TEST_COOKIES']).read_text()):
    session.cookies.set(cookie['name'], cookie['value'],
                        domain='localhost.local' if cookie['domain'] == 'localhost' else cookie['domain'],
                        path=cookie['path'])
session.headers['X-MoinPDF-Client'] = 'web'
out = Path('umbrel-evidence/formats031')
out.mkdir(parents=True, exist_ok=True)


def post(path, name, content, options=None, expected=200):
    response = session.post(base + '/api/documents' + path,
                            files={'file': (name, content)},
                            data={'options': json.dumps(options or {})}, timeout=240)
    assert response.status_code == expected, (path, response.status_code, response.text[:500])
    if expected == 200:
        assert response.headers.get('cache-control') == 'no-store'
        assert response.headers.get('content-disposition')
    return response.content


def check_pdf(content, pages=None, text=None):
    with pymupdf.open(stream=content, filetype='pdf') as document:
        assert len(document) > 0
        if pages is not None:
            assert len(document) == pages, len(document)
        if text is not None:
            assert text in ''.join(page.get_text() for page in document)
        for page in document:
            assert sum(value < 245 for value in page.get_pixmap().samples) > 100, f'Blank PDF page {page.number + 1}'


def rar5_stored(members):
    """Stored-member fixture following RARLAB's published RAR5 specification."""
    def vint(value):
        result = bytearray()
        while value > 127:
            result.append((value & 127) | 128)
            value >>= 7
        result.append(value)
        return bytes(result)

    def header(body):
        body = vint(len(body)) + body
        return struct.pack('<I', zlib.crc32(body)) + body

    archive = bytearray(b'Rar!\x1a\x07\x01\x00' + header(b'\x01\x00\x00'))
    for name, data in members:
        name = name.encode('utf-8')
        body = (b'\x02\x02' + vint(len(data)) + b'\x04' + vint(len(data)) + vint(0o100644)
                + struct.pack('<I', zlib.crc32(data)) + b'\x00\x01' + vint(len(name)) + name)
        archive.extend(header(body))
        archive.extend(data)
    archive.extend(header(b'\x05\x00\x00'))
    return bytes(archive)


capabilities = session.get(base + '/api/documents/v1/capabilities', timeout=30)
capabilities.raise_for_status()
features = capabilities.json()['capabilities']
for key in ['formatOffice', 'formatAzw3', 'kindleImport', 'cbrImport']:
    assert features.get(key) is True, (key, features)
assert features.get('formatCbr') is False, features

with pymupdf.open() as document:
    for title in ['Fictional MoinPDF format test', 'Second page with text 123.45']:
        page = document.new_page(width=300, height=400)
        page.insert_text((25, 40), title, fontsize=12)
        page.draw_rect(pymupdf.Rect(25, 80, 75, 130), color=(1, 0, 0), fill=(1, 0, 0))
    pdf = document.tobytes()

for fmt in ['rtf', 'odt', 'odp']:
    result = post('/v1/formats/' + fmt, 'fictional.pdf', pdf)
    if fmt == 'rtf':
        assert result.startswith(b'{\\rtf')
    else:
        with zipfile.ZipFile(io.BytesIO(result)) as archive:
            expected = 'text' if fmt == 'odt' else 'presentation'
            assert archive.read('mimetype') == ('application/vnd.oasis.opendocument.' + expected).encode()
            assert 'content.xml' in archive.namelist()
    restored = post('/v1/office', 'restored.' + fmt, result)
    check_pdf(restored, pages=2, text='Fictional MoinPDF' if fmt != 'odp' else None)
    (out / ('export.' + fmt)).write_bytes(result)
    (out / ('restored-' + fmt + '.pdf')).write_bytes(restored)

kindle = post('/v1/formats/azw3', 'fictional.pdf', pdf, {'title': 'Fictional book', 'language': 'en'})
assert kindle[60:68] == b'BOOKMOBI'
restored = post('/v1/documents/ebook', 'fictional.azw3', kindle, {'paper': 'a5', 'fontSize': 14})
(out / 'fictional.azw3').write_bytes(kindle)
(out / 'restored-kindle.pdf').write_bytes(restored)
check_pdf(restored, text='Fictional MoinPDF')
with pymupdf.open(stream=restored, filetype='pdf') as document:
    assert 'Second page' in ''.join(page.get_text() for page in document)
    assert round(document[0].rect.width) == 420

images = []
for color in [(1, 0, 0), (0, 0, 1)]:
    with pymupdf.open() as document:
        page = document.new_page(width=50, height=70)
        page.draw_rect(page.rect, color=color, fill=color)
        images.append(page.get_pixmap().tobytes('png'))
comic = rar5_stored([('page10.png', images[0]), ('page2.png', images[1])])
restored = post('/v1/documents/ebook', 'fictional.cbr', comic)
check_pdf(restored, pages=2)
with pymupdf.open(stream=restored, filetype='pdf') as document:
    # Natural ordering: page2 (blue) must precede page10 (red).
    for page, dominant in zip(document, [2, 0]):
        image = page.get_pixmap()
        pixel = image.pixel(image.width // 2, image.height // 2)
        assert pixel[dominant] > 200 and all(value < 30 for i, value in enumerate(pixel[:3]) if i != dominant), pixel
(out / 'restored-comic.pdf').write_bytes(restored)

post('/v1/formats/cbr', 'fictional.pdf', pdf, expected=503)
for name in ['broken.wpd', 'broken.wps', 'broken.odg']:
    post('/v1/office', name, b'not a document', expected=422)
for name in ['broken.mobi', 'broken.azw3', 'broken.cbr']:
    post('/v1/documents/ebook', name, b'not a document', expected=422)

(out / 'result.json').write_text(json.dumps({
    'architecture': platform.machine(),
    'installation': os.environ['MOINPDF_TEST_INSTALLATION'],
    'source': json.loads((Path(__file__).parent / 'asset-checksums.json').read_text())['source'],
    'checks': ['rtf-odt-odp-export-and-pdf-reimport', 'azw3-export-and-pdf-reimport',
               'rar5-cbr-import-natural-page-order', 'optional-rar-creation-unavailable',
               'invalid-legacy-office-and-ebook-rejected'],
}, indent=2) + '\n')
print('PASS: native RTF/ODT/ODP and Kindle round trips, CBR import/page order, '
      'optional RAR availability and corrupt-file rejection through signed-in Umbrel.', flush=True)
