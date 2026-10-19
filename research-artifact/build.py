"""Package the current paper with the verified v5 experiment snapshot and E03 replay."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA256 = '5eea96567a69e5200ab4f2f5033b5643876d510b1cc2ff098473ac1323300526'
PREFIX = 'REAL-research/'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def paper_input(path):
    """Exclude compiler scratch files and caches, retaining saved review evidence."""
    return (path.is_file() and not path.is_symlink()
            and '__pycache__' not in path.parts
            and not path.name.startswith('.')
            and '-render.' not in path.name
            and path.suffix not in {'.aux', '.log', '.blg', '.bbl', '.pyc', '.out'})


def build(base, out):
    if out.exists():
        raise ValueError('refusing to overwrite an existing version: ' + str(out))
    if digest(base.read_bytes()) != BASE_SHA256:
        raise ValueError('base archive does not match the verified v5 snapshot')
    with zipfile.ZipFile(base) as archive:
        if archive.testzip() is not None:
            raise ValueError('base archive CRC failure')
        old = json.loads(archive.read(PREFIX + 'ARTIFACT-MANIFEST.json'))
        payload = {}
        for name, record in old['files'].items():
            if Path(name).is_absolute() or '..' in Path(name).parts:
                raise ValueError('unsafe base path: ' + name)
            data = archive.read(PREFIX + name)
            if digest(data) != record['sha256'] or len(data) != record['bytes']:
                raise ValueError('base manifest mismatch: ' + name)
            payload[name] = data
    # Preserve the complete evaluated code/data, not the evolving working tree.
    # Replace document files as a unit so obsolete render logs cannot masquerade
    # as verification of this candidate. The v5 archive itself remains intact.
    removed = [name for name in payload if name.startswith(('paper/himas-2027/',
                                                           'research-artifact/'))]
    for name in removed:
        del payload[name]
    overlaid = []

    def overlay(path):
        if path.is_symlink() or not path.is_file():
            raise ValueError('invalid overlay input: ' + str(path))
        name = path.relative_to(ROOT).as_posix()
        payload[name] = path.read_bytes()
        overlaid.append(name)

    paper = ROOT / 'paper/himas-2027'
    review = json.loads((paper / 'review-artifacts.json').read_text())
    if not 8 <= review['main_text_pages'] <= 9:
        raise ValueError('short-paper package requires eight or nine checked body pages')
    for name, expected in review['files_sha256'].items():
        if digest((paper / name).read_bytes()) != expected:
            raise ValueError('paper changed after its recorded checks: ' + name)
    if review['pdfa_validation']['pdf_sha256'] != review['files_sha256']['REAL-HIMAS-2027.pdf']:
        raise ValueError('PDF validation receipt belongs to another version')
    for path in sorted(paper.rglob('*')):
        if paper_input(path):
            overlay(path)
    for name in ['paper/README.md', 'paper/review-archive/REAL-expanded-20261018.zip',
                 'paper/review-archive/REAL-ten-page-20261018.zip',
                 'research-artifact/README.md', 'research-artifact/build.py',
                 'research-artifact/verify.py']:
        overlay(ROOT / name)
    replay = ROOT / 'experiments/E03-oneshot-baselines'
    overlay(replay / 'OFFLINE-REPLAY.md')
    for path in sorted((replay / 'results/offline-20261018').iterdir()):
        if path.is_file():
            overlay(path)
    # Assert that every code and evidence file outside the declared overlays
    # still has the exact base bytes. No production project/demo ZIP is added.
    for name, record in old['files'].items():
        if name not in removed and name not in overlaid:
            if digest(payload[name]) != record['sha256']:
                raise ValueError('unexpected experiment mutation: ' + name)
    if any(name.startswith('demo/paganini-no23/') for name in payload):
        raise ValueError('production project is not a research-package input')
    manifest = dict(
        format='REAL-review-artifact-v2',
        version='v7-short-paper-20261018',
        status='local review candidate; author approval and publication pending',
        entry_point='research-artifact/README.md',
        provenance=dict(base_archive_sha256=BASE_SHA256,
                        base_files_verified=len(old['files']),
                        overlaid_paths=sorted(overlaid),
                        removed_base_paths=sorted(removed),
                        evaluated_code_policy='All evaluated code/data retain verified v5 bytes. E03 replay is a separately frozen supplement.'),
        files={name: dict(sha256=digest(data), bytes=len(data))
               for name, data in sorted(payload.items())})
    payload['ARTIFACT-MANIFEST.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(PREFIX + name, (2026, 10, 18, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    checksum = digest(out.read_bytes())
    out.with_suffix(out.suffix + '.sha256').write_text(checksum + '  ' + out.name + '\n')
    print(json.dumps(dict(path=str(out), files=len(payload), bytes=out.stat().st_size,
                          sha256=checksum, experiment_code_unchanged=True), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path,
                        default=ROOT / 'paper/artifacts/REAL-HIMAS-2027-artifact-v5.zip')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    build(args.base, args.out)
