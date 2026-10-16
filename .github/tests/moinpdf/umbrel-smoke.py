"""Real Umbrel app gateway, browser, documents, and restart persistence (amd64)."""
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile
import time

import pymupdf
from playwright.sync_api import expect, sync_playwright

origin = 'http://localhost:8785'
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
    expect(page.locator('.home-all-tools')).to_be_visible()
    print('PASS: DE/EN mobile search, projects, focus and PDF retention through Umbrel.', flush=True)


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
        page.get_by_label('Dokumenttitel', exact=True).fill('Umbrel 0.14.4')
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
    expect_home(page)
    browser.close()

(evidence / 'result.txt').write_text('PASS: umbrelOS 2.0.0 on amd64; fresh install through Umbrel, protected app gateway, signed-in browser, PDF upload and DE/EN switching, mobile search/projects/document retention, document creation/drafts/PDF export, HTTP and HTTPS app routes, real Office, website conversion, DE/EN translation and speech, restart and persisted models. ARM runtime was not tested.\n')
print((evidence / 'result.txt').read_text())
