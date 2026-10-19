#!/usr/bin/env python3
"""ElevenLabs narration with cached takes, timing data, and unchanged video.

Reads only ~/.elevenlabs/env (or the named API key environment variable).
Never stores the key in requests, artifacts, command arguments, or logs.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
import wave

import numpy as np

ROOT=Path(__file__).resolve().parent
VOICE='JBFqnCBsd6RMkjVDRZzb'
VOICE_NAME='George'
VOICES={
    'george':('JBFqnCBsd6RMkjVDRZzb','George'),
    'grandpa-spuds-oxley':('NOpBlnGInO9m6vDvFkFC','Grandpa Spuds Oxley'),
}
MODEL='eleven_multilingual_v2'
RATE=44100


def read_key():
    for name in ('ELEVENLAB_API_KEY','ELEVENLABS_API_KEY'):
        if os.environ.get(name): return os.environ[name]
    for line in (Path.home()/'.elevenlabs/env').read_text().splitlines():
        line=line.strip().removeprefix('export ')
        if '=' not in line or line.startswith('#'): continue
        name,value=line.split('=',1)
        if name.strip() in ('ELEVENLAB_API_KEY','ELEVENLABS_API_KEY'):
            parts=shlex.split(value,comments=True)
            if parts: return parts[0]
    raise ValueError('No ElevenLabs API key found')


def request_take(body, directory):
    directory.mkdir(parents=True,exist_ok=True)
    fingerprint=hashlib.sha256(json.dumps({'voice':VOICE,'body':body},sort_keys=True).encode()).hexdigest()[:20]
    path=directory/f'{fingerprint}.json'
    if path.exists(): return json.loads(path.read_text()),fingerprint
    # Reuse the successful first-line capability check, rather than billing twice.
    test=Path('/tmp/real-eleven-test')
    if (test/'request.json').exists() and json.loads((test/'request.json').read_text())==body and (test/'voice.txt').read_text()==VOICE:
        response=json.loads((test/'response.json').read_text())
    else:
        key=read_key()
        req=urllib.request.Request(f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/with-timestamps?output_format=mp3_44100_128',
            data=json.dumps(body).encode(),headers={'xi-api-key':key,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=120) as r: response=json.load(r)
        except urllib.error.HTTPError as exc:
            detail=json.loads(exc.read().decode().replace(key,'[REDACTED]')).get('detail',{})
            raise RuntimeError(f'ElevenLabs HTTP {exc.code}: {detail.get("message",detail)}') from None
    path.write_text(json.dumps(response))
    (directory/f'{fingerprint}-request.json').write_text(json.dumps({'voice':VOICE,**body},indent=2)+'\n')
    return response,fingerprint


def decode(response):
    raw=subprocess.check_output(['ffmpeg','-v','error','-i','pipe:0','-ac','1','-ar',str(RATE),
        '-f','f32le','pipe:1'],input=base64.b64decode(response['audio_base64']))
    return np.frombuffer(raw,np.float32).copy()


def synthesize(scenes,out):
    full=np.zeros(RATE*30,np.float32)
    reports=[]; words=[]; cursor=0
    for i,scene in enumerate(scenes,1):
        duration,kind,title,text,caption=scene
        speed=1.0
        for attempt in range(3):
            body={'text':text.replace('REAL','Real'),'model_id':MODEL,
                'voice_settings':{'stability':.5,'similarity_boost':.75,'style':.15,
                                  'use_speaker_boost':True,'speed':speed},'seed':41+i}
            if i>1: body['previous_text']=scenes[i-2][3].replace('REAL','Real')
            response,fingerprint=request_take(body,out/'elevenlabs-takes')
            audio=decode(response)
            active=np.flatnonzero(np.abs(audio)>.001)
            if not len(active): raise ValueError(f'Empty audio: {kind}')
            left=max(0,int(active[0])-.05*RATE); left=int(left)
            right=min(len(audio),int(active[-1])+.05*RATE+1); right=int(right)
            audio=audio[left:right]
            seconds=len(audio)/RATE
            if seconds<=duration-.20: break
            next_speed=round(min(1.2,max(speed+.04,speed*seconds/(duration-.25))),3)
            if next_speed<=speed or attempt==2: break
            speed=next_speed
        # A small pitch-preserving adjustment is allowed only if native speed
        # still overshoots. Never clip words to fit a scene.
        tempo=max(1.0,(len(audio)/RATE)/(duration-.20))
        if tempo>1.12: raise ValueError(f'{kind} needs a shorter script; refusing {tempo:.2f}x extra compression')
        if tempo>1:
            raw=subprocess.check_output(['ffmpeg','-v','error','-f','f32le','-ar',str(RATE),'-ac','1','-i','-',
                '-af',f'atempo={tempo:.8f}','-f','f32le','-'],input=audio.tobytes())
            audio=np.frombuffer(raw,np.float32).copy()
        start=cursor+.10
        end=start+len(audio)/RATE
        if end>cursor+duration: raise ValueError(f'Audio overflow in {kind}')
        index=round(start*RATE)
        full[index:index+len(audio)]=audio
        alignment=response.get('normalized_alignment') or response.get('alignment')
        if not alignment: raise ValueError('Missing ElevenLabs character alignment')
        chars=''.join(alignment['characters'])
        for match in re.finditer(r'\S+',chars):
            a=alignment['character_start_times_seconds'][match.start()]
            b=alignment['character_end_times_seconds'][match.end()-1]
            a=max(start,start+(a-left/RATE)/tempo)
            b=min(end,start+(b-left/RATE)/tempo)
            if a<b: words.append({'text':match.group(),'start':round(a,4),'end':round(b,4),'scene':i})
        reports.append({'scene':i,'text':text,'start':start,'end':round(end,4),'speed':speed,
                        'post_tempo':tempo,'cached_take':fingerprint})
        print(f'{out.name}: {kind}: {len(audio)/RATE:.2f}s in {duration}s; native speed {speed}',flush=True)
        cursor+=duration
    assert cursor==30
    gain=.89/float(np.max(np.abs(full))); full*=gain
    with wave.open(str(out/'narration.wav'),'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(RATE)
        wav.writeframes(np.round(full*32767).astype(np.int16).tobytes())
    (out/'narration.json').write_text(json.dumps({'provenance':'ElevenLabs API neural narration',
        'engine':'elevenlabs','model':MODEL,'voice_id':VOICE,'voice_name':VOICE_NAME,'sample_rate':RATE,'duration':30,
        'normalization_gain':gain,'scenes':reports,'word_onsets':words,
        'timing_note':'ElevenLabs character alignment grouped into words and adjusted for padding/tempo. Provider-supplied alignment, not independent forced alignment.'},indent=2)+'\n')


def replace_audio(out):
    # Utility imports do not import or initialize Kokoro.
    from neural_narration import video_hash,refresh_hashes
    out=Path(out)
    shots=json.loads((out/'shots.json').read_text())
    scenes=[((s['end_frame']-s['start_frame'])/30,s['name'],s['name'],s['narration'],s['caption']) for s in shots]
    backup=Path(tempfile.mkdtemp(prefix=f'real-pre-elevenlabs-{out.name}-'))
    for name in ['narration.wav','narration.json','reference.mp4','SHA256SUMS','verification.json','audio-replacement.json']:
        if (out/name).exists(): shutil.copy2(out/name,backup/name)
    before=video_hash(out/'reference.mp4')
    synthesize(scenes,out)
    replacement=out/'reference-elevenlabs.tmp.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(out/'reference.mp4'),'-i',str(out/'narration.wav'),
        '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','160k','-t','30',
        '-movflags','+faststart',str(replacement)],check=True)
    assert video_hash(replacement)==before,'Video stream changed'
    replacement.replace(out/'reference.mp4')
    (out/'audio-replacement.json').write_text(json.dumps({'engine':'elevenlabs','model':MODEL,'voice_id':VOICE,'voice_name':VOICE_NAME,
        'video_stream_unchanged':True,'video_packet_hash':before,'previous_audio_backup':str(backup)},indent=2)+'\n')
    refresh_hashes(out)
    print(f'Updated {out}/reference.mp4 with ElevenLabs; video unchanged',flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('projects',nargs='+',type=Path)
    ap.add_argument('--voice',choices=VOICES,default='george')
    args=ap.parse_args()
    VOICE,VOICE_NAME=VOICES[args.voice]
    for project in args.projects: replace_audio(project)
