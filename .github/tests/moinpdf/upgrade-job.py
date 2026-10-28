"""Retain a real queued conversion result across a native Umbrel app update."""
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import sys
import time
import zipfile

import pymupdf
import requests

origin = 'http://localhost:8785'
state_file = Path('/tmp/moinpdf-upgrade-job.json')
mode = sys.argv[1]
assert mode in ('before', 'after')
session = requests.Session()
login = session.post(origin.replace(':8785', '') + '/trpc/user.login',
                     json={'password': 'synthetic-umbrel-ci-password'},
                     headers={'Origin': 'http://localhost'}, timeout=30)
login.raise_for_status()
api = origin + '/api/documents/v1/jobs'

if mode == 'before':
    ticket = secrets.token_hex(32)
    headers = {'X-MoinPDF-Client': 'web', 'X-MoinPDF-Job-Ticket': ticket}
    office = io.BytesIO()
    with zipfile.ZipFile(office, 'w', zipfile.ZIP_DEFLATED) as document:
        document.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        document.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        document.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Synthetic MoinPDF job created before the Umbrel update.</w:t></w:r></w:p><w:sectPr/></w:body></w:document>')
    # Start from a fully operational published installation, including the
    # persistent language models. Umbrel's app state becomes ready while their
    # first installation can still be running in the background.
    for attempt in range(180):
        try:
            ready = session.get(origin + '/api/documents/v1/capabilities', headers=headers, timeout=10)
            features = ready.json().get('capabilities', {}) if ready.ok else {}
            if features and all(features.values()):
                break
            if attempt % 6 == 0:
                print('Waiting for the complete 0.23.0 baseline; pending capabilities:',
                      sorted(name for name, value in features.items() if not value) or ['document API'],
                      flush=True)
        except (requests.RequestException, ValueError):
            if attempt % 6 == 0:
                print('Waiting for the complete 0.23.0 baseline document API.', flush=True)
        time.sleep(10)
    else:
        raise AssertionError('The complete published 0.23.0 baseline did not become ready')
    print('PASS: all 0.23.0 document capabilities and persisted language models ready before update.', flush=True)
    submitted = session.post(api, headers=headers, data={'operation': '/v1/office'},
                             files={'file': ('upgrade.docx', office.getvalue(),
                                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document')},
                             timeout=30)
    submitted.raise_for_status()
    job_id = submitted.json()['id']
else:
    saved = json.loads(state_file.read_text())
    job_id = saved['id']
    headers = {'X-MoinPDF-Client': 'web', 'X-MoinPDF-Job-Ticket': saved['ticket']}

url = api + '/' + job_id
for attempt in range(120):
    try:
        response = session.get(url, headers=headers, timeout=10)
        if response.ok:
            status = response.json()['status']
            if status == 'completed':
                break
            assert status in ('queued', 'running'), status
    except (requests.RequestException, ValueError):
        pass
    time.sleep(2)
else:
    raise AssertionError(f'Persistent job did not become available {mode} the update')
result = session.get(url + '/result', headers=headers, timeout=30)
result.raise_for_status()
with pymupdf.open(stream=result.content, filetype='pdf') as document:
    assert 'job created before the Umbrel update' in ''.join(page.get_text() for page in document)
digest = hashlib.sha256(result.content).hexdigest()
if mode == 'before':
    fd = os.open(state_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as handle:
        json.dump({'id': job_id, 'ticket': ticket, 'sha256': digest}, handle)
    print('PASS: real persistent conversion completed on 0.23.0 before the native update.', flush=True)
else:
    assert digest == saved['sha256'], 'Existing conversion result changed during the update'
    wrong = {**headers, 'X-MoinPDF-Job-Ticket': secrets.token_hex(32)}
    assert session.get(url, headers=wrong, timeout=30).status_code == 404
    output = Path('umbrel-evidence/upgrade-background-job.json')
    output.write_text(json.dumps({'status': 'passed', 'from': '0.23.0', 'resultSha256': digest,
                                 'byteIdenticalAfterNativeUpdate': True, 'ticketIsolation': True}, indent=2) + '\n')
    session.post(url + '/delete', headers=headers, timeout=30).raise_for_status()
    state_file.unlink()
    print('PASS: pre-upgrade background-job result retained byte-for-byte, with private ticket isolation.', flush=True)
