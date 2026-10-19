"""REAL architecture: artifacts, review points and the measured-clock handoff."""
from figure_style import *

def document(c,x,y,w,h,title,rows,color=INK):
 p=c.beginPath();p.moveTo(x,y);p.lineTo(x+w,y);p.lineTo(x+w,y+h-10);p.lineTo(x+w-10,y+h);p.lineTo(x,y+h);p.close()
 c.setStrokeColor(RULE);c.setFillColor(WHITE);c.setLineWidth(.7);c.drawPath(p,fill=1,stroke=1)
 line(c,x+w-10,y+h,x+w-10,y+h-10);line(c,x+w-10,y+h-10,x+w,y+h-10)
 text(c,x+8,y+h-20,title,9,True,color);line(c,x+8,y+h-27,x+w-8,y+h-27)
 for i,row in enumerate(rows):text(c,x+8,y+h-43-i*13,row,7.7,color=MUTED)

def main():
 c=canvas('architecture',235)
 text(c,10,220,'CREATOR',8,True,TEAL)
 line(c,74,223,489,223,TEAL,1)
 stages=[('1','Brainstorm','Intent','Notebook',['narration','visual requests','constraints']),
 ('2','Catalogue','Evidence','Catalogue',['probed facts','observations','suggested use']),
 ('3','Storyboard','Decisions','reel.json',['asset + source','word anchor','creator override']),
 ('4','Compile','Finishing','FCPXML',['clips + titles','media references','frame boundaries'])]
 xs=[10,137,264,391]
 for i,(n,name,action,artifact,fields) in enumerate(stages):
  x=xs[i];ctr=x+49.5
  arrow(c,ctr,219,ctr,200,TEAL,.8)
  text(c,ctr,188,action,8,True,TEAL,'center')
  text(c,x,168,n,8,True,MUTED);text(c,x+13,168,name,10,True)
  document(c,x,66,99,91,artifact,fields,TEAL if i==2 else INK)
  if i<3:arrow(c,x+102,111,x+124,111,INK,1)
 for x,label in zip(xs,['Interpret brief','Probe + describe','Bind + place','Validate + export']):
  text(c,x+49.5,52,label,7.8,False,MUTED,'center')
 # Feedback is explicit and local to the authoritative storyboard.
 line(c,180,22,250,22,BLUE,1)
 arrow(c,250,22,250,108,BLUE,1)
 rect(c,10,9,170,26,WHITE,BLUE,.8)
 text(c,95,19,'Recorded take: word timings',8,False,BLUE,'center')
 text(c,328,25,'Re-time placements',8,True,BLUE)
 text(c,328,12,'Keep confirmed choices',8,color=MUTED)
 finish(c,'architecture')

if __name__=='__main__':main()
