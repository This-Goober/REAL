"""Package the confirmed Paganini v4 edit and only its referenced media.

No compilation, timeline edits, media encoding, or Final Cut automation.
Usage: python3 build_zip.py --xml PATH --media-root PATH [--output PATH]
The optional media root also allows rebuilding from an extracted ZIP's Media.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROJECT = ROOT / 'bench/work/media/paganini-23-octaves-60s'
CONFIRMED_SHA = '4818312007c9c27d478bc6ca792c0d33767e44fdfcfda5ea3666fe2a157384c3'
FOLDER = 'paganini_no23_tutorial'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build(xml_path, output, media_root=None):
    data = xml_path.read_bytes()
    if digest(data) != CONFIRMED_SHA:
        raise ValueError('Input is not the creator-confirmed v4 XML; review the edit before packaging.')
    root = ET.fromstring(data)
    files = {}
    template = data.decode('utf-8')
    for rep in root.findall('.//media-rep'):
        uri = rep.attrib['src']
        parsed = urlparse(uri)
        if parsed.scheme != 'file' or parsed.netloc not in ('', 'localhost'):
            raise ValueError('Only local media can be packaged: ' + uri)
        source = Path(unquote(parsed.path))
        if source.parent.name not in ('takes', 'stills'):
            raise ValueError('Unexpected media location: ' + str(source))
        relative = Path(source.parent.name) / source.name
        if media_root:
            source = media_root / relative
        if not source.is_file():
            raise FileNotFoundError(source)
        entry = 'Media/' + relative.as_posix()
        if entry in files:
            raise ValueError('Duplicate media name: ' + entry)
        files[entry] = source.read_bytes()
        # Change media locations only; leave title settings and timing byte-for-byte.
        template = template.replace(uri, 'file:///__REAL_PAGANINI_MEDIA__/' + relative.as_posix())
    if len(files) != 14 or len(re.findall('file:///__REAL_PAGANINI_MEDIA__/', template)) != 14:
        raise ValueError('v4 must contain exactly 14 media resources')
    if len(root.findall('.//title')) != 5 or root.find('.//sequence').get('duration') != '2441/30s':
        raise ValueError('Unexpected v4 structure')
    files['.support/timeline.template.xml'] = template.encode('utf-8')
    checksums = ''.join(f'{digest(payload)}  {name}\n' for name, payload in sorted(files.items()))
    files['.support/SHA256SUMS.txt'] = checksums.encode('utf-8')
    files['Prepare for Final Cut.command'] = (HERE / 'Prepare for Final Cut.command').read_bytes()
    files['README.txt'] = (HERE / 'PACKAGE-README.txt').read_bytes()
    source_bytes = sum(len(value) for name, value in files.items() if name.startswith('Media/'))
    output.parent.mkdir(parents=True, exist_ok=True)
    # Fixed timestamps make the archive reproducible for identical input bytes.
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix='.zip', delete=False) as temporary:
        staging = Path(temporary.name)
    try:
        with zipfile.ZipFile(staging, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, payload in sorted(files.items()):
                info = zipfile.ZipInfo(FOLDER + '/' + name, date_time=(2026, 10, 18, 0, 0, 0))
                info.create_system = 3
                info.compress_type = zipfile.ZIP_DEFLATED
                mode = 0o100755 if name.endswith('.command') else 0o100644
                info.external_attr = mode << 16
                archive.writestr(info, payload, compresslevel=9)
        with zipfile.ZipFile(staging) as archive:
            if archive.testzip() is not None:
                raise ValueError('ZIP integrity check failed')
        staging.replace(output)
    finally:
        staging.unlink(missing_ok=True)
    receipt = dict(archive=output.name, archive_bytes=output.stat().st_size,
                   archive_sha256=digest(output.read_bytes()), media_files=14,
                   media_bytes=source_bytes, confirmed_source_xml_sha256=CONFIRMED_SHA,
                   media_reencoded=False, native_glow_visible_confirmed_by='the authors',
                   native_glow_confirmation='ok the v4 has glow in it.',
                   confirmation_scope='Visible Glow in the source v4 import; relocated package requires a new import.')
    output.with_suffix('.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xml', type=Path, default=PROJECT / 'Paganini-23-INTRO-GLOW-v4.fcpxml')
    parser.add_argument('--media-root', type=Path)
    parser.add_argument('--output', type=Path, default=HERE / 'paganini_no23_tutorial.zip')
    args = parser.parse_args()
    build(args.xml, args.output, args.media_root)
