"""Freeze a small author-review bundle without changing evaluated evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / 'paper/himas-2027'
ART = PAPER / '.artifacts'


def build(out):
    if out.exists():
        raise ValueError('refusing to replace an existing review snapshot')
    receipt = json.loads((ART / 'review-artifacts.json').read_text())
    for name, expected in receipt['files_sha256'].items():
        if hashlib.sha256((PAPER / name).read_bytes()).hexdigest() != expected:
            raise ValueError('paper changed after its checks: ' + name)
    payload = {'upload-candidate/REAL-HIMAS-2027.pdf': (PAPER / 'REAL-HIMAS-2027.pdf').read_bytes()}
    for name in ['REAL-HIMAS-2027-source.zip', 'REAL-HIMAS-2027.html', 'README.md',
                 'CLAIM-EVIDENCE.md', 'review-artifacts.json', 'anonymity-audit.json']:
        where = PAPER if name == 'README.md' else ART
        payload['author-review/' + name] = (where / name).read_bytes()
    payload['README.txt'] = (ROOT / 'paper/submission/README.md').read_bytes()
    manifest = {'status': 'Author-review working package; no submission or policy certification',
                'main_text_pages': receipt['main_text_pages'], 'total_pages': receipt['pages'],
                'author_approved': False,
                'files': {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
                          for name, data in sorted(payload.items())}}
    payload['MANIFEST.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(name, (2026, 10, 18, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            package.writestr(info, data)
    checksum = hashlib.sha256(out.read_bytes()).hexdigest()
    out.with_suffix(out.suffix + '.sha256').write_text(checksum + '  ' + out.name + '\n')
    print(json.dumps({'path': str(out), 'bytes': out.stat().st_size, 'sha256': checksum}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    build(parser.parse_args().out)
