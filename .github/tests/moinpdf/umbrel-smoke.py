"""Real Umbrel app gateway, browser, documents, and restart persistence (amd64)."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

import pymupdf
from playwright.sync_api import expect, sync_playwright

origin = 'http://localhost:8785'
evidence = Path('umbrel-evidence')
evidence.mkdir(exist_ok=True)


def umbrel(*args):
    return subprocess.check_output(['docker', 'exec', 'moinpdf-umbrel-test', 'umbreld', 'client', *args], text=True)


with sync_playwright() as browser_api, tempfile.TemporaryDirectory() as temporary:
    browser = browser_api.chromium.launch()
    context = browser.new_context(ignore_https_errors=True, viewport={'width': 1440, 'height': 1000})
    rejected = context.request.get(origin + '/api/documents/v1/capabilities',
                                   headers={'X-MoinPDF-Client': 'web'}, max_redirects=0)
    assert 'MoinPDF Dokumentenserver' not in rejected.text(), 'App API is accessible without Umbrel login'

    login = context.request.post('http://localhost/trpc/user.login',
                                 data={'password': 'synthetic-umbrel-ci-password'},
                                 headers={'Origin': 'http://localhost'})
    assert login.ok, 'Synthetic Umbrel user could not sign in'
    page = context.new_page()
    page.goto(origin)
    page.get_by_role('img', name='MoinPDF. Papierkram. Läuft.', exact=True).wait_for(timeout=60000)
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
    page.get_by_text('umbrel-test.pdf', exact=True).wait_for()
    page.screenshot(path=str(evidence / 'moinpdf-tools.png'), full_page=True)
    page.get_by_role('button', name='Seiten organisieren', exact=True).click()
    page.get_by_role('tab', name='Dokument', exact=True).click()
    preview = page.get_by_role('img', name='umbrel-test.pdf, Seite 1', exact=True)
    preview.wait_for(timeout=30000)
    expect(preview).to_have_js_property('complete', True)
    assert preview.evaluate('(image) => image.naturalWidth > 0'), 'PDF preview did not render'
    page.screenshot(path=str(evidence / 'moinpdf-document.png'), full_page=True)
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

    # Umbrel deliberately uses distinct HTTP and __Host- HTTPS session cookies.
    # Authenticate the HTTPS session through the real login endpoint as well.
    https_login = context.request.post('https://localhost/trpc/user.login',
                                       data={'password': 'synthetic-umbrel-ci-password'},
                                       headers={'Origin': 'https://localhost'})
    assert https_login.ok, 'Synthetic Umbrel user could not sign in over HTTPS'
    # Validate the HTTPS app route using the disposable OS-generated certificate.
    page.goto('https://localhost:8785')
    page.get_by_role('img', name='MoinPDF. Papierkram. Läuft.', exact=True).wait_for(timeout=30000)
    print('PASS: signed-in HTTPS app page; checking restart persistence.', flush=True)

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
    subprocess.run(['python', '.github/tests/moinpdf/selfhost-smoke.py'], env=environment, check=True)
    page.goto(origin)
    page.get_by_role('img', name='MoinPDF. Papierkram. Läuft.', exact=True).wait_for(timeout=30000)
    browser.close()

(evidence / 'result.txt').write_text('PASS: umbrelOS 2.0.0 on amd64; fresh install through Umbrel, protected app gateway, signed-in browser, PDF upload, HTTP and HTTPS app routes, real Office and DE/EN translation, restart and persisted models. ARM runtime was not tested.\n')
print((evidence / 'result.txt').read_text())
