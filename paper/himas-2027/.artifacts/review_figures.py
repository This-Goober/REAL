"""Evidence-led print figures. Saved artifacts are the sole numerical source."""
import argparse,hashlib,io,json,shutil,subprocess
from pathlib import Path
from fractions import Fraction
import xml.etree.ElementTree as ET
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageDraw
from figure_style import *

ROOT=HERE.parents[2];DATA=HERE/'figure-data';SOURCES={}

# Presentation-only face redactions on the frozen 128x224 proxy samples.
# Redact raster pixels before embedding so the PDF contains no recoverable face
# beneath a vector cover. Originals and their provenance stay unchanged internally.
FACE_REDACTIONS={1:[(31,104,91,195)],2:[(105,103,128,165)],
                 3:[(120,103,128,165)],4:[],5:[(105,103,128,165)]}

def anonymous_sample(index):
 with Image.open(DATA/f'paganini-sample-{index}.jpg') as original:
  image=original.convert('RGB')
 draw=ImageDraw.Draw(image)
 for box in FACE_REDACTIONS[index]:draw.rectangle(box,fill='#54616b')
 stream=io.BytesIO();image.save(stream,format='PNG');stream.seek(0)
 return ImageReader(stream)

def source(p):
 SOURCES[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest();return p

def read(p):return json.loads(source(p).read_text())
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')

def prepare(refresh_from=None):
 DATA.mkdir(exist_ok=True)
 # Regeneration uses the frozen paper inputs even if a newer production project
 # is present. Replacing those inputs is a separate, explicit capture operation.
 if refresh_from is not None:
  p=Path(refresh_from).resolve()
  if not p.is_relative_to(ROOT):raise ValueError('refresh project must be inside the repository')
  cat=read(p/'asset-catalog.json');a=next(x for x in cat['assets'] if x['id']=='A02')
  bindings=read(p/'bindings.json');b=next(x for x in bindings['bindings'].values() if x['cell']=='C2' and x['type']=='video')
  before=read(p/'reel.json');after=read(p/'review-claude/reel.json')
  flat=lambda r:{l['id']:l for beat in r['beats'] for l in beat['layers']}
  old,new=flat(before),flat(after)
  changes=[{'id':k,'kind':old[k]['kind'],'before':[round(old[k][t]*30) for t in ('t0','t1')],
            'after':[round(new[k][t]*30) for t in ('t0','t1')], 'text':old[k].get('content',old[k].get('text','')),
            'anchor_before':old[k].get('anchor_text'),'anchor_after':new[k].get('anchor_text')}
           for k in old if old[k]['t0']!=new[k]['t0'] or old[k]['t1']!=new[k]['t1']]
  assert len(changes)==8
  assert all(old[k]==new[k] for k in old if old[k]['kind']=='video')
  x={'asset':{k:a[k] for k in ('id','role','shows','use','dur','w','h','fps','temporal','source_window')},
     'binding':b,'changes':changes,'fps':30,'total_s':before['clock']['total_s'],
     'beats':[{'id':z['id'],'t0':z['t0'],'t1':z['t1'],'name':z['name']} for z in before['beats']],
     'status':'Claude-proposed revisions; not accepted by a participant or creator'}
  write(DATA/'paganini.json',x)
  movie=source(p/'takes/P-src-02.mov')
  for i,t in enumerate([a['temporal']['sampled_at'][j] for j in (0,3,7,11,15)]):
   out=DATA/f'paganini-sample-{i+1}.jpg'
   subprocess.run(['ffmpeg','-v','error','-y','-ss',str(t),'-i',str(movie),'-frames:v','1','-q:v','2',str(out)],check=True)
   SOURCES[str(out.relative_to(ROOT))]=hashlib.sha256(out.read_bytes()).hexdigest()
 if refresh_from is None:
  provenance=json.loads((DATA/'provenance.json').read_text())
  for image in sorted(DATA.glob('paganini-sample-*.jpg')):
   expected=provenance[str(image.relative_to(ROOT))]
   if hashlib.sha256(image.read_bytes()).hexdigest()!=expected:
    raise ValueError('frozen frame hash mismatch: '+image.name)
 return read(DATA/'placement.json'),read(DATA/'paganini.json')

def catalogue(d):
 c=canvas('catalogue-path',365)
 panel(c,'a','Sampled visual evidence',10,349)
 text(c,489,349,'P-src-02.mov · 5 of 16 frames',8,color=MUTED,align='right')
 samples=[d['asset']['temporal']['sampled_at'][j] for j in (0,3,7,11,15)]
 for i,t in enumerate(samples):
  x=10+i*99
  c.drawImage(anonymous_sample(i+1),x,208,width=84,height=126,preserveAspectRatio=True,anchor='c')
  text(c,x+42,195,f'{t:.2f} s',8,False,MUTED,'center')
 line(c,10,184,490,184)
 panel(c,'b','Catalogue entry',10,166)
 panel(c,'c','Notebook / asset binding',267,166)
 text(c,10,148,'PROBED',7.2,True,MUTED)
 text(c,69,148,'A02 · 16.53 s · 15 fps · 128×224',8.2)
 text(c,10,130,'OBSERVED',7.2,True,BLUE)
 y=wrap(c,10,114,'“Speaker brings violin under chin; left hand is visible along the fingerboard, then moves closer to the violin body.”',229,8.4,12)
 text(c,10,y-4,'SUGGESTED',7.2,True,TEAL)
 text(c,83,y-4,'Beat 2: interval spacing',8.2)
 # A quotation excerpt and exact logged signal contributions.
 wrap(c,267,147,'<video clip of the close-up of the left hand ... #passage-2>',221,8.2,11.5)
 labels=[('Exact tag',6),('Binding text',4),('Media type',2),('Observed content',1.2),('Role',.4)]
 for i,(name,value) in enumerate(labels):
  y=106-i*13
  text(c,267,y,name,7.8)
  rect(c,366,y-1,75*value/6,5,BLUE,BLUE,0)
  text(c,452,y,f'+{value:.1f}',7.8,color=MUTED)
 arrow(c,245,108,259,108,MUTED)
 line(c,10,26,490,26)
 text(c,10,10,'Script-supplied window: original 29.0–45.5 s; asset A02; beat B2',8.4,True)
 finish(c,'catalogue-path')

def trace(d):
 c=canvas('placement-trace',264)
 panel(c,'a','One identity across representations',10,248)
 cols=[(10,145,'NOTEBOOK'),(180,140,'REEL'),(350,140,'FCPXML')]
 for x,w,title in cols:
  text(c,x,228,title,7.5,True,MUTED);line(c,x,220,x+w,220)
 wrap(c,10,206,'<show image of a chart about the amber ~0.8s #img07>',145,8.4,12)
 text(c,180,206,'id: B4.L3',8.4,True,TEAL)
 text(c,180,192,'asset: img07',8.4);text(c,180,178,'duration: 0.8 s',8.4)
 text(c,180,164,'anchor: nickel to velvet',8.2,color=TEAL)
 text(c,350,206,'<video name="B4.L3 ..."',8)
 text(c,350,192,'  offset="67/30s"',8)
 text(c,350,178,'  duration="4/5s"',8)
 text(c,350,164,'  lane="2">',8)
 arrow(c,151,186,173,186);arrow(c,325,186,343,186)
 panel(c,'b','A local correction on the frame grid',10,137)
 x0,x1=104,480;f0,f1=550,650
 X=lambda f:x0+(f-f0)/(f1-f0)*(x1-x0)
 for f in range(550,651,10):
  line(c,X(f),46,X(f),114,RULE,.4)
  text(c,X(f),32,str(f),7.8,color=MUTED,align='center')
 text(c,10,94,'Before',8.5);text(c,10,65,'After',8.5,True,TEAL)
 for y,start,color in [(90,607,MUTED),(61,562,TEAL)]:
  rect(c,X(start),y,X(start+24)-X(start),13,color,color,0)
  text(c,X(start)+4,y+3,'img07',7.8,color=WHITE)
  text(c,X(start+24)+5,y+3,f'{start}–{start+24}',7.7,color=color)
 arrow(c,X(607),86,X(562),78,TEAL,.8)
 text(c,10,9,'B4.L3: nickel to velvet',8.3,True,TEAL)
 text(c,490,9,'24 frames retained · 15 other placements unchanged',8.3,align='right')
 finish(c,'placement-trace')

def scenario(d):
 c=canvas('creator-scenario',336)
 panel(c,'a','Five source excerpts remain fixed',10,320)
 x0,x1=100,488;X=lambda s:x0+s/67.4*(x1-x0)
 shades=[HexColor(x) for x in ('#dce4e8','#eef1f3','#dce4e8','#eef1f3','#dce4e8')]
 for b,fill in zip(d['beats'],shades):
  x=X(b['t0']);w=X(b['t1'])-x
  rect(c,x,277,w,26,fill,WHITE,.6);text(c,x+w/2,286,b['id'],9,True,INK,'center')
 text(c,10,287,'Base clips',8.5,True)
 panel(c,'b','Eight proposed overlay re-anchors',10,252)
 rect(c,306,251,10,4,MUTED,MUTED,0);text(c,321,249,'Before',7.5)
 rect(c,373,251,10,4,TEAL,TEAL,0);text(c,388,249,'Proposed',7.5)
 for b in d['beats'][1:]:line(c,X(b['t0']),39,X(b['t0']),236,RULE,.45,[2,2])
 for i,z in enumerate(d['changes']):
  y=226-i*23
  text(c,10,y-1,z['id'],8.5,True)
  text(c,48,y-1,'still' if z['kind']=='image' else 'caption',7.5,color=MUTED)
  a,b=z['before'];q,r=z['after']
  rect(c,X(a/30),y+2,X(b/30)-X(a/30),5,MUTED,MUTED,0)
  rect(c,X(q/30),y-7,X(r/30)-X(q/30),5,TEAL,TEAL,0)
  if q!=a:arrow(c,X(a/30),y,X(q/30),y,TEAL,.65,2.8)
 line(c,x0,31,x1,31,INK,.7)
 for s in range(0,61,10):
  line(c,X(s),31,X(s),27,INK);text(c,X(s),16,str(s),8,align='center')
 text(c,490,16,'s',8,align='right');text(c,10,16,'Timeline',8,color=MUTED)
 finish(c,'creator-scenario')

def tutorial():
 folder=ROOT/'experiments/E05-tier2-codex-reproduction/results'
 ds={m:read(folder/f'transformer-math-30s-mode-{m}.json') for m in ('A','B')}
 c=canvas('tutorial-results',214)
 panel(c,'a','Base-picture coverage',10,196)
 panel(c,'b','Mean absolute boundary error',255,196)
 text(c,10,180,'900 reference frames',8,color=MUTED)
 x0,x1=51,227
 for row,m in enumerate(('A','B')):
  y=139-row*44;d=ds[m];good=round(d['base_frame_acc']*d['frames']);fraction=good/900
  text(c,10,y+5,m,9,True)
  col=ORANGE if m=='A' else BLUE
  rect(c,x0,y,(x1-x0)*fraction,17,col,col,0)
  if fraction<1:
   rect(c,x0+(x1-x0)*fraction,y,(x1-x0)*(1-fraction),17,WHITE,ORANGE,.7)
   for xx in range(int(x0+(x1-x0)*fraction)+2,int(x1)-3,5):line(c,xx,y+1,xx+4,y+16,ORANGE,.5)
  text(c,x0,y-13,f'{good}/900 matching',8,color=col)
  if fraction<1:text(c,x1,y+25,'209 uncovered',7.5,color=ORANGE,align='right')
 line(c,x0,62,x1,62,INK)
 for pct in (0,25,50,75,100):
  x=x0+(x1-x0)*pct/100;line(c,x,62,x,58,INK);text(c,x,45,str(pct),7.7,align='center')
 text(c,x1,31,'Coverage (%)',8,color=MUTED,align='right')
 # Right: paired values, common scale, exact numeric labels.
 left,right=340,484;X=lambda v:left+v/30*(right-left)
 for tick in (0,10,20,30):
  line(c,X(tick),60,X(tick),161,RULE,.45)
  text(c,X(tick),45,str(tick),7.7,align='center')
 metrics=[('Shot start','shots','in_err_mean_f'),('Shot end','shots','out_err_mean_f'),('Caption start','captions','in_err_mean_f'),('Caption end','captions','out_err_mean_f')]
 for i,(name,key,f) in enumerate(metrics):
  y=152-i*28;va=ds['A'][key][f];vb=ds['B'][key][f]
  text(c,255,y-3,name,8)
  line(c,X(vb),y,X(va),y,RULE,1.2)
  c.setFillColor(ORANGE);c.circle(X(va),y,4 if abs(va-vb)<.1 else 3,fill=1,stroke=0)
  rect(c,X(vb)-2.5,y-2.5,5,5,BLUE,BLUE,0)
  if abs(va-vb)<.1:text(c,X(va),y+7,f'{va:.1f}',7.3,align='center')
  else:
   text(c,X(va),y+7,f'{va:.1f}',7.3,color=ORANGE,align='center')
   text(c,X(vb),y+7,f'{vb:.1f}',7.3,color=BLUE,align='center')
 text(c,right,31,'Error (frames at 30 fps)',8,color=MUTED,align='right')
 c.setFillColor(ORANGE);c.circle(14,13,3,fill=1,stroke=0);text(c,23,10,'A: blank pauses',8)
 rect(c,154,10,5,5,BLUE,BLUE,0);text(c,166,10,'B: hold pauses',8)
 finish(c,'tutorial-results')

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--refresh-from',type=Path,
                     help='explicitly replace frozen inputs from a repository-local historical project with review-claude/reel.json')
 args=parser.parse_args()
 placement,paganini=prepare(args.refresh_from);catalogue(paganini);trace(placement);scenario(paganini);tutorial()
 p=DATA/'provenance.json';old=json.loads(p.read_text()) if p.exists() else {};write(p,{**old,**SOURCES})

if __name__=='__main__':main()
