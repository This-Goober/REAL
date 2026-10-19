"""Small, auditable data and provenance helpers. No model calls here."""
import hashlib
import json
import math
from pathlib import Path
import subprocess
import urllib.request


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(text)
    tmp.replace(path)


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = ''.join(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n' for r in rows)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(text)
    tmp.replace(path)


def download(url, path, expected=None, max_bytes=256 * 1024 * 1024):
    """Bounded download; never accept a stale or partly downloaded pinned file."""
    path = Path(path)
    if path.exists():
        if expected and sha256(path) != expected:
            raise ValueError('cached file hash mismatch: ' + str(path))
        return sha256(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.part')
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'REAL-academic-eval/1'})
        with urllib.request.urlopen(req, timeout=60) as response, tmp.open('wb') as f:
            total = 0
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > max_bytes:
                    raise ValueError('download exceeds byte limit: ' + url)
                f.write(block)
        digest = sha256(tmp)
        if expected and digest != expected:
            raise ValueError('download hash mismatch: ' + url)
        tmp.replace(path)
        return digest
    finally:
        tmp.unlink(missing_ok=True)


def finite(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def validate_spans(spans, duration=None, scored=False):
    if not isinstance(spans, list):
        raise ValueError('spans must be a list')
    for span in spans:
        if not isinstance(span, (list, tuple)) or len(span) != (3 if scored else 2):
            raise ValueError('invalid span shape')
        if not all(finite(v) for v in span):
            raise ValueError('span contains a non-finite number')
        if not 0 <= span[0] < span[1] or (duration is not None and span[1] > duration + 1e-6):
            raise ValueError('span out of bounds: ' + repr(span))
    return spans


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                        '-of', 'json', str(path)], capture_output=True, text=True, check=True)
    data = json.loads(r.stdout)
    stream = next(s for s in data['streams'] if s['codec_type'] == 'video')
    return {'duration': float(stream.get('duration') or data['format']['duration']),
            'fps': stream['avg_frame_rate'], 'width': stream['width'], 'height': stream['height']}
