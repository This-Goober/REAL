#!/usr/bin/env python3
"""Kokoro neural narration and audio-only replacement for the reference films.

Uses public Kokoro-82M weights and af_heart, entirely locally after download.
Word times are model predictions, never claimed as forced alignment.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = 'hexgrad/Kokoro-82M'
FILES = ['config.json', 'kokoro-v1_0.pth', 'voices/af_heart.pt']
_pipeline = None


def model_directory(value=None):
    return Path(value or os.environ.get('REAL_KOKORO_DIR', '/tmp/real-kokoro'))


def download(directory):
    directory.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        target = directory / Path(name).name
        if not target.exists():
            temporary = target.with_suffix(target.suffix + '.download')
            urllib.request.urlretrieve(f'https://huggingface.co/{REPO}/resolve/main/{name}', temporary)
            temporary.replace(target)


def pipeline(directory):
    global _pipeline
    if _pipeline is None:
        import torch
        from kokoro import KModel, KPipeline
        torch.set_num_threads(2)
        torch.manual_seed(0)
        for name in FILES:
            if not (directory / Path(name).name).exists():
                raise FileNotFoundError(f'Missing {name}; run neural_narration.py --download first')
        model = KModel(repo_id=REPO, config=str(directory/'config.json'),
                       model=str(directory/'kokoro-v1_0.pth')).to('cpu').eval()
        _pipeline = KPipeline(lang_code='a', repo_id=REPO, model=model, device='cpu')
    return _pipeline


def synthesize(scenes, out, directory=None):
    import soundfile as sf
    import kokoro
    directory = model_directory(directory)
    engine = pipeline(directory)
    rate = 24000
    full = np.zeros(rate * 30, np.float32)
    reports, onsets = [], []
    cursor = 0
    for i, scene in enumerate(scenes, 1):
        dur, kind, title, text, caption = scene
        spoken = text.replace('REAL', 'Real')
        speed = 1.0
        for attempt in range(6):
            chunks, tokens, offset = [], [], 0.0
            for result in engine(spoken, voice=str(directory/'af_heart.pt'), speed=speed):
                audio = result.audio.numpy().astype(np.float32)
                chunks.append(audio)
                for token in result.tokens or []:
                    if getattr(token, 'start_ts', None) is not None:
                        tokens.append({'text': token.text, 'start': offset+token.start_ts,
                                       'end': offset+token.end_ts})
                offset += len(audio)/rate
            audio = np.concatenate(chunks)
            # Remove synthesis padding, leaving 50 ms around audible material.
            active = np.flatnonzero(np.abs(audio) > 0.001)
            if not len(active):
                raise ValueError(f'Empty synthesis in {kind}')
            left = max(0, int(active[0])-1200)
            right = min(len(audio), int(active[-1])+1201)
            audio = audio[left:right]
            if len(audio)/rate <= dur-.20:
                break
            speed = round(max(speed+.03, speed*(len(audio)/rate)/(dur-.25)), 3)
            if speed > 1.35:
                raise ValueError(f'{kind} needs an editorial adjustment; refusing rushed voice at {speed}x')
        else:
            raise ValueError(f'Could not fit {kind}')
        start = cursor + .10
        index = round(start*rate)
        full[index:index+len(audio)] = audio
        end = start+len(audio)/rate
        for token in tokens:
            token['start'] = round(max(start, start+token['start']-left/rate), 4)
            token['end'] = round(min(end, start+token['end']-left/rate), 4)
            if token['start'] < token['end']:
                token['scene'] = i
                onsets.append(token)
        reports.append({'scene':i,'text':text,'synthesis_text':spoken,'start':start,
                        'end':round(end,4),'speed':speed})
        print(f'{out.name}: {kind}: {len(audio)/rate:.2f}s in {dur}s, speed {speed}', flush=True)
        cursor += dur
    assert cursor == 30
    # Common peak normalization preserves relative line loudness without clipping.
    gain = .89 / float(np.max(np.abs(full)))
    full *= gain
    sf.write(str(out/'narration.wav'), full, rate, subtype='PCM_16')
    report = {'provenance':'Kokoro-82M neural synthesis, af_heart US English narrator',
              'engine':'kokoro','engine_version':kokoro.__version__,'model':REPO,'voice':'af_heart',
              'sample_rate':rate,'duration':30,'normalization_gain':gain,
              'scenes':reports,'word_onsets':onsets,
              'timing_note':'Token start/end times are Kokoro duration-model predictions, adjusted for removed synthesis padding; not measured or forced-aligned word times.',
              'model_sha256':{Path(name).name:hashlib.sha256((directory/Path(name).name).read_bytes()).hexdigest() for name in FILES}}
    (out/'narration.json').write_text(json.dumps(report,indent=2)+'\n')


def video_hash(path):
    return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:v:0',
        '-c','copy','-f','hash','-hash','sha256','-'],text=True).strip()


def refresh_hashes(out):
    files = sorted(p for p in out.rglob('*') if p.is_file() and p.name not in ('SHA256SUMS','verification.json'))
    (out/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out)}\n' for p in files))


def replace_audio(out, directory):
    out = Path(out)
    shots = json.loads((out/'shots.json').read_text())
    scenes = [((s['end_frame']-s['start_frame'])/30,s['name'],s['name'],s['narration'],s['caption']) for s in shots]
    backup = Path(tempfile.mkdtemp(prefix=f'real-previous-audio-{out.name}-'))
    for name in ['narration.wav','narration.json','reference.mp4','SHA256SUMS','verification.json']:
        if (out/name).exists(): shutil.copy2(out/name,backup/name)
    before = video_hash(out/'reference.mp4')
    synthesize(scenes,out,directory)
    replacement = out/'reference-neural.tmp.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(out/'reference.mp4'),'-i',str(out/'narration.wav'),
        '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','160k','-t','30',
        '-movflags','+faststart',str(replacement)],check=True)
    assert video_hash(replacement) == before, 'Video stream changed during audio replacement'
    replacement.replace(out/'reference.mp4')
    (out/'audio-replacement.json').write_text(json.dumps({'engine':'Kokoro-82M','voice':'af_heart',
        'video_stream_unchanged':True,'video_packet_hash':before,'previous_audio_backup':str(backup)},indent=2)+'\n')
    refresh_hashes(out)
    print(f'Updated {out}/reference.mp4; video stream unchanged',flush=True)


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('projects',nargs='*',type=Path)
    ap.add_argument('--model-dir',type=Path,default=model_directory())
    ap.add_argument('--download',action='store_true')
    args=ap.parse_args()
    if args.download: download(args.model_dir)
    for out in args.projects: replace_audio(out,args.model_dir)
