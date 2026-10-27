"""Verify current PDF editing and Word export through the signed-in Umbrel gateway.

All documents are synthetic. Outputs are read independently with MuPDF/OOXML;
this is Chromium automation, not a physical-device or native Word test.
"""
import json
import os
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET

import pymupdf
from playwright.sync_api import expect, sync_playwright

origin = os.environ['MOINPDF_TEST_URL'].rstrip('/')
cookies = json.loads(Path(os.environ['MOINPDF_TEST_COOKIES']).read_text())
out = Path('umbrel-evidence/core-exports')
out.mkdir(parents=True, exist_ok=True)
source = out / 'synthetic-layout.pdf'
original = 'MoinPDF original 4815'
replacement = 'MoinPDF edited 4815'
with pymupdf.open() as artwork:
    image_page = artwork.new_page(width=100, height=80)
    image_page.draw_rect(image_page.rect, color=None, fill=(.8, .1, .2))
    image = image_page.get_pixmap().tobytes('png')
with pymupdf.open() as document:
    page = document.new_page(width=500, height=700)
    page.insert_text((40, 80), original, fontsize=18)
    page.insert_text((40, 640), 'KEEP FOOTER', fontsize=12)
    page.insert_image((300, 180, 425, 280), stream=image)
    document.save(source)

with sync_playwright() as api:
    browser = api.chromium.launch()
    for operation in ('edit-text', 'pdf-word'):
        context = browser.new_context(ignore_https_errors=False, viewport={'width': 1440, 'height': 1000},
                                      reduced_motion='reduce', accept_downloads=True)
        context.add_cookies(cookies)
        page = context.new_page()
        page.set_default_timeout(60000)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        try:
            page.goto(origin + '?lang=de')
            page.locator('input[type=file]').first.set_input_files(str(source.resolve()))
            page.locator(f'.chooser-tool[data-tool-id="{operation}"]').click()
            if operation == 'edit-text':
                target = page.get_by_role('button', name='Text bearbeiten: ' + original, exact=True)
                expect(target).to_be_visible(timeout=120000)
                target.click()
                field = page.get_by_label('Text direkt in der PDF bearbeiten', exact=True)
                field.fill(replacement)
                expect(field).to_have_text(replacement)
                field.press('Control+z')
                expect(field).to_have_text(original)
                field.press('Control+y')
                expect(field).to_have_text(replacement)
                page.get_by_role('toolbar', name='Text direkt formatieren', exact=True).get_by_role(
                    'button', name='Fertig', exact=True).click()
                page.get_by_role('button', name='Bearbeitete PDF erstellen', exact=True).click()
                link = page.get_by_role('link', name='PDF herunterladen', exact=True).first
                expect(link).to_be_visible(timeout=240000)
                with page.expect_download() as download:
                    link.click()
                destination = out / 'edited.pdf'
                download.value.save_as(destination)
                with pymupdf.open(destination) as result, pymupdf.open(source) as before:
                    text = ''.join(p.get_text() for p in result)
                    assert replacement in text and original not in text and 'KEEP FOOTER' in text, text
                    assert len(result) == 1 and result[0].rect == before[0].rect
                    clip = pymupdf.Rect(300, 180, 425, 280)
                    assert result[0].get_pixmap(clip=clip).samples == before[0].get_pixmap(clip=clip).samples
                print('PASS: Umbrel original-text edit, undo/redo, real PDF download, removed old text and unchanged image.', flush=True)
            else:
                expect(page.get_by_role('heading', name='PDF zu Word', exact=True)).to_be_visible()
                # Version 0.23.0 starts Word export locally, even with a server.
                expect(page.get_by_role('radio', name='Aussehen möglichst erhalten', exact=True)).to_be_checked()
                expect(page.get_by_role('radio', name='Text und Tabellen bearbeiten', exact=True)).to_be_visible()
                expect(page.locator('.word-export-options')).to_contain_text('Die Word-Datei wird auf deinem Gerät erstellt.')
                expect(page.locator('.word-export-options details')).not_to_have_attribute('open', '')
                page.get_by_role('button', name='Word-Datei erstellen', exact=True).click()
                link = page.get_by_role('link', name='Word herunterladen', exact=True)
                expect(link).to_be_visible(timeout=180000)
                with page.expect_download() as download:
                    link.click()
                destination = out / 'layout.docx'
                download.value.save_as(destination)
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
                      'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture'}
                with zipfile.ZipFile(destination) as archive:
                    assert archive.testzip() is None
                    xml = ET.fromstring(archive.read('word/document.xml'))
                    text = ' '.join(n.text or '' for n in xml.findall('.//w:t', ns))
                    assert original in text and 'KEEP FOOTER' in text, text
                    assert xml.findall('.//w:txbxContent', ns) and xml.findall('.//pic:pic', ns)
                    assert not xml.findall('.//w:vanish', ns)
                    size = xml.find('.//w:sectPr/w:pgSz', ns)
                    assert (int(size.get('{%s}w' % ns['w'])), int(size.get('{%s}h' % ns['w']))) == (10000, 14000)
                    assert any(n.startswith('word/media/') for n in archive.namelist())
                print('PASS: Umbrel real Word download with editable text boxes, embedded imagery and original page size.', flush=True)
            assert not errors, errors
            page.screenshot(path=str(out / f'{operation}.png'), full_page=True)
        except Exception:
            page.screenshot(path=str(out / f'{operation}-failed.png'), full_page=True)
            (out / f'{operation}-failed.html').write_text(page.content())
            raise
        finally:
            context.close()
    browser.close()
