"""Real Umbrel gateway, browser, documents and persistence on native runners."""
import json
import hashlib
import io
import os
import platform
import re
import secrets
from pathlib import Path
import subprocess
import tempfile
import time
import zipfile

import pymupdf
from playwright.sync_api import expect, sync_playwright

origin = 'http://localhost:8785'
installation = os.environ.get('MOINPDF_TEST_INSTALLATION', 'fresh')
architecture = {'x86_64': 'amd64', 'aarch64': 'arm64'}.get(platform.machine())
assert architecture == os.environ.get('MOINPDF_TEST_ARCHITECTURE', 'amd64'), platform.machine()
container_architecture = subprocess.check_output([
    'docker', 'exec', 'moinpdf-umbrel-test', 'uname', '-m'], text=True).strip()
assert container_architecture == platform.machine(), container_architecture
evidence = Path('umbrel-evidence')
evidence.mkdir(exist_ok=True)
version = re.search(r'^version: "([^\"]+)"$',
                    Path('denny-moinpdf/umbrel-app.yml').read_text(), re.M).group(1)


def umbrel(*args):
    return subprocess.check_output(['docker', 'exec', 'moinpdf-umbrel-test', 'umbreld', 'client', *args], text=True)


def switch_language(page, label, code):
    trigger = page.locator('.language-trigger')
    # Wait for the animated menu to unmount before opening it again.
    expect(page.locator('.language-menu')).to_have_count(0)
    expect(trigger).to_be_enabled()
    trigger.click()
    menu = page.locator('.language-menu')
    expect(menu).to_be_visible()
    menu.get_by_role('menuitemradio', name=label, exact=True).click()
    expect(page.locator('html')).to_have_attribute('lang', code)
    expect(trigger).to_have_attribute('aria-expanded', 'false')
    expect(trigger).to_have_attribute('aria-busy', 'false')
    expect(menu).to_have_count(0)


def expect_home(page):
    try:
        logo = page.get_by_role('img', name='MoinPDF', exact=True)
        expect(logo).to_be_visible(timeout=60000)
        expect(logo).to_have_js_property('complete', True)
        assert logo.evaluate('(image) => image.naturalWidth > 0'), 'App logo did not render'
        expect(page.locator('.harbor-wordmark > span')).to_have_text('Papierkram. Läuft.')
        expect(page.get_by_role('button', name='PDF oder andere Datei auswählen', exact=True)).to_be_enabled()
        expect(page.locator('.moinpdf-version')).to_have_text(f'MoinPDF v{version}')
        expect(page.locator('.tool-mosaic-card')).to_have_count(6)
        assert page.locator('.tool-mosaic-card').evaluate_all(
            '(cards) => cards.map(card => card.dataset.toolId)') == [
                'edit-text', 'merge', 'compress', 'ocr', 'sign', 'pdf-word']
        expect(page.locator('.quick-access-settings')).to_be_visible()
        expect(page.locator('.harbor-photo')).to_be_hidden()
        expect(page.locator('.desktop-command-trigger')).to_be_visible()
        assert page.locator('.desktop-command-trigger').evaluate('''el =>
            el.getBoundingClientRect().top >= document.querySelector('.app-toolbar').getBoundingClientRect().bottom - 1
        '''), 'Desktop search must have its own row below the toolbar'
        expect(page.locator('.harbor-photo img')).to_have_js_property('complete', True)
        assert page.locator('.harbor-photo img').evaluate('(image) => image.naturalWidth > 0'), 'Harbour image did not render'
    except Exception:
        page.screenshot(path=str(evidence / 'moinpdf-failure.png'), full_page=True)
        (evidence / 'moinpdf-failure.html').write_text(page.content())
        raise


def mobile_search(page):
    """Exercise the new navigation through the signed-in Umbrel gateway."""
    page.set_viewport_size({'width': 390, 'height': 844})
    nav = page.locator('.harbor-mobile-nav')
    expect(nav.locator('button')).to_have_count(5)
    expect(page.locator('#moinpdf-project-bar')).to_be_hidden()
    for label, language in (('Deutsch', 'de'), ('English', 'en')):
        switch_language(page, label, language)
        en = language == 'en'
        nav.get_by_role('button', name='Home' if en else 'Start', exact=True).click()
        expect(page.locator('.harbor-photo')).to_be_visible()
        search = nav.get_by_role('button', name='Search' if en else 'Suche', exact=True)
        search.click()
        dialog = page.locator('.mobile-tool-search')
        field = dialog.get_by_role('combobox')
        expect(field).to_be_focused()
        page.wait_for_function('''el => {
            const r=el.getBoundingClientRect();
            return r.width > 0 && r.height > 0
                && r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight
                && el.contains(document.elementFromPoint(r.x+r.width/2, r.y+r.height/2));
        }''', arg=field.element_handle())
        field.fill('split' if en else 'teilen')
        expect(dialog.locator('[data-tool-id="split"]')).to_be_visible()
        page.screenshot(path=str(evidence / f'moinpdf-mobile-search-{language}.png'))
        title = dialog.locator('[data-tool-id="split"] strong').inner_text()
        dialog.locator('[data-tool-id="split"]').click()
        expect(dialog).to_have_count(0)
        expect(page.locator('main h1')).to_have_text(title)
        nav.get_by_role('button', name='Tools' if en else 'Werkzeuge', exact=True).click()
        expect(page.locator('.chooser-file')).to_contain_text('umbrel-test.pdf')
        expect(page.locator('.chooser-document-count')).to_contain_text('1 file' if en else '1 Datei')
        projects = nav.get_by_role('button', name='Projects' if en else 'Projekte', exact=True)
        projects.click()
        expect(page.get_by_role('dialog')).to_be_visible()
        page.keyboard.press('Escape')
        expect(projects).to_be_focused()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    switch_language(page, 'Deutsch', 'de')
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.locator('.harbor-desktop-nav').get_by_role('button', name='Start', exact=True).click()
    expect(page.locator('.mosaic-all-tools')).to_be_visible()
    page.locator('.mosaic-all-tools').click()
    expect(page.locator('.chooser-tool')).to_have_count(112)
    expect(page.locator('.chooser-file')).to_contain_text('umbrel-test.pdf')
    page.locator('.harbor-desktop-nav').get_by_role('button', name='Start', exact=True).click()
    print('PASS: DE/EN mobile search, projects, focus and PDF retention through Umbrel.', flush=True)


def create_persistent_job(context):
    """Use the real queue through Umbrel, then retain its exact result over restart."""
    subprocess.run([
        'docker', 'exec', 'moinpdf-umbrel-test', 'docker', 'exec',
        'denny-moinpdf_documents_1', 'python', '-c',
        'import os,stat; p=os.environ["MOINPDF_JOB_DIR"]; s=os.stat(p); '
        'assert (s.st_uid,s.st_gid)==(1000,1000), (s.st_uid,s.st_gid); '
        'assert stat.S_IMODE(s.st_mode)==0o700, oct(s.st_mode); '
        'assert os.access(p,os.W_OK), p; '
        'print("PASS: private persistent job directory is writable by the unprivileged document service.")',
    ], check=True)
    ticket = secrets.token_hex(32)
    headers = {'X-MoinPDF-Client': 'web', 'X-MoinPDF-Job-Ticket': ticket}
    api = origin + '/api/documents/v1/jobs'
    office = io.BytesIO()
    with zipfile.ZipFile(office, 'w', zipfile.ZIP_DEFLATED) as document:
        document.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        document.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        document.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>MoinPDF persistent Umbrel job: survives an app restart.</w:t></w:r></w:p><w:sectPr/></w:body></w:document>')
    submitted = context.request.post(api, headers=headers, multipart={
        'operation': '/v1/office',
        'file': {'name': 'restart.docx',
                 'mimeType': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                 'buffer': office.getvalue()},
    })
    assert submitted.ok, f'Queue submission failed: {submitted.status} {submitted.text()}'
    job_id = submitted.json()['id']
    url = api + '/' + job_id
    for attempt in range(120):
        status = context.request.get(url, headers=headers)
        assert status.ok, status.text()
        state = status.json()
        if state['status'] == 'completed':
            break
        assert state['status'] in ('queued', 'running'), state
        time.sleep(1)
    else:
        raise AssertionError('Persistent conversion did not complete within two minutes')
    result = context.request.get(url + '/result', headers=headers)
    assert result.ok, result.text()
    with pymupdf.open(stream=result.body(), filetype='pdf') as document:
        assert 'persistent Umbrel job' in ''.join(page.get_text() for page in document)
    wrong = {**headers, 'X-MoinPDF-Job-Ticket': secrets.token_hex(32)}
    for suffix in ('', '/result'):
        assert context.request.get(url + suffix, headers=wrong).status == 404
        assert context.request.get(url + suffix, headers={'X-MoinPDF-Client': 'web'}).status == 404
    # Confirm the result is on the persistent bind mount, not the container's tmpfs.
    mounts = json.loads(subprocess.check_output([
        'docker', 'exec', 'moinpdf-umbrel-test', 'docker', 'inspect',
        'denny-moinpdf_documents_1', '--format', '{{json .Mounts}}'], text=True))
    assert any(m['Type'] == 'bind' and m['RW'] and
               m['Destination'] == '/var/lib/moinpdf-jobs' and
               m['Source'].endswith('/data/document-jobs') for m in mounts), mounts
    digest = hashlib.sha256(result.body()).hexdigest()
    print('PASS: real background conversion, private job ticket and persistent Umbrel mount.', flush=True)
    return url, headers, digest


def verify_persistent_job(context, job):
    url, headers, digest = job
    status = context.request.get(url, headers=headers)
    assert status.ok and status.json()['status'] == 'completed', status.text()
    result = context.request.get(url + '/result', headers=headers)
    assert result.ok and hashlib.sha256(result.body()).hexdigest() == digest
    deleted = context.request.post(url + '/delete', headers=headers)
    assert deleted.ok, deleted.text()
    assert context.request.get(url, headers=headers).status == 404
    (evidence / 'background-job.json').write_text(json.dumps({
        'status': 'passed', 'resultSha256': digest,
        'checks': ['conversion', 'ticket-isolation', 'persistent-bind-mount',
                   'byte-identical-result-after-umbrel-restart', 'explicit-delete'],
    }, indent=2) + '\n')
    print('PASS: background job result survives Umbrel restart byte-for-byte and can be deleted.', flush=True)


with sync_playwright() as browser_api, tempfile.TemporaryDirectory() as temporary:
    browser = browser_api.chromium.launch()
    context = browser.new_context(ignore_https_errors=True, viewport={'width': 1440, 'height': 1000})
    for api, service in (('documents', 'MoinPDF Dokumentenserver'), ('website', 'MoinPDF Web-Konverter')):
        rejected = context.request.get(origin + f'/api/{api}/v1/capabilities',
                                       headers={'X-MoinPDF-Client': 'web'}, max_redirects=0)
        assert service not in rejected.text(), f'{api} API is accessible without Umbrel login'

    login = context.request.post('http://localhost/trpc/user.login',
                                 data={'password': 'synthetic-umbrel-ci-password'},
                                 headers={'Origin': 'http://localhost'})
    assert login.ok, 'Synthetic Umbrel user could not sign in'
    page = context.new_page()
    page.goto(origin)
    expect_home(page)
    page.screenshot(path=str(evidence / 'moinpdf-home.png'), full_page=True)
    print('PASS: protected gateway and signed-in HTTP app page.', flush=True)

    # Open a real synthetic PDF in the browser before testing server jobs.
    pdf_path = Path(temporary) / 'umbrel-test.pdf'
    with pymupdf.open() as document:
        document.new_page().insert_text((50, 60), 'MoinPDF on Umbrel - synthetic test')
        document.save(pdf_path)
    page.locator('input[type="file"]').first.set_input_files(str(pdf_path))
    page.get_by_role('heading', name='Was möchtest du tun?', exact=True).wait_for(timeout=30000)
    expect(page.locator('.chooser-document-count')).to_have_text('1 Datei·1 Seite')
    uploaded_file = page.locator('.chooser-file')
    expect(uploaded_file).to_have_count(1)
    expect(uploaded_file.get_by_text('umbrel-test.pdf', exact=True)).to_be_visible()
    switch_language(page, 'English', 'en')
    expect(page.locator('.chooser-document-count')).to_contain_text('1 file')
    expect(page.locator('.chooser-file')).to_contain_text('umbrel-test.pdf')
    switch_language(page, 'Deutsch', 'de')
    expect(page.locator('.chooser-document-count')).to_have_text('1 Datei·1 Seite')
    page.screenshot(path=str(evidence / 'moinpdf-tools.png'), full_page=True)
    page.get_by_role('button', name='Seiten organisieren', exact=True).click()
    page.get_by_role('tab', name='Vorschau', exact=True).click()
    preview = page.get_by_role('img', name='umbrel-test.pdf, Seite 1', exact=True)
    preview.wait_for(timeout=30000)
    expect(preview).to_have_js_property('complete', True)
    assert preview.evaluate('(image) => image.naturalWidth > 0'), 'PDF preview did not render'
    page.screenshot(path=str(evidence / 'moinpdf-document.png'), full_page=True)
    try:
        mobile_search(page)
        page.get_by_role('button', name='Neues Dokument', exact=True).click()
        page.get_by_label('Dokumenttitel', exact=True).fill(f'Umbrel {version}')
        page.get_by_role('textbox', name='Dokumentinhalt', exact=True).fill('A document created on Umbrel. Umlauts: ÄÖÜ.')
        page.get_by_role('button', name='Entwurf speichern', exact=True).click()
        expect(page.locator('.writer-save-state')).to_have_attribute('data-state', 'saved')
        with page.expect_download() as download:
            page.get_by_role('button', name='Als PDF herunterladen', exact=True).click()
        expect(page.locator('.writer-export')).to_be_visible()
        saved = Path(temporary) / 'umbrel-created.pdf'
        download.value.save_as(saved)
        with pymupdf.open(saved) as document:
            assert len(document) == 1 and 'created on Umbrel' in document[0].get_text()
            assert 'ÄÖÜ' in document[0].get_text()
        print('PASS: document creation, local draft and independently read PDF export on Umbrel HTTP.', flush=True)
    except Exception:
        page.screenshot(path=str(evidence / 'moinpdf-navigation-writer-failure.png'), full_page=True)
        raise
    print('PASS: synthetic PDF opened in the browser; waiting for all language models.', flush=True)

    for attempt in range(180):
        response = context.request.get(origin + '/api/documents/v1/capabilities',
                                       headers={'X-MoinPDF-Client': 'web'})
        if response.ok and all(response.json().get('capabilities', {}).values()):
            assert response.json()['capabilities']
            break
        time.sleep(10)
    else:
        raise AssertionError('Document and translation services did not become ready')

    cookies = Path(temporary) / 'cookies.json'
    cookies.write_text(json.dumps(context.cookies()))
    cookies.chmod(0o600)
    environment = dict(os.environ, MOINPDF_TEST_URL=origin, MOINPDF_TEST_COOKIES=str(cookies),
                       MOINPDF_TEST_REPO=str(Path.cwd()))
    subprocess.run(['python', '.github/tests/moinpdf/selfhost-smoke.py'], env=environment, check=True)

    # Exercise the main 0.20.1 exports through Umbrel's authenticated app route.
    subprocess.run(['python', '.github/tests/moinpdf/core-export-smoke.py'], env=environment, check=True)

    # Umbrel deliberately uses distinct HTTP and __Host- HTTPS session cookies.
    # Authenticate the HTTPS session through the real login endpoint as well.
    https_login = context.request.post('https://localhost/trpc/user.login',
                                       data={'password': 'synthetic-umbrel-ci-password'},
                                       headers={'Origin': 'https://localhost'})
    assert https_login.ok, 'Synthetic Umbrel user could not sign in over HTTPS'
    # Validate the HTTPS app route using the disposable OS-generated certificate.
    page.goto('https://localhost:8785')
    expect_home(page)
    print('PASS: signed-in HTTPS app page; checking restart persistence.', flush=True)

    persistent_job = create_persistent_job(context)
    umbrel('apps.restart.mutate', '--appId', 'denny-moinpdf')
    for attempt in range(60):
        state = json.loads(umbrel('apps.state.query', '--appId', 'denny-moinpdf'))
        if state['state'] == 'ready':
            break
        time.sleep(5)
    else:
        raise AssertionError('Umbrel restart did not finish')
    for attempt in range(30):
        try:
            response = context.request.get(origin + '/api/documents/v1/capabilities',
                                           headers={'X-MoinPDF-Client': 'web'})
            if response.ok and response.json()['capabilities']['translate']:
                break
        except Exception:
            pass
        time.sleep(5)
    else:
        raise AssertionError('Translation did not recover from the persisted models')
    verify_persistent_job(context, persistent_job)
    subprocess.run(['python', '.github/tests/moinpdf/selfhost-smoke.py'], env=environment, check=True)
    page.goto(origin)
    expect_home(page)
    browser.close()

(evidence / 'result.txt').write_text(f'PASS: umbrelOS 2.0.0 on native {architecture}; installation path: {installation}; native Umbrel installation, protected app gateway, signed-in browser, PDF upload and DE/EN switching, mobile search/projects/document retention, document creation/drafts/PDF export, HTTP and HTTPS app routes, real Office, website conversion, DE/EN translation and speech, restart, persisted models and byte-identical background-job results with ticket isolation and deletion. Physical NAS devices and camera/printer hardware were not tested.\n')
print((evidence / 'result.txt').read_text())
