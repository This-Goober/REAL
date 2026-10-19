#!/usr/bin/env python3
"""Verify the distributed video against independent source-media reconstruction.

Checks format, full decoding, hashes, source length, exact EDL coverage, audio,
and pixels immediately before/after each caption boundary and each shot cut.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import wave

import numpy as np
from PIL import Image


def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames',
        '-show_streams','-show_format','-of','json',str(path)]))


def frames(path, indices, w, h):
    expr='+'.join(f'eq(n\\,{i})' for i in indices)
    data=subprocess.check_output(['ffmpeg','-v','error','-threads','2','-i',str(path),
        '-vf',f'select={expr}','-fps_mode','vfr','-f','rawvideo','-pix_fmt','rgb24','-'])
    result=np.frombuffer(data,np.uint8).reshape((-1,h,w,3))
    assert len(result)==len(indices),(path,len(result),len(indices))
    return dict(zip(indices,result))


def verify(root):
    root=Path(root)
    edl=json.loads((root/'truth.json').read_text())
    w,h,n,fps=edl['w'],edl['h'],edl['total_f'],edl['fps']
    assert (w,h,n,fps)==(720,1280,900,30)
    for line in (root/'SHA256SUMS').read_text().splitlines():
        expected,name=line.split('  ',1)
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
    p=probe(root/'reference.mp4')
    v=next(s for s in p['streams'] if s['codec_type']=='video')
    a=next(s for s in p['streams'] if s['codec_type']=='audio')
    assert (v['width'],v['height'],v['r_frame_rate'],int(v['nb_read_frames']))==(w,h,'30/1',n)
    assert abs(float(v['duration'])-30)<1/fps
    assert abs(float(a['duration'])-30)<.05
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(root/'reference.mp4'),'-f','null','-'],check=True)
    with wave.open(str(root/'narration.wav')) as wav:
        sample_rate=wav.getframerate()
        assert wav.getnframes()==sample_rate*30
        signal=np.frombuffer(wav.readframes(wav.getnframes()),np.int16)
        assert np.count_nonzero(signal)>len(signal)*.2
        assert np.max(np.abs(signal.astype(np.int32)))<32767,'Clipped WAV'
    decoded_audio=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',
        str(root/'reference.mp4'),'-vn','-ac','1','-ar',str(sample_rate),'-f','f32le','-']),np.float32)
    assert len(decoded_audio)>=len(signal)
    original=signal.astype(np.float32)/32768
    audio_error=np.mean((decoded_audio[:len(original)]-original)**2)
    audio_snr=99.0 if audio_error==0 else float(10*np.log10(np.mean(original**2)/audio_error))
    assert audio_snr>20,('MP4 audio does not match narration WAV',audio_snr)
    speech=json.loads((root/'narration.json').read_text())
    assert all(0<=s['start']<s['end']<=30 for s in speech['scenes'])
    assert all(0<=s['start']<30 for s in speech['word_onsets'])
    shots=json.loads((root/'shots.json').read_text())
    for spoken,shot in zip(speech['scenes'],shots):
        assert shot['start_frame']/fps<=spoken['start']<spoken['end']<=shot['end_frame']/fps
    coverage=np.zeros(n,int)
    bases=[e for e in edl['events'] if e['kind']=='video']
    overlays=[e for e in edl['events'] if e['kind']=='image']
    samples=set()
    for e in edl['events']:
        assert 0<=e['f0']<e['f1']<=n
        samples.update(f for f in [e['f0']-1,e['f0'],e['f1']-1,e['f1']] if 0<=f<n)
    for e in bases: coverage[e['f0']:e['f1']]+=1
    assert np.all(coverage==1),'Missing or overlapping primary frames'
    samples=sorted(samples)
    reference=frames(root/'reference.mp4',samples,w,h)
    measurements=[]
    for e in bases:
        path=root/'media/Videos'/f"{e['asset']}.mp4"
        srcinfo=next(s for s in probe(path)['streams'] if s['codec_type']=='video')
        assert int(srcinfo['nb_read_frames'])==e['f1']-e['f0']
        local=[f-e['f0'] for f in samples if e['f0']<=f<e['f1']]
        source=frames(path,local,w,h)
        expected_frames=[]
        frame_numbers=[]
        for sf,array in source.items():
            f=sf+e['f0']; expected=Image.fromarray(array)
            for o in overlays:
                if o['f0']<=f<o['f1']:
                    overlay=Image.open(root/'media/Images'/f"{o['asset']}.png").convert('RGBA')
                    expected.paste(overlay,(0,0),overlay)
            expected_frames.append(np.asarray(expected))
            frame_numbers.append(f)
        # Match the delivery video's chroma subsampling before measuring codec
        # error. RGB vs YUV420 directly penalizes correct colored text edges.
        converted=subprocess.check_output(['ffmpeg','-v','error','-filter_threads','1',
            '-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}','-r',str(fps),'-i','-',
            '-vf','format=yuv420p,format=rgb24','-f','rawvideo','-pix_fmt','rgb24','-'],
            input=np.stack(expected_frames).tobytes())
        expected_frames=np.frombuffer(converted,np.uint8).reshape((-1,h,w,3))
        for f,expected in zip(frame_numbers,expected_frames):
            delta=expected.astype(np.float32)-reference[f].astype(np.float32)
            mse=float(np.mean(delta**2))
            psnr=99.0 if mse==0 else float(10*np.log10(255**2/mse))
            caption_mae=float(np.abs(delta[1100:1190]).mean())
            measurements.append({'frame':f,'psnr_db':round(psnr,3),'caption_mae':round(caption_mae,4)})
            assert psnr>35,(f,psnr)
            assert caption_mae<2,(f,'caption mismatch',caption_mae)
    report={'passed':True,'video':{'width':w,'height':h,'fps':fps,'frames':n,'seconds':30},
        'audio':'30-second non-silent synthetic narration, AAC and WAV',
        'audio_engine':speech.get('engine','espeak'),'audio_wav_match_snr_db':round(audio_snr,3),
        'primary_coverage':'exactly one shot on every frame','asset_hashes':'all match',
        'full_decode':'passed','boundary_frames_checked':len(measurements),
        'minimum_boundary_psnr_db':min(m['psnr_db'] for m in measurements),
        'boundary_psnr':sorted(measurements,key=lambda x:x['frame']),
        'scope':'Verifies independent reference construction, not REAL reproduction or Final Cut import.'}
    (root/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(root.name, 'PASS', len(measurements),'boundary frames, minimum PSNR',report['minimum_boundary_psnr_db'])


if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('projects',nargs='+'); a=ap.parse_args()
    for path in a.projects: verify(path)
