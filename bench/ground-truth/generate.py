#!/usr/bin/env python3
"""Independent, deterministic artwork/assembly for Fable's two reference reels.

No REAL pipeline modules are imported. Pillow + numpy + ffmpeg + ElevenLabs.
Run from anywhere: python3 generate.py [--project transformer-math-30s]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
W, H, FPS, TOTAL = 720, 1280, 30, 900
BG = '#0b101b'
PANEL = '#151e2e'
EDGE = '#2c3950'
WHITE = '#f3f5fa'
MUTED = '#a3b2c9'
BLUE, GREEN, ORANGE = '#67afff', '#70dfae', '#ffb56d'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'

# All creative timing decisions live here, before running the system under test.
# Durations sum to precisely 900 frames; captions remain separate timeline events.
PROJECTS = {
 'transformer-math-30s': [
  (4, 'hook', 'One line. Many connections.', 'Attention starts with one line of math. Here is how it works.', 'one line'),
  (5, 'vectors', 'Three views of each token.', 'Each token becomes a query, a key, and a value, using three learned projections.', 'Q · K · V'),
  (4, 'scores', 'Compare a query to every key.', 'Dot products compare each query with every key.', 'compare tokens'),
  (5, 'softmax', 'Turn scores into weights.', 'Divide by the square root of the key dimension, then apply softmax.', 'weights sum to 1'),
  (5, 'mix', 'Mix the values.', 'The weights blend the values into a new vector for each token.', 'weighted sum'),
  (4, 'context', 'Attention adds context.', 'Transformers add feed-forward layers and residual paths.', 'one part of a transformer'),
  (3, 'formula', 'That is attention.', 'That is scaled dot-product attention.', "that's attention"),
 ],
 'real-tutorial-30s': [
  (4, 'clutter', 'Your footage. A clear plan.', 'REAL helps assemble your footage into an editable project.', 'it shows its work'),
  (4, 'notebook', '01 / Notebook', 'First, a notebook holds your script and shot ideas.', 'NOTEBOOK.md'),
  (4, 'catalogue', '02 / Catalogue', 'A catalogue describes your media and flags what is unknown.', 'asset-catalog.json'),
  (7, 'anchor', '03 / Reel', 'The reel pins pictures to narration words. Re-record the line, and timing follows those anchors.', 'pinned to words'),
  (5, 'compile', '04 / Compile', 'Compile the approved edit into a Final Cut project, with editable clips and titles.', 'timeline.fcpxml'),
  (3, 'refuse', 'Make uncertainty visible.', 'Unsupported edits are flagged instead of guessed.', 'refuses, never guesses'),
  (3, 'end', 'Now reproduce this edit.', 'This reference is the target for REAL.', 'REFERENCE FOR REAL'),
 ],
}


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')


_fonts = {}
def font(size, bold=False, mono=False):
    key = (size, bold, mono)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(MONO if mono else BOLD if bold else FONT, size)
    return _fonts[key]


def text(d, xy, s, size=28, fill=WHITE, bold=False, anchor=None, mono=False):
    d.text(xy, s, font=font(size, bold, mono), fill=fill, anchor=anchor)


def lines(d, xy, s, size=28, fill=WHITE, width=610, bold=False, gap=12):
    x, y = xy
    row = ''
    for word in s.split():
        trial = (row + ' ' + word).strip()
        if d.textlength(trial, font=font(size, bold)) > width and row:
            text(d, (x, y), row, size, fill, bold)
            row, y = word, y + size + gap
        else:
            row = trial
    text(d, (x, y), row, size, fill, bold)
    return y + size + gap


def card(d, box, fill=PANEL, outline=EDGE, radius=22):
    d.rounded_rectangle(box, radius, fill=fill, outline=outline, width=2)


def arrow(d, start, end, fill=MUTED, width=4):
    d.line([start, end], fill=fill, width=width)
    a = math.atan2(end[1]-start[1], end[0]-start[0])
    pts = [end] + [(end[0]-15*math.cos(a+s), end[1]-15*math.sin(a+s)) for s in (-.5, .5)]
    d.polygon(pts, fill=fill)


def ease(t):
    t = min(1, max(0, t))
    return t*t*(3-2*t)


def formula(d, cy=570):
    card(d, (44, cy-110, 676, cy+160))
    text(d, (360, cy-72), 'Attention(Q, K, V)', 33, WHITE, True, 'mm')
    text(d, (162, cy+30), 'softmax', 33, WHITE, False, 'mm')
    text(d, (299, cy+26), '(', 72, MUTED, False, 'mm')
    text(d, (392, cy-6), 'QKᵀ', 43, BLUE, True, 'mm')
    d.line((334, cy+30, 451, cy+30), fill=MUTED, width=2)
    text(d, (392, cy+65), '√dₖ', 38, GREEN, False, 'mm')
    text(d, (485, cy+26), ')', 72, MUTED, False, 'mm')
    text(d, (560, cy+30), 'V', 56, ORANGE, True, 'mm')


def vector(d, x, y, color, label, vals=(.3,.8,.5,.65)):
    text(d, (x+55, y-40), label, 30, color, True, 'mm')
    for j, val in enumerate(vals):
        card(d, (x, y+j*35, x+110, y+j*35+25), '#1c293b', color, 5)
        d.rounded_rectangle((x+3,y+j*35+3,x+3+int(102*val),y+j*35+22),4,fill=color)


def artwork(project, scene, f, n):
    kind, title = scene[1:3]
    t = f / FPS
    im = Image.new('RGB', (W,H), BG)
    d = ImageDraw.Draw(im)
    # Quiet grid establishes a consistent visual identity without competing with math.
    for x in range(0,W,60): d.line((x,300,x,1060), fill='#111a29')
    for y in range(300,1060,60): d.line((0,y,W,y), fill='#111a29')
    is_math = project.startswith('transformer')
    accent = BLUE if is_math else GREEN
    text(d,(48,58),'REAL / REFERENCE FILM',20,MUTED,True)
    text(d,(48,112),'ATTENTION, EXPLAINED' if is_math else 'AN EDIT YOU CAN INSPECT',20,accent,True)
    lines(d,(44,177),title,45,WHITE,632,True,10)
    d.line((48,328,672,328),fill=EDGE,width=2)

    if kind in ('hook','formula'):
        formula(d,580)
        if kind == 'hook':
            text(d,(360,862),'QUERY   ×   KEY   →   WEIGHTS   ×   VALUE',22,MUTED,False,'mm')
        else:
            for x,c,l in [(150,BLUE,'COMPARE'),(360,GREEN,'NORMALIZE'),(570,ORANGE,'MIX')]:
                d.ellipse((x-5,805,x+5,815),fill=c)
                text(d,(x,855),l,21,c,True,'mm')
    elif kind == 'vectors':
        card(d,(250,384,470,478))
        text(d,(360,431),'token x',32,WHITE,True,'mm')
        for x,c,l,w in [(85,BLUE,'Q','WQ'),(305,GREEN,'K','WK'),(525,ORANGE,'V','WV')]:
            arrow(d,(360,491),(x+55,603),c)
            text(d,(x+55,561),w,24,c,True,'mm')
            vector(d,x,669,c,l)
        text(d,(360,920),'same input · different learned projections',24,MUTED,False,'mm')
    elif kind == 'scores':
        labels = ['The','cat','sat','here']
        text(d,(86,385),'Q',26,BLUE,True)
        text(d,(366,385),'Kᵀ',26,GREEN,True)
        for i,l in enumerate(labels):
            text(d,(184+i*125,461),l,23,GREEN,False,'mm')
            text(d,(69,533+i*90),l,22,BLUE,False,'mm')
        vals = [[1.0,.4,.1,.2],[.2,2.8,1.4,0.],[.5,1.,2.2,.9],[.4,.2,.8,1.6]]
        step = min(4,int(t*1.6))
        for row in range(4):
            for col in range(4):
                x,y = 131+col*125,492+row*90
                active = row == 1 and col < step
                card(d,(x,y,x+108,y+74),'#203f4d' if active else PANEL,GREEN if active else EDGE,12)
                if active: text(d,(x+54,y+37),f'{vals[row][col]:.1f}',28,WHITE,True,'mm')
        text(d,(360,933),'one query → one score for every key',25,MUTED,False,'mm')
    elif kind == 'softmax':
        # The exact row shown is [0.2, 2.8, 1.4, 0] / sqrt(4).
        raw = np.array([.2,2.8,1.4,0.])
        weights = np.exp(raw/2)/np.exp(raw/2).sum()
        text(d,(50,388),'SCORES ÷ √4',24,BLUE,True)
        for j,v in enumerate(raw/2):
            x=54+j*164
            card(d,(x,446,x+144,518))
            text(d,(x+72,482),f'{v:.1f}',32,BLUE,True,'mm')
        arrow(d,(360,538),(360,596),GREEN)
        text(d,(390,561),'softmax',24,GREEN)
        for j,v in enumerate(weights):
            x=70+j*164
            height = max(2,int(v*425*ease(t/1.5)))
            d.rounded_rectangle((x,879-height,x+110,879),8,fill=GREEN if j==1 else BLUE)
            text(d,(x+55,925),f'{v:.3f}',25,WHITE,False,'mm',True)
        text(d,(360,994),' + '.join(f'{v:.3f}' for v in weights)+' ≈ 1',22,MUTED,False,'mm')
    elif kind == 'mix':
        weights=np.exp(np.array([.2,2.8,1.4,0.])/2)
        weights/=weights.sum()
        vectors=np.array([(.2,.5,.8,.3),(.8,.3,.4,.7),(.5,.8,.2,.4),(.3,.4,.6,.5)])
        for j,(weight,values) in enumerate(zip([f'{v:.3f}' for v in weights],vectors)):
            x=52+j*164
            text(d,(x+55,410),weight,26,GREEN,True,'mm')
            vector(d,x,493,ORANGE,'V'+str(j+1),values)
            arrow(d,(x+55,665),(360,762),ORANGE)
        vector(d,305,824,ORANGE,'output',weights@vectors)
    elif kind == 'context':
        for j,(label,color) in enumerate([('Attention',BLUE),('Add residual connection',MUTED),('Feed-forward network',GREEN),('Add residual connection',MUTED)]):
            y=400+j*143
            card(d,(98,y,622,y+94),PANEL,color)
            text(d,(360,y+47),label,26,color,True,'mm')
            if j<3: arrow(d,(360,y+101),(360,y+131),MUTED)
        text(d,(360,1043),'Simplified block · normalization omitted',20,MUTED,False,'mm')
    elif kind == 'clutter':
        card(d,(36,404,684,943))
        for j in range(8):
            y=448+j*54
            for k in range(4):
                x=63+k*145+(j%2)*14
                length=90+((j*29+k*17)%40)
                card(d,(x,y,x+length,y+33),[BLUE,GREEN,ORANGE,'#8f87d7'][(j+k)%4],None,4)
        cursor=100+int(480*ease(t/3))
        d.line((cursor,420,cursor,916),fill=WHITE,width=3)
        text(d,(360,1000),'Too many clips. Too little clarity.',26,MUTED,False,'mm')
    elif kind == 'notebook':
        card(d,(40,404,680,973))
        text(d,(72,441),'NOTEBOOK.md',27,GREEN,True,mono=True)
        code=[('## the reel',WHITE),('',WHITE),('Every picture has a place.',WHITE),('',WHITE),('<video clip of the demo>',BLUE),('<caption: pinned to words>',GREEN),('',WHITE),('Your script. Your decisions.',MUTED)]
        for j,(s,c) in enumerate(code): text(d,(72,518+j*49),s,23,c,mono=True)
    elif kind == 'catalogue':
        for j,(label,status,col) in enumerate([('demo_take_01','verified',GREEN),('notebook','verified',GREEN),('wide_shot','unknown',ORANGE),('title_card','verified',GREEN)]):
            x,y=43+(j%2)*326,405+(j//2)*270
            card(d,(x,y,x+308,y+248))
            d.rounded_rectangle((x+18,y+18,x+290,y+139),12,fill='#22364b')
            if j==0:
                for k in range(4): d.rounded_rectangle((x+35,y+35+k*21,x+230-k*22,y+46+k*21),3,fill=BLUE)
            elif j==1:
                for k in range(4): d.line((x+40,y+42+k*22,x+236,y+42+k*22),fill=MUTED,width=3)
            elif j==2: d.polygon([(x+30,y+118),(x+113,y+38),(x+166,y+106),(x+224,y+51),(x+274,y+118)],fill=BLUE)
            else: text(d,(x+154,y+78),'REAL',40,WHITE,True,'mm')
            text(d,(x+20,y+159),label,22,WHITE,True)
            text(d,(x+20,y+202),status.upper(),20,col,True)
        text(d,(360,1004),'Unknown facts stay visible.',27,MUTED,False,'mm')
    elif kind == 'anchor':
        stretch=ease((t-2.8)/2)
        text(d,(52,392),'NARRATION',22,MUTED,True)
        xpos=[60,195,310+int(100*stretch),460+int(130*stretch)]
        for x,l in zip(xpos,['feel','the','pressure','rise']):
            card(d,(x,454,x+(132 if l=='pressure' else 98),527), '#1c3741' if l=='pressure' else PANEL,GREEN if l=='pressure' else EDGE,10)
            text(d,(x+8,490),l,21,GREEN if l=='pressure' else WHITE,False,'lm')
        text(d,(52,616),'PICTURE / CAPTION',22,MUTED,True)
        snap=ease(t/1.5)
        cx=int(80+(xpos[2]-80)*snap)
        card(d,(cx,685,cx+212,773),'#254b40',GREEN,12)
        text(d,(cx+106,729),'pressure',28,GREEN,True,'mm')
        if t>1:
            d.line((xpos[2]+60,532,cx+60,680),fill=GREEN,width=3)
        text(d,(360,896),'original take' if t<2.8 else 'longer re-recording',28,WHITE,True,'mm')
        text(d,(360,960),'same word · updated timing',26,MUTED,False,'mm')
    elif kind == 'compile':
        card(d,(46,397,674,490))
        text(d,(360,443),'File  →  Import  →  XML',29,WHITE,True,'mm')
        arrow(d,(360,513),(360,574),GREEN)
        card(d,(40,601,680,992))
        for j,(label,col) in enumerate([('titles',GREEN),('pictures',BLUE),('narration',ORANGE)]):
            y=654+j*94
            text(d,(59,y),label,20,MUTED)
            for k in range(3):
                if t > .5+k*.35:
                    card(d,(195+k*151,y-5,331+k*151,y+47),col,None,6)
        text(d,(360,1040),'Illustrated timeline · not a Final Cut capture',19,MUTED,False,'mm')
    elif kind == 'refuse':
        card(d,(55,443,665,888),PANEL,ORANGE)
        d.ellipse((310,493,410,593),outline=ORANGE,width=4)
        text(d,(360,542),'!',64,ORANGE,True,'mm')
        text(d,(360,672),'Cannot represent this edit',30,WHITE,True,'mm')
        lines(d,(101,739),'Review the unsupported choice before compiling.',26,MUTED,520)
    elif kind == 'end':
        text(d,(360,526),'REAL',118,WHITE,True,'mm')
        text(d,(360,655),'An editable answer.',34,GREEN,False,'mm')
        text(d,(360,791),'github.com/This-Goober/REAL',25,MUTED,False,'mm')
        text(d,(360,881),'Independent ground-truth reference',23,MUTED,False,'mm')

    # Caption region below all artwork; supplied as a separate PNG overlay.
    d.line((48,1085,672,1085),fill=EDGE,width=2)
    text(d,(48,1218),'REFERENCE / 30s',18,MUTED)
    text(d,(672,1218),'MATH' if is_math else 'UI ILLUSTRATION',18,MUTED,anchor='ra')
    return im


def caption_image(label):
    im=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
    size=32
    while d.textlength(label,font=font(size,True))>630: size-=1
    text(d,(360,1142),label,size,WHITE,True,'mm')
    return im


def encode_frames(path, frames, lossless=False):
    cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}',
         '-r',str(FPS),'-i','-','-an','-c:v','libx264','-threads','2','-preset','ultrafast',
         '-crf','0' if lossless else '17','-pix_fmt','yuv444p' if lossless else 'yuv420p',
         '-movflags','+faststart',str(path)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for im in frames: p.stdin.write(im.tobytes())
    finally: p.stdin.close()
    if p.wait(): raise RuntimeError(f'Encoding failed: {path}')


def narration(scenes, out):
    """Use the neural narrator by default; never silently fall back to eSpeak."""
    from elevenlabs_narration import synthesize
    synthesize(scenes, out)


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def build(project, resume=False):
    scenes=PROJECTS[project]
    assert sum(s[0] for s in scenes)==30
    out=ROOT/project
    for name in ['media/Videos','media/Images','previews']:
        (out/name).mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT.parent/'projects'/project/'NOTEBOOK.md',out/'SOURCE-NOTEBOOK.md')
    events=[]; catalog=[]; shots=[]; cursor=0; thumbs=[]
    notebook=['---',f'reel: {project} independent reference','target: 30s','aspect: 9:16','---','',
              'Shortened reference adaptation. Exact timing is in EDIT-DECISIONS.csv.',
              'Narration is a supplied synthetic WAV; it must not be re-estimated.','']
    for i,s in enumerate(scenes,1):
        dur,kind,title,spoken,caption=s
        count=dur*FPS; aid=f'clip{i:02d}'; cid=f'img{i:02d}'
        print(f'{project}: {aid} {kind} ({count} frames)',flush=True)
        clip=out/'media/Videos'/f'{aid}.mp4'
        valid=False
        if resume and clip.exists():
            p=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
                'stream=nb_frames','-of','csv=p=0',str(clip)],capture_output=True,text=True)
            valid=p.returncode==0 and p.stdout.strip()==str(count)
        if not valid:
            if kind in ('scores','softmax','clutter','anchor','compile'):
                frames=(artwork(project,s,f,count) for f in range(count))
            else:
                still=artwork(project,s,0,count)
                frames=(still for _ in range(count))
            encode_frames(clip,frames,lossless=True)
        overlay=caption_image(caption)
        overlay.save(out/'media/Images'/f'{cid}.png')
        still=artwork(project,s,count//2,count)
        still.save(out/'previews'/f'{aid}.png')
        still.paste(overlay,(0,0),overlay)
        thumbs.append(still.resize((216,384)))
        events.append({'kind':'video','asset':aid,'f0':cursor,'f1':cursor+count,'z':0,'src_in':0,'beat':f'B{i}'})
        # Delay the editable caption by 12 frames; remove it 6 frames before the cut.
        events.append({'kind':'image','asset':cid,'f0':cursor+12,'f1':cursor+count-6,'z':1,'beat':f'B{i}',
                       'text':caption,'alpha':True,'fit':'fit'})
        catalog += [
          {'id':aid,'f':f'Videos/{aid}.mp4','k':'video','dur':dur,'w':W,'h':H,'fps':FPS,'rotation':0,
           'exists':True,'role':title,'shows':f'Code-rendered {kind} animation','tags':[aid,kind],'use':f'B{i} primary'},
          {'id':cid,'f':f'Images/{cid}.png','k':'image','dur':None,'w':W,'h':H,'fps':None,'rotation':0,
           'exists':True,'role':f'caption: {caption}','shows':caption,'tags':[cid],'use':f'B{i} transparent caption'}]
        shots.append({'scene':i,'name':kind,'start_frame':cursor,'end_frame':cursor+count,'narration':spoken,'caption':caption})
        notebook += [f'## {kind}','',f'<{spoken}>',f'<video clip of {title} #{aid}>',
                     f'<show image of caption {caption} #{cid}>','']
        cursor+=count
    (out/'NOTEBOOK.md').write_text('\n'.join(notebook))
    dump(out/'truth.json',{'fps':FPS,'w':W,'h':H,'total_f':TOTAL,'events':events,
        'audio':{'file':'narration.wav','start_frame':0,'gain_db':0},
        'provenance':'Authored independently of REAL, using generate.py PROJECTS; frame ranges are half-open.'})
    dump(out/'shots.json',shots)
    dump(out/'asset-catalog.json',{'project':project,'root':'media','generated':'independent reference generator',
        'script_beats':[s[1] for s in scenes],'assets':catalog})
    (out/'EDIT-DECISIONS.csv').write_text('kind,asset,start_frame,end_frame,source_in,z\n'+
        ''.join(f"{e['kind']},{e['asset']},{e['f0']},{e['f1']},{e.get('src_in',0)},{e['z']}\n" for e in events))
    sheet=Image.new('RGB',(216*4,424*2),BG)
    sd=ImageDraw.Draw(sheet)
    for i,thumb in enumerate(thumbs):
        x,y=i%4*216,i//4*424
        sheet.paste(thumb,(x,y))
        text(sd,(x+8,y+391),f'{shots[i]["start_frame"]/FPS:04.1f}s / {scenes[i][1]}',16,WHITE)
    sheet.save(out/'contact-sheet.jpg',quality=92)
    narration(scenes,out)
    # Assemble independently from decoded source media, not by re-running artwork.
    subprocess.run(['python3',str(ROOT/'render.py'),str(out/'truth.json'),str(out/'reference.mp4')],check=True)
    paths=[p for p in out.rglob('*') if p.is_file() and p.name not in ('SHA256SUMS','verification.json')]
    (out/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.relative_to(out)}\n' for p in sorted(paths)))
    print(f'Finished {out}/reference.mp4',flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--project',choices=PROJECTS)
    ap.add_argument('--resume',action='store_true',help='Reuse complete source clips from an interrupted run of the same artwork code')
    args=ap.parse_args()
    for project in ([args.project] if args.project else PROJECTS): build(project,args.resume)
