"""Check author-identity leakage in the anonymous paper and standalone source.

This is an identity-specific publication check, not a guarantee against inference
from topic or footage. Figure redactions still require visual inspection.
"""
import hashlib
import os
import json
from pathlib import Path
import re
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
# Author-identifying strings. Personal names are deliberately NOT written into
# the repository: put them one per line in ~/.config/real/anonymity-terms.txt
# (or the file named by REAL_ANONYMITY_TERMS) and they are checked as well.
IDENTIFIERS = [
    'Enrica', 'Eidee', 'Selina Lai', 'jaqarx', 'htansetiawan',
    'tanenr@', 's-tanei@', 's-laise@', 'enrica@', 'enrica.ai',
    'Newport High School', 'University of Washington', 'bsd405.org',
    'Google Brain', 'Microsoft Research', '/Users/',
]
_extra = Path(os.environ.get('REAL_ANONYMITY_TERMS',
                             Path.home() / '.config/real/anonymity-terms.txt'))
if _extra.exists():
    IDENTIFIERS += [line.strip() for line in _extra.read_text().splitlines()
                    if line.strip() and not line.startswith('#')]


def check(label, content):
    # Text extraction may wrap names or separate them with arbitrary whitespace.
    normalized = re.sub(r'\s+', ' ', content).casefold()
    found = [value for value in IDENTIFIERS if value.casefold() in normalized]
    if found:
        raise ValueError(f'{label}: identifying author information: {found}')


def main():
    pdf = HERE.parent / 'REAL-HIMAS-2027.pdf'   # the draft PDF sits above .artifacts
    source = HERE / 'REAL-HIMAS-2027-source.zip'
    checked = []
    for name in ['REAL-HIMAS-2027.md', 'REAL-HIMAS-2027.html', 'REAL-HIMAS-2027.tex']:
        check(name, (HERE / name).read_text()); checked.append(name)
    paper_text = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True)
    assert not re.search(r'Author contributions|Acknowledg(?:e)?ments', paper_text, re.I)
    for args, label in [(['pdftotext', '-layout', str(pdf), '-'], 'PDF text'),
                        (['pdfinfo', str(pdf)], 'PDF document information'),
                        (['pdfinfo', '-meta', str(pdf)], 'PDF XMP metadata')]:
        check(label, subprocess.check_output(args, text=True)); checked.append(label)
    with zipfile.ZipFile(source) as package:
        assert package.testzip() is None
        for entry in package.infolist():
            check('source filename', entry.filename)
            if not entry.filename.endswith('.pdf'):
                check(entry.filename, package.read(entry).decode('utf-8'))
        assert 'Anonymous authors' in package.read('main.tex').decode()
        assert not any(name.endswith(('.jpg', '.jpeg', '.png')) for name in package.namelist())
    checked.append('standalone ZIP filenames and all non-PDF source/license text')
    loc = lambda n: (HERE.parent / n) if n in ('REAL-HIMAS-2027.pdf', 'catalogue-path.pdf') else HERE / n
    files = {name: hashlib.sha256(loc(name).read_bytes()).hexdigest()
             for name in ['REAL-HIMAS-2027.pdf', 'REAL-HIMAS-2027-source.zip',
                          'REAL-HIMAS-2027.html', 'catalogue-path.pdf']}
    report = dict(status='passed', files_sha256=files, checked=checked,
                  author_contributions_and_acknowledgments_absent=True,
                  raw_photo_files_in_source_zip=False,
                  figure_redaction='Raster face masks applied before embedding; visual inspection recorded separately.',
                  scope='Known author identifiers only. Scholarly references and third-party tools remain. Internal repository and evidence archives are not anonymous.')
    (HERE / 'anonymity-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Anonymous draft: known author identifiers absent from text, metadata and source ZIP.')


if __name__ == '__main__':
    main()
