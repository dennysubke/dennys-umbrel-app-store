"""Released workspace controls through Umbrel's authenticated app gateway."""
import json
import os
from pathlib import Path
import tempfile
import time
import pymupdf
from playwright.sync_api import expect, sync_playwright

origin = os.getenv('MOINPDF_TEST_URL', 'http://localhost:8080').rstrip('/')
out = Path('umbrel-evidence/workspace-controls'); out.mkdir(parents=True, exist_ok=True)

def recovery_summaries(page):
    return page.evaluate('''() => new Promise((resolve, reject) => {
        const request = indexedDB.open('moinpdf.workspace.v1');
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const tx = db.transaction('recovery');
            const get = tx.objectStore('recovery').getAll();
            tx.oncomplete = () => {
                db.close();
                resolve(get.result.map(({id, updated}) => ({id, updated})).sort((a,b) => b.updated-a.updated));
            };
            tx.onerror = () => { db.close(); reject(tx.error); };
        };
    })''')

def check_clear_dialog(page):
    page.get_by_role('button', name='Arbeitsbereich leeren', exact=True).click()
    dialog = page.get_by_role('alertdialog')
    clear = dialog.get_by_role('button', name='Leeren', exact=True)
    expect(clear).to_have_attribute('data-variant', 'destructive')
    color = clear.evaluate('(button) => getComputedStyle(button).backgroundColor')
    assert color in ['rgb(195, 39, 70)', 'rgb(169, 29, 57)'], color
    dialog.get_by_role('button', name='Behalten', exact=True).click()
    expect(dialog).not_to_be_visible()

with sync_playwright() as api, tempfile.TemporaryDirectory() as temporary:
    browser = api.chromium.launch()
    source = Path(temporary) / 'workspace.pdf'
    with pymupdf.open() as pdf:
        for text in ['First original page', 'Second original page']:
            pdf.new_page().insert_text((50, 60), text)
        pdf.save(source)
    try:
        for width in [1440, 390]:
            context = browser.new_context(viewport={'width': width, 'height': 950})
            context.add_cookies(json.loads(Path(os.environ['MOINPDF_TEST_COOKIES']).read_text()))
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda message: print(message.text, flush=True) if message.text.startswith('WORKSPACE_RECOVERY ') else None)
            page.add_init_script('''(() => {
                const put = IDBObjectStore.prototype.put;
                IDBObjectStore.prototype.put = function(value, ...rest) {
                    if (this.name === 'recovery') console.log('WORKSPACE_RECOVERY ' + JSON.stringify({pages:value.state.pages.length,history:value.state.history.map(s => s.pages.length),future:value.state.future.map(s => s.pages.length),sources:value.sources.map(s => s.name)}));
                    return put.call(this,value,...rest);
                };
            })()''')
            try:
                page.goto(origin)
                page.locator('input[type=file]').first.set_input_files(str(source))
                check_clear_dialog(page)
                page.get_by_role('button', name='Seiten organisieren', exact=True).click()
                check_clear_dialog(page)
                page.get_by_role('button', name='Seite 2 entfernen', exact=True).click()
                page.get_by_role('button', name='Seiten speichern', exact=True).click()
                page.get_by_role('button', name='Ergebnis weiterbearbeiten', exact=True).click()
                page.locator('.history-tools').get_by_role('button', name='Rückgängig', exact=True).click()
                page.locator('.history-tools').get_by_role('button', name='Rückgängig', exact=True).click()
                expect(page.get_by_role('button', name='Seite 2 entfernen', exact=True)).to_be_visible()
                page.locator('.history-tools').get_by_role('button', name='Wiederholen', exact=True).click()
                page.locator('.history-tools').get_by_role('button', name='Wiederholen', exact=True).click()
                expect(page.locator('.history-tools').get_by_role('button', name='Wiederholen', exact=True)).to_be_disabled()
                expect(page.get_by_role('button', name='Seite 2 entfernen', exact=True)).to_have_count(0)
                # wait_for_function treats a returned Promise as truthy before it
                # resolves. Poll completed IndexedDB reads before reloading.
                deadline = time.monotonic() + 10
                while not page.evaluate('''() => new Promise(resolve => {
                    const request = indexedDB.open('moinpdf.workspace.v1');
                    request.onerror = () => resolve(false);
                    request.onsuccess = () => {
                        const db = request.result;
                        const get = db.transaction('recovery').objectStore('recovery').getAll();
                        get.onsuccess = () => {
                            const values = get.result.sort((a,b) => b.updated-a.updated);
                            const value = values[0];
                            db.close();
                            resolve(values.length >= 2 && new Set(values.map(v => v.id)).size === values.length
                                && value?.id !== 'current' && value?.state.history.length >= 2
                                && value?.state.pages.length === 1 && value?.sources.length === 2);
                        };
                    };
                })'''):
                    assert time.monotonic() < deadline, 'The edited workspace was not saved for recovery'
                    page.wait_for_timeout(100)
                page.reload()
                page.get_by_role('button', name='Letzten Arbeitsstand wiederherstellen', exact=True).click()
                expect(page.locator('main h1')).to_have_text('Seiten organisieren')
                expect(page.get_by_role('button', name='Seite 1 entfernen', exact=True)).to_be_visible()
                expect(page.get_by_role('button', name='Seite 2 entfernen', exact=True)).to_have_count(0)
                page.locator('.history-tools').get_by_role('button', name='Rückgängig', exact=True).click()
                page.locator('.history-tools').get_by_role('button', name='Rückgängig', exact=True).click()
                expect(page.get_by_role('button', name='Seite 2 entfernen', exact=True)).to_be_visible()
                navigation = page.locator('.harbor-mobile-nav' if width == 390 else '.harbor-desktop-nav')
                navigation.get_by_role('button', name='Mehr', exact=True).click()
                page.get_by_role('menuitem', name='Ergebnisse und Aufträge', exact=True).click()
                tray = page.get_by_role('dialog')
                expect(tray.get_by_role('button', name='Herunterladen', exact=True)).to_be_visible()
                with page.expect_download() as download:
                    tray.get_by_role('button', name='Herunterladen', exact=True).click()
                with pymupdf.open(download.value.path()) as pdf:
                    assert len(pdf) == 1
                    assert 'First original page' in pdf[0].get_text()
                page.keyboard.press('Escape')
                # Multiple document snapshots used to make Discard immediately
                # reappear with an indistinguishable older workspace.
                page.reload()
                expect(page.get_by_role('button', name='Verwerfen', exact=True)).to_be_visible()
                before = recovery_summaries(page)
                assert len(before) >= 2, before
                page.get_by_role('button', name='Verwerfen', exact=True).click()
                expect(page.get_by_role('button', name='Verwerfen', exact=True)).to_have_count(0)
                expect(page.get_by_text('Arbeitsstand verworfen.', exact=True)).to_be_visible()
                after = recovery_summaries(page)
                assert after == before[1:], (before, after)
                page.reload()
                saved = page.get_by_role('button', name='Gesicherte Arbeitsstände', exact=True)
                expect(saved).to_be_visible()
                expect(page.get_by_role('button', name='Verwerfen', exact=True)).to_have_count(0)
                assert recovery_summaries(page) == after
                saved.click()
                page.get_by_role('menuitemradio').first.click()
                expect(page.get_by_role('button', name='Verwerfen', exact=True)).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                assert not errors, errors
                page.screenshot(path=str(out / f'workspace-{width}.png'), full_page=True)
                print(f'PASS: {width}px result adoption undo/redo, reload recovery, actual snapshot deletion, reload dismissal, other-snapshot selection, destructive dialogs and result download')
            except Exception:
                page.screenshot(path=str(out / f'workspace-failure-{width}.png'), full_page=True)
                print(page.locator('body').inner_text(), flush=True)
                raise
            finally: context.close()
    finally: browser.close()
