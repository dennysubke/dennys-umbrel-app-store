"""Exercise 0.30 server outputs through the authenticated native Umbrel gateway.

Fictional invoices and an attributed AFL-3.0 handwriting fixture only. This is
an integration test, not an independent handwriting-accuracy benchmark.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import zipfile

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
fixtures = Path(__file__).parent / 'growth030'
out = Path('umbrel-evidence/growth030')
out.mkdir(parents=True, exist_ok=True)


def post(path, files, data=None):
    response = session.post(base + '/api/documents' + path,
                            files=files, data=data or {}, timeout=300)
    response.raise_for_status()
    assert response.headers.get('cache-control') == 'no-store'
    return response


invoice = (fixtures / 'invoice.pdf').read_bytes()
xml = (fixtures / 'xrechnung-standard.xml').read_bytes()
response = post('/v1/xrechnung/validate', {'file': ('invoice.xml', xml, 'application/xml')})
with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
    xrechnung = json.loads(archive.read('Ergebnis.json'))
    assert xrechnung['xrechnungAccepted'] and xrechnung['documentHashVerified'], xrechnung
    assert xrechnung['errorCount'] == 0, xrechnung
(out / 'xrechnung.zip').write_bytes(response.content)

hybrid_xml = (fixtures / 'zugferd-standard.xml').read_bytes()
response = post('/v1/zugferd/create', {
    'file': ('invoice.pdf', invoice, 'application/pdf'),
    'invoice': ('invoice.xml', hybrid_xml, 'application/xml'),
}, {'profile': 'T'})
with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
    hybrid = json.loads(archive.read('Ergebnis.json'))
    assert all(hybrid[key] for key in ['compliant', 'mustangValid', 'pdfa3b', 'declaredPdfaValid']), hybrid
    with pymupdf.open(stream=archive.read('ZUGFeRD-geprueft.pdf'), filetype='pdf') as pdf:
        assert any(pdf.embfile_get(name) == hybrid_xml for name in pdf.embfile_names())
        assert '129.70' in ''.join(page.get_text() for page in pdf)
(out / 'zugferd.zip').write_bytes(response.content)

response = post('/v1/print-pdfx', {'file': ('invoice.pdf', invoice, 'application/pdf')},
                {'options': json.dumps({'trimInsetMm': 3, 'allowFontSubstitution': False})})
with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
    print_report = json.loads(archive.read('Technische-Pruefung.json'))
    assert print_report['technicalChecksPassed'] and print_report['isoConformanceVerified'] is False, print_report
    with pymupdf.open(stream=archive.read('Druckdatei-PDFX3.pdf'), filetype='pdf') as pdf:
        assert len(pdf) == 1 and '129.70' in pdf[0].get_text()
        assert len(pdf[0].get_pixmap().samples) > 10000
(out / 'pdfx.zip').write_bytes(response.content)

with pymupdf.open() as scan:
    image = pymupdf.Pixmap(fixtures / 'fixture-2.jpg')
    page = scan.new_page(width=image.width, height=image.height)
    page.insert_image(page.rect, filename=str(fixtures / 'fixture-2.jpg'))
    scan.new_page(width=120, height=64)
    content = scan.tobytes()
regions = [{'page': n, 'rect': {'x': 0, 'y': 0, 'w': 1, 'h': 1}} for n in (0, 1)]
response = post('/v1/documents/handwriting', {'file': ('scan.pdf', content, 'application/pdf')},
                {'options': json.dumps({'lines': regions})})
handwriting = response.json()
assert handwriting['reviewRequired'] is True, handwriting
assert handwriting['lines'][0]['text'] == 'Handschrift', handwriting
assert handwriting['lines'][1]['status'] == 'blank' and handwriting['lines'][1]['text'] == '', handwriting
(out / 'handwriting.json').write_text(json.dumps(handwriting, indent=2) + '\n')
(out / 'result.json').write_text(json.dumps({
    'architecture': platform.machine(),
    'installation': os.environ['MOINPDF_TEST_INSTALLATION'],
    'source': json.loads((Path(__file__).parent / 'asset-checksums.json').read_text())['source'],
    'checks': ['xrechnung-kosit', 'zugferd-mustang-pdfa3b-declared-profile-exact-xml',
               'pdfx-independent-technical-partial-report', 'real-german-handwriting-and-blank-line'],
    'fixtureSha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in fixtures.iterdir() if path.is_file()},
}, indent=2) + '\n')
print('PASS: native Umbrel XRechnung, ZUGFeRD with exact embedded XML, PDF/X partial check, '
      'real German handwriting and blank-line rejection through the signed-in gateway.', flush=True)
