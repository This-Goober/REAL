"""Shared print-scale drawing primitives for REAL's vector figures."""
from pathlib import Path
import math
import subprocess
import reportlab
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

HERE=Path(__file__).resolve().parent
PAPER_FIGURES={'architecture','catalogue-path','placement-trace'}
def dest(name):return HERE.parent if name in PAPER_FIGURES else HERE
INK=HexColor('#18232d');MUTED=HexColor('#54616b');RULE=HexColor('#bcc5cb')
BLUE=HexColor('#0072b2');TEAL=HexColor('#007d65');ORANGE=HexColor('#c45318')
PALE=HexColor('#f1f4f5');WHITE=HexColor('#ffffff')

def setup():
 f=Path(reportlab.__file__).resolve().parent/'fonts'
 for name,file in [('Sans','Vera.ttf'),('Bold','VeraBd.ttf'),('Italic','VeraIt.ttf')]:
  pdfmetrics.registerFont(TTFont(name,str(f/file)))

def canvas(name,h):
 setup();c=Canvas(str(dest(name)/(name+'.pdf')),pagesize=(500,h),invariant=1,pageCompression=1,pdfVersion=(1,4),initialFontName='Sans')
 c.setTitle('REAL: '+name.replace('-',' '));return c

def text(c,x,y,s,size=8.5,bold=False,color=INK,align='left'):
 size=max(size,8.5)  # At manuscript width, labels remain at least 7.7 pt.
 c.setFillColor(color);c.setFont('Bold' if bold else 'Sans',size)
 if align=='center':c.drawCentredString(x,y,s)
 elif align=='right':c.drawRightString(x,y,s)
 else:c.drawString(x,y,s)

def wrap(c,x,y,s,width,size=8.5,leading=12,color=INK,bold=False):
 size=max(size,8.5)
 font='Bold' if bold else 'Sans';lines=[];line=''
 for word in s.split():
  trial=(line+' '+word).strip()
  if pdfmetrics.stringWidth(trial,font,size)>width and line:lines.append(line);line=word
  else:line=trial
 if line:lines.append(line)
 for i,line in enumerate(lines):text(c,x,y-i*leading,line,size,bold,color)
 return y-len(lines)*leading

def line(c,x1,y1,x2,y2,color=RULE,width=.6,dash=None):
 c.setStrokeColor(color);c.setLineWidth(width);c.setDash(dash or [])
 c.line(x1,y1,x2,y2);c.setDash()

def rect(c,x,y,w,h,fill=WHITE,stroke=RULE,width=.6):
 c.setFillColor(fill);c.setStrokeColor(stroke);c.setLineWidth(width);c.rect(x,y,w,h,fill=1,stroke=1)

def arrow(c,x1,y1,x2,y2,color=INK,width=.8,head=3.6,dash=None):
 line(c,x1,y1,x2,y2,color,width,dash)
 a=math.atan2(y2-y1,x2-x1);p=c.beginPath();p.moveTo(x2,y2)
 for sign in (-1,1):p.lineTo(x2-head*math.cos(a)+sign*head*.5*math.sin(a),y2-head*math.sin(a)-sign*head*.5*math.cos(a))
 p.close();c.setFillColor(color);c.drawPath(p,fill=1,stroke=0)

def panel(c,label,title,x,y):
 text(c,x,y,label,10,True);text(c,x+21,y,title,10,True)

def finish(c,name):
 c.save();subprocess.run(['pdftoppm','-singlefile','-r','220','-png',str(dest(name)/(name+'.pdf')),str(dest(name)/name)],check=True,capture_output=True)
