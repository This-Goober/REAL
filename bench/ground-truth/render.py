#!/usr/bin/env python3
"""Render a frame EDL from supplied assets, with alpha captions and narration.

No REAL imports. Accepts truth.json or a REAL EDL from bench/fcpxml_edl.py.
For a REAL EDL, pass --media-root REFERENCE/media --audio REFERENCE/narration.wav.
Reject unsupported events instead of silently dropping them.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from PIL import Image


def render(edl_path, output, media_root=None, audio=None):
    edl_path,output=Path(edl_path),Path(output)
    edl=json.loads(edl_path.read_text())
    root=Path(media_root) if media_root else edl_path.parent/'media'
    fps,w,h,total=edl['fps'],edl['w'],edl['h'],edl['total_f']
    if (w,h,fps)!=(720,1280,30): raise ValueError('Expected reference format 720x1280 at 30 fps')
    sources={}; overlays={}; events=edl['events']
    for e in events:
        if e['kind'] not in ('video','image','gap'): raise ValueError(f'Unsupported event: {e}')
        if not 0<=e['f0']<e['f1']<=total: raise ValueError(f'Invalid bounds: {e}')
        aid=e.get('asset')
        if e['kind']=='video' and aid not in sources:
            sources[aid]=root/'Videos'/f'{aid}.mp4'
        if e['kind']=='image' and aid not in overlays:
            overlays[aid]=Image.open(root/'Images'/f'{aid}.png').convert('RGBA')
    if audio is None and edl.get('audio'):
        if edl['audio'].get('start_frame',0)!=0 or edl['audio'].get('gain_db',0)!=0:
            raise ValueError('Only unshifted unity-gain narration is supported')
        audio=edl_path.parent/edl['audio']['file']
    # Decode each clip once to disk; memory use remains bounded to a few frames.
    with tempfile.TemporaryDirectory(prefix='real-reference-') as tmp:
        arrays={}
        for aid,path in sources.items():
            raw=Path(tmp)/f'{aid}.rgb'
            subprocess.run(['ffmpeg','-v','error','-y','-threads','2','-i',str(path),'-f','rawvideo','-pix_fmt','rgb24',str(raw)],check=True)
            frame_bytes=w*h*3
            if raw.stat().st_size%frame_bytes: raise ValueError(f'Wrong source dimensions: {aid}')
            arrays[aid]=np.memmap(raw,dtype=np.uint8,mode='r',shape=(raw.stat().st_size//frame_bytes,h,w,3))
        cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}',
             '-r',str(fps),'-i','-']
        if audio: cmd+=['-i',str(audio)]
        cmd+=['-map','0:v','-c:v','libx264','-threads','2','-preset','fast','-crf','17','-pix_fmt','yuv420p']
        if audio: cmd+=['-map','1:a','-c:a','aac','-b:a','160k']
        cmd+=['-t',str(total/fps),'-movflags','+faststart',str(output)]
        p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        try:
            for f in range(total):
                im=Image.new('RGB',(w,h),'black')
                for e in sorted(events,key=lambda x:x['z']):
                    if not e['f0']<=f<e['f1']: continue
                    if e['kind']=='video':
                        sf=e.get('src_in',0)+f-e['f0']
                        if sf>=len(arrays[e['asset']]): raise ValueError(f'Source too short: {e}')
                        im=Image.fromarray(arrays[e['asset']][sf].copy())
                    elif e['kind']=='image':
                        overlay=overlays[e['asset']]
                        if overlay.size!=(w,h): raise ValueError('Reference overlay size mismatch')
                        im.paste(overlay,(0,0),overlay)
                p.stdin.write(im.tobytes())
        finally:
            p.stdin.close()
        if p.wait(): raise RuntimeError('Reference encoding failed')
    print(output,flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('edl'); ap.add_argument('output')
    ap.add_argument('--media-root'); ap.add_argument('--audio')
    a=ap.parse_args(); render(a.edl,a.output,a.media_root,a.audio)
