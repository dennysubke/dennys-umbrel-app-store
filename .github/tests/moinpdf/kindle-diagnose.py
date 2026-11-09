"""Reproduce the released Kindle roundtrip with fictional data, retaining every stage."""
import json
import sys
import zipfile
from pathlib import Path
sys.path.insert(0, '/service')
import pymupdf
import format_documents
import recovery_documents

out = Path('/evidence')
export = out / 'export'
imported = out / 'import'
export.mkdir(parents=True, exist_ok=True)
imported.mkdir(parents=True, exist_ok=True)
source = export / 'fictional.pdf'
with pymupdf.open() as document:
    for title in ['Fictional MoinPDF format test', 'Second page with text 123.45']:
        page = document.new_page(width=300, height=400)
        page.insert_text((25, 40), title, fontsize=12)
        page.draw_rect((25, 80, 75, 130), color=(1, 0, 0), fill=(1, 0, 0))
    document.save(source)
(export / 'settings.json').write_text(json.dumps({'title': 'Fictional book', 'language': 'en'}))
(imported / 'settings.json').write_text(json.dumps({'paper': 'a5', 'fontSize': 14}))
format_documents.azw3_export(source, export)
format_documents.ebook(export / 'output.azw3', imported)
report = {}
for name in ['converted.epub', 'book.epub', 'output.pdf']:
    path = imported / name
    with pymupdf.open(path) as book:
        if book.is_reflowable:
            book.layout(width=420, height=595, fontsize=14)
            document = pymupdf.open(stream=book.convert_to_pdf(), filetype='pdf')
            document.save(imported / (name + '.pdf'))
        else:
            document = book
        report[name] = [{'number': page.number + 1,
                         'text': page.get_text(),
                         'nonwhite': sum(v < 245 for v in page.get_pixmap().samples),
                         'images': page.get_image_info()} for page in document]
        for page in document:
            page.get_pixmap().save(imported / (name + '-' + str(page.number + 1) + '.png'))
        if document is not book:
            document.close()
    if name.endswith('.epub'):
        with zipfile.ZipFile(path) as archive:
            print('EPUB XML', name)
            for member in archive.namelist():
                if member.endswith(('.xhtml', '.opf')):
                    print(member, archive.read(member).decode()[:20000])
(out / 'report.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
