#!/usr/bin/env python3
"""tracks.py — reel.json -> REEL-TRACKS.html, the thing the creator looks at.

    python3 tracks.py tracks reel.json REEL-TRACKS.html [--clock clock.json]

One self-contained page, no server, no CDN, thumbnails embedded as data URIs:

  * a horizontal multi-lane track view — one lane per role (video / image /
    text / narration / audio) with blocks at real time and a time ruler, so
    layering and pacing are visible at a glance;
  * a scrub/preview pane that composites the frame at the playhead in the
    reel's real aspect ratio, stacked in z-order, with grey labelled cards
    where an asset still has to be built, and the narration for that moment;
  * click any block to see where it came from — the notebook component, the
    bound file, WHY that file, the runners-up, the confidence, the anchor word;
  * every low-confidence and every stub item marked on sight;
  * and the correction surface built into the page: click a candidate chip,
    pick from the dropdown of everything unbound, or type a note, then hit
    "copy revision block" and paste it back. The page IS the interview.

Nothing is stored in the browser; the export button exists because of that.
Copy the block before closing the tab.

Stdlib + PIL only (PIL only for making thumbnails; a missing file just renders
as a card).
"""

import argparse
import base64
import io
import json
import os
import subprocess
import sys
import tempfile

THUMB_W = 260


def thumb_image(path):
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        im = Image.open(path)
        im.load()
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        w, h = im.size
        im = im.resize((THUMB_W, max(1, int(h * THUMB_W / w))))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=72)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def thumb_video(path):
    exe = None
    for cand in ("ffmpeg", "/usr/bin/ffmpeg", "/opt/homebrew/bin/ffmpeg"):
        if os.path.exists(cand) or cand == "ffmpeg":
            exe = cand
            break
    tmp = os.path.join(tempfile.gettempdir(), "reel-thumb.jpg")
    try:
        subprocess.run([exe, "-y", "-loglevel", "error", "-ss", "1", "-i", path,
                        "-frames:v", "1", "-vf", "scale=%d:-1" % THUMB_W, tmp],
                       check=True, timeout=25,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return thumb_image(tmp)
    except Exception:
        return None


def collect_thumbs(reel):
    out, misses = {}, []
    for a in reel.get("assets", []):
        p = a.get("file") or ""
        if not p or not os.path.exists(p):
            misses.append(a["id"])
            continue
        t = thumb_image(p) if a.get("kind") == "image" else (
            thumb_video(p) if a.get("kind") == "video" else None)
        if t:
            out[a["id"]] = t
    for b in reel.get("beats", []):
        for L in b.get("layers", []):
            st = L.get("stub") or {}
            f = st.get("file")
            if f and os.path.exists(f):
                t = thumb_image(f)
                if t:
                    out["stub:" + L["id"]] = t
    return out, misses


def build(reel, out_path, clock=None):
    thumbs, misses = collect_thumbs(reel)
    words = []
    if clock:
        words = [{"i": w["i"], "s": w["start"], "e": w["end"], "w": w["w"]}
                 for w in clock.get("words", [])]
    payload = {"reel": reel, "thumbs": thumbs, "words": words,
               "thumb_misses": misses}
    html = TEMPLATE.replace("/*__PAYLOAD__*/null",
                            json.dumps(payload).replace("</", "<\\/"))
    with open(out_path, "w") as fh:
        fh.write(html)
    return len(thumbs), misses


TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>REEL TRACKS</title>
<style>
:root{--bg:#0d0f13;--pnl:#161a21;--pnl2:#1d222b;--ln:#2a3140;--tx:#e8ecf3;
 --tx2:#9aa5b6;--tx3:#68738a;--amber:#e8c06a;--green:#7fd39a;--red:#f0918a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);padding-bottom:88px;
 font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Helvetica,Arial,sans-serif}
.wrap{max-width:1400px;margin:0 auto;padding:26px 20px}
h1{font-size:23px;margin:0 0 4px;letter-spacing:-.02em}
.sub{color:var(--tx2);margin:0 0 16px;font-size:13px}
.badge{display:inline-block;font-size:10px;letter-spacing:.08em;text-transform:uppercase;
 padding:2px 7px;border-radius:99px;border:1px solid var(--ln);color:var(--tx2);margin-left:6px}
.badge.est{border-color:#c9a22766;color:var(--amber)}
.badge.meas{border-color:#4aa96c66;color:var(--green)}
.badge.unbound{border-color:#a33;color:var(--red);background:#2a1614}
.stats{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}
.stat{background:var(--pnl);border:1px solid var(--ln);border-radius:9px;padding:7px 12px;min-width:92px}
.stat b{display:block;font-size:17px}
.stat span{font-size:10px;color:var(--tx3);text-transform:uppercase;letter-spacing:.07em}
.cols{display:grid;grid-template-columns:340px 1fr;gap:16px;align-items:start}
.panel{background:var(--pnl);border:1px solid var(--ln);border-radius:12px;padding:14px 16px;margin-bottom:12px}
.panel h2{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--tx3);margin:0 0 9px}
.panel.warn{border-color:#4a3f22;background:#241f14}
.panel.warn a{color:var(--amber);cursor:pointer}
.frame{position:relative;width:100%;background:#000;border:1px solid #333a49;border-radius:10px;overflow:hidden}
.ly{position:absolute;inset:0;background-position:center;background-size:cover;background-repeat:no-repeat}
.ly.fit{background-size:contain;background-color:#08090c}
.ly.card{display:flex;align-items:center;justify-content:center;text-align:center;padding:14px;
 background:repeating-linear-gradient(45deg,#23262c,#23262c 8px,#1a1d22 8px,#1a1d22 16px)}
.ly.card span{font-size:11px;color:#c3cad6;line-height:1.4}
.ly.card b{color:var(--amber);display:block;font-size:10px;letter-spacing:.1em;margin-bottom:5px}
.ly.txt{display:flex;align-items:flex-end;justify-content:center;padding:0 12px 12%;
 background:linear-gradient(0deg,#000000cc 18%,#0000 55%)}
.ly.txt span{font-size:15px;font-weight:800;text-shadow:0 2px 10px #000;text-align:center}
.ly.txt.title{align-items:center;padding-bottom:0}
.ly.txt.title span{font-size:20px;letter-spacing:.02em}
.narr{margin:9px 0 0;font-size:13px;color:var(--tx2);min-height:42px}
.narr b{color:var(--tx);background:#25303f;border-radius:3px;padding:0 2px}
.scrub{display:flex;align-items:center;gap:8px;margin-top:9px}
.scrub input{flex:1}
.scrub button{background:var(--pnl2);border:1px solid var(--ln);color:var(--tx);
 border-radius:7px;padding:5px 11px;cursor:pointer;font:13px inherit}
.tc{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:var(--tx2);min-width:96px}
.tracks{position:relative;overflow-x:auto}
.beatstrip{position:relative;height:22px;margin-bottom:6px}
.beatstrip div{position:absolute;top:0;bottom:0;border-radius:4px;background:#232a35;
 border:1px solid var(--ln);font-size:10px;color:var(--tx2);padding:2px 6px;overflow:hidden;white-space:nowrap;cursor:pointer}
.lanerow{display:grid;grid-template-columns:74px 1fr;align-items:center;gap:8px;margin-bottom:5px}
.lanelabel{font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--tx3);text-align:right}
.lane{position:relative;height:30px;background:#11151b;border-radius:6px}
.blk{position:absolute;top:3px;bottom:3px;border-radius:4px;background:#37506b;
 border:1px solid #4a6690;overflow:hidden;cursor:pointer;padding:2px 5px;font-size:10px;
 color:#dbe4f2;white-space:nowrap}
.blk:hover{filter:brightness(1.25)}
.blk.sel{outline:2px solid #7fd39a;outline-offset:-2px;z-index:5}
.blk.low{background:#5a4a1e;border-color:#8a7433}
.blk.stub{background:repeating-linear-gradient(45deg,#3a3f48,#3a3f48 5px,#2a2e35 5px,#2a2e35 10px);border-color:#6b7280}
.blk.creator{background:#1f4b31;border-color:#3d7a55}
.blk.text{background:#4a3a5e;border-color:#6b5484}
.blk.audio{background:#2f4a52;border-color:#44707c}
.blk.narr{background:#2b3a52;border-color:#43587a}
.blk img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.42}
.blk span{position:relative}
.ruler{position:relative;height:20px;border-top:1px solid var(--ln);margin:6px 0 0 82px}
.tk{position:absolute;top:0;border-left:1px solid var(--ln);height:5px}
.tk span{position:absolute;top:6px;left:-12px;font-size:9.5px;color:var(--tx3)}
.ph{position:absolute;top:0;bottom:0;width:2px;background:#7fd39a;pointer-events:none;z-index:9}
.det table{width:100%;border-collapse:collapse}
.det td{padding:3px 5px;font-size:12px;color:var(--tx2);border-bottom:1px solid #1e232c;vertical-align:top}
.det td.k{color:var(--tx3);width:96px;font-size:10.5px;text-transform:uppercase;letter-spacing:.06em}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.cand{display:flex;align-items:center;gap:6px;background:var(--pnl2);border:1.5px solid var(--ln);
 border-radius:8px;padding:4px 8px;cursor:pointer;color:var(--tx2);font:11px inherit}
.cand:hover{border-color:#4a5670;color:var(--tx)}
.cand.sel{border-color:var(--green);color:var(--green)}
.cand img{width:34px;height:22px;object-fit:cover;border-radius:3px}
select,input.note,input.spec{width:100%;background:#11151b;border:1px solid var(--ln);
 border-radius:7px;color:var(--tx);padding:6px 9px;font:12.5px inherit;margin-top:7px}
.who{font-size:9px;letter-spacing:.06em;text-transform:uppercase;padding:2px 6px;border-radius:4px}
.who.claude{background:#1d222b;color:#8894a8}
.who.creator{background:#17361f;color:var(--green)}
.who.low{background:#3a2f14;color:var(--amber)}
.who.stubb{background:#2b2f36;color:#c3cad6}
.flag{font-size:11.5px;color:var(--amber);margin:4px 0 0}
.q{font-size:12px;color:var(--tx2);margin:3px 0}
.bar{position:fixed;left:0;right:0;bottom:0;background:#11151bf2;border-top:1px solid var(--ln);
 backdrop-filter:blur(8px);padding:10px 20px;display:flex;align-items:center;gap:12px;z-index:99}
.bar b{font-size:13px}.bar span{font-size:12px;color:var(--tx3)}
.bar button{background:#2f6b45;border:0;color:#eafff2;font-size:13px;font-weight:600;
 padding:8px 15px;border-radius:8px;cursor:pointer}
.bar button.ghost{background:var(--pnl2);color:var(--tx2)}
#out{position:fixed;inset:auto 20px 70px 20px;max-height:42vh;overflow:auto;background:#0b0d11;
 border:1px solid var(--ln);border-radius:10px;padding:12px;display:none;z-index:100}
#out textarea{width:100%;height:170px;background:#0b0d11;border:0;color:var(--green);
 font:12.5px ui-monospace,Menlo,monospace;resize:vertical}
@media(max-width:980px){.cols{grid-template-columns:1fr}}
</style></head><body>
<div class="wrap">
<div id="head"></div>
<div class="cols">
  <div>
    <div class="panel">
      <h2>Preview at the playhead</h2>
      <div class="frame" id="frame"></div>
      <p class="narr" id="narr"></p>
      <div class="scrub">
        <button id="play">▶</button>
        <input type="range" id="seek" min="0" max="1000" value="0">
        <span class="tc" id="tc">0:00.00</span>
      </div>
    </div>
    <div class="panel det" id="det"><h2>Nothing selected</h2>
      <p class="q">Click any block in the tracks. Everything about it — which
      notebook component it came from, which file it bound to and why, what else
      could have gone there — shows up here, and every fix is one click.</p></div>
  </div>
  <div>
    <div class="panel"><h2>Tracks</h2><div class="tracks" id="tracks"></div></div>
    <div id="panels"></div>
  </div>
</div>
</div>
<div id="out"><textarea id="txt" readonly></textarea></div>
<div class="bar">
  <b id="cnt">0 notes</b>
  <span>click a candidate, pick from a dropdown, or type a note — then copy the
  block and paste it back</span>
  <div style="flex:1"></div>
  <button class="ghost" onclick="toggleOut()">show block</button>
  <button onclick="copyBlock()">copy revision block</button>
</div>
<script>
var PAYLOAD = /*__PAYLOAD__*/null;
var R = PAYLOAD.reel, TH = PAYLOAD.thumbs, WORDS = PAYLOAD.words || [];
var TOTAL = (R.clock && R.clock.total_s) || 1;
var pending = {}, playhead = 0, sel = null, playing = null;

function esc(s){ return String(s==null?"":s).replace(/[&<>"]/g, function(c){
  return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]; }); }
function tc(x){ var m=Math.floor(x/60), s=x-60*m; return m+":"+(s<10?"0":"")+s.toFixed(2); }
function assetById(id){ return (R.assets||[]).find(function(a){return a.id===id;}); }
function allItems(){ var o=[]; (R.beats||[]).forEach(function(b){
  (b.layers||[]).forEach(function(L){o.push({b:b,x:L,kind:L.kind,lane:L.kind==="text"?"text":L.kind});});
  (b.audio||[]).forEach(function(A){o.push({b:b,x:A,kind:A.kind,lane:A.kind==="narration"?"narration":"audio"});});
 }); return o; }

/* ---------------------------------------------------------------- header */
function header(){
  var c=R.clock||{}, unbound=(R.open&&R.open.unbound_layers||[]).length;
  var stubs=0, low=0, creator=0;
  allItems().forEach(function(it){
    if(it.x.stub) stubs++;
    if(it.x.confidence==="low" && it.x.asset) low++;
    if(it.x.chosen_by==="creator") creator++; });
  var unboundAll = (R.assets||[]).length===0;
  document.getElementById("head").innerHTML =
   '<h1>'+esc(R.reel.title)+'<span class="badge '+(c.mode==="measured"?"meas":"est")+'">'
   +esc(c.mode)+' clock</span>'+(unboundAll?'<span class="badge unbound">UNBOUND — no catalogue</span>':'')+'</h1>'
   +'<p class="sub">'+esc(c.note||"")+' · '+esc(c.rate_source||"")
   +' · '+R.reel.width+'×'+R.reel.height+' '+esc(R.reel.aspect)+' @'+R.reel.fps+'fps'
   +'. Production-close, not final — trim in the editor.</p>'
   +'<div class="stats">'
   +stat(tc(c.total_s||0),"runtime ("+esc(c.mode)+")")
   +stat((R.beats||[]).length,"beats")
   +stat(allItems().length,"layers")
   +stat(low,"low confidence")
   +stat(stubs,"to build")
   +stat(creator,"creator's own")
   +(c.target_s?stat(((c.total_s-c.target_s)>=0?"+":"")+(c.total_s-c.target_s).toFixed(1)+"s","vs "+c.target_s+"s target"):"")
   +'</div>';
}
function stat(a,b){ return '<div class="stat"><b>'+a+'</b><span>'+b+'</span></div>'; }

/* ---------------------------------------------------------------- tracks */
var LANES=["video","image","text","narration","audio"];
function tracks(){
  var host=document.getElementById("tracks"), h="";
  var strip="";
  (R.beats||[]).forEach(function(b){
    strip+='<div style="left:'+(b.t0/TOTAL*100)+'%;width:'+((b.t1-b.t0)/TOTAL*100)+'%" '
      +'onclick="seekTo('+b.t0+')" title="'+esc(b.name)+'">'+esc(b.id)+' '+esc(b.name)+'</div>';
  });
  h+='<div class="beatstrip">'+strip+'</div>';
  LANES.forEach(function(lane){
    var blocks="";
    allItems().forEach(function(it){
      var k = it.lane==="unknown" ? "image" : it.lane;
      if(k!==lane) return;
      var x=it.x, w=Math.max(0.25,(x.t1-x.t0)/TOTAL*100);
      var cls="blk "+(lane==="text"?"text":lane==="audio"?"audio":lane==="narration"?"narr":"");
      if(x.stub) cls+=" stub";
      else if(x.confidence==="low") cls+=" low";
      if(x.chosen_by==="creator") cls+=" creator";
      var th=TH[x.asset]||TH["stub:"+x.id];
      var label = x.content || (x.stub?"TO BUILD · "+(x.stub.file||"").split("/").pop():"")
        || (x.asset||"") || (x.text||x.note||"").slice(0,44) || "—";
      blocks+='<div class="'+cls+'" id="blk-'+x.id+'" style="left:'+(x.t0/TOTAL*100)+'%;width:'+w+'%" '
        +'onclick="select(\''+x.id+'\')" title="'+esc(x.id+" · "+(x.source_text||x.note||x.text||""))+'">'
        +(th?'<img src="'+th+'">':'')+'<span>'+esc(label)+'</span></div>';
    });
    h+='<div class="lanerow"><div class="lanelabel">'+lane+'</div>'
      +'<div class="lane" onclick="laneSeek(event,this)">'+blocks+'</div></div>';
  });
  var ticks="";
  var step = TOTAL>90?15:TOTAL>40?10:5;
  for(var x=0;x<=TOTAL;x+=step)
    ticks+='<div class="tk" style="left:'+(x/TOTAL*100)+'%"><span>'+Math.floor(x/60)+":"+("0"+Math.floor(x%60)).slice(-2)+'</span></div>';
  h+='<div class="ruler">'+ticks+'</div>';
  h+='<div class="ph" id="ph" style="left:0"></div>';
  host.innerHTML=h;
  host.style.position="relative";
  movePh();
}
function laneSeek(ev,el){
  if(ev.target!==el) return;
  var r=el.getBoundingClientRect();
  seekTo((ev.clientX-r.left)/r.width*TOTAL);
}
function movePh(){
  var lane=document.querySelector(".lane"); if(!lane) return;
  var host=document.getElementById("tracks"), ph=document.getElementById("ph");
  var lr=lane.getBoundingClientRect(), hr=host.getBoundingClientRect();
  ph.style.left=(lr.left-hr.left+host.scrollLeft+playhead/TOTAL*lr.width)+"px";
}

/* --------------------------------------------------------------- preview */
function activeAt(t){
  return allItems().filter(function(it){ return it.x.t0<=t && t<it.x.t1; });
}
function preview(){
  var f=document.getElementById("frame");
  f.style.aspectRatio=R.reel.width+" / "+R.reel.height;
  var vis=activeAt(playhead).filter(function(it){return it.lane!=="audio"&&it.lane!=="narration";});
  vis.sort(function(a,b){return (a.x.z||0)-(b.x.z||0);});
  var h="";
  vis.forEach(function(it){
    var x=it.x;
    if(x.kind==="text"){
      h+='<div class="ly txt '+(x.style==="title"?"title":"")+'"><span>'+esc(x.content||"")+'</span></div>';
      return;
    }
    var th=TH[x.asset]||TH["stub:"+x.id];
    if(th){ h+='<div class="ly '+(x.fit==="fit"?"fit":"")+'" style="background-image:url('+th+')"></div>'; return; }
    if(x.stub){
      h+='<div class="ly card"><span><b>TO BUILD</b>'+esc(x.stub.spec||"").slice(0,150)
        +'<br><i style="color:#8894a8">'+esc(x.stub.file||"")+'</i></span></div>'; return;
    }
    var a=assetById(x.asset);
    h+='<div class="ly card"><span><b>'+(a?esc(a.kind)+" · "+esc(x.asset):"NO ASSET")+'</b>'
      +esc(a?(a.catalog&&a.catalog.role||a.file):(x.source_text||""))+'</span></div>';
  });
  if(!vis.length) h='<div class="ly card"><span><b>BLANK</b>nothing on screen here — deliberate, or a defect</span></div>';
  f.innerHTML=h;

  var beat=(R.beats||[]).find(function(b){return b.t0<=playhead&&playhead<b.t1;})
        || (R.beats||[])[0];
  var n=document.getElementById("narr");
  if(!beat||!beat.narration){ n.innerHTML='<i style="color:#68738a">— no narration here —</i>'; }
  else{
    var toks=beat.narration.split(/\s+/), cur=-1;
    if(WORDS.length){
      for(var i=beat.w0;i<=beat.w1;i++){
        var w=WORDS[i]; if(w&&w.s<=playhead&&playhead<w.e){cur=i-beat.w0;break;}
      }
    } else {
      var frac=(playhead-beat.t0)/Math.max(0.001,beat.t1-beat.t0);
      cur=Math.floor(frac*toks.length);
    }
    n.innerHTML=toks.map(function(t,i){return i===cur?"<b>"+esc(t)+"</b>":esc(t);}).join(" ");
  }
  document.getElementById("tc").textContent=tc(playhead);
  document.getElementById("seek").value=Math.round(playhead/TOTAL*1000);
  movePh();
}
function seekTo(t){ playhead=Math.max(0,Math.min(TOTAL,t)); preview(); }

/* -------------------------------------------------------------- details */
function findItem(id){ return allItems().find(function(it){return it.x.id===id;}); }
function select(id){
  sel=id;
  document.querySelectorAll(".blk").forEach(function(e){e.classList.remove("sel");});
  var el=document.getElementById("blk-"+id); if(el) el.classList.add("sel");
  var it=findItem(id); if(!it) return;
  seekTo(it.x.t0+0.01);
  details(it);
}
function row(k,v){ return "<tr><td class='k'>"+k+"</td><td>"+v+"</td></tr>"; }
function details(it){
  var x=it.x, b=it.b, a=assetById(x.asset), h="";
  h+="<h2>"+esc(x.id)+" · "+esc(b.id)+" "+esc(b.name)+"</h2><table>";
  h+=row("what", esc(x.content||x.source_text||x.note||x.text||"—"));
  h+=row("from", "<code>"+esc(x.source_component||"—")+"</code> in cell "+esc(b.source&&b.source.cell||"—"));
  h+=row("time", tc(x.t0)+" → "+tc(x.t1)+"  ("+(x.t1-x.t0).toFixed(2)+"s)");
  h+=row("anchor", "word "+esc(x.anchor_word)+(x.offset_ms?(" "+(x.offset_ms>0?"+":"")+x.offset_ms+"ms"):"")
        +(x.snapped?' <span class="who low">snapped</span>':"")
        +(x.placement?' <span class="who claude">'+esc(x.placement)+'</span>':""));
  h+=row("chosen by", '<span class="who '+(x.chosen_by==="creator"?"creator":"claude")+'">'
        +esc(x.chosen_by||"claude")+'</span>'
        +(x.confidence?' <span class="who '+(x.confidence==="low"?"low":"claude")+'">'+esc(x.confidence)+'</span>':"")
        +(x.stub?' <span class="who stubb">to build</span>':""));
  if(a) h+=row("file","<code>"+esc(a.file)+"</code><br>"+esc(a.catalog&&a.catalog.role||"")
        +(a.dur_s?(" · "+a.dur_s+"s"):"")+(a.w?(" · "+a.w+"×"+a.h):""));
  if(x.stub) h+=row("stub","<code>"+esc(x.stub.file)+"</code><br>"+esc(x.stub.spec)
        +"<br><i>"+esc(x.stub.dur_s)+"s · "+esc(x.stub.w)+"×"+esc(x.stub.h)+" · "+esc(x.stub.status)+"</i>");
  if(x.why) h+=row("why", esc(x.why));
  h+="</table>";

  (b.flags||[]).filter(function(f){return f.layer===x.id;}).forEach(function(f){
    h+='<p class="flag">⚑ '+esc(f.code)+" — "+esc(f.msg)+"</p>"; });

  // every control below writes one revision line; the verbs match revise.py
  var slot = x.id.split(".").pop();                 // L2 / A1
  var verb = (it.lane==="audio"||it.lane==="narration") ? "audio " : "layer ";
  var pre = b.id+": ";

  if((x.candidates||[]).length){
    h+='<h2 style="margin-top:12px">Instead of this, use…</h2><div class="chips">';
    x.candidates.forEach(function(cid){
      var ca=assetById(cid), th=TH[cid];
      h+='<button class="cand" data-act="line" data-key="'+esc(x.id)+':asset" data-line="'
        +esc(pre+verb+slot+" = "+cid)+'">'
        +(th?'<img src="'+th+'">':'')+esc(cid)+" "+esc(ca?(ca.catalog.role||ca.file).slice(0,34):"")
        +((x.candidates_why&&x.candidates_why[cid])?'<i style="color:#68738a"> · '
          +esc(x.candidates_why[cid].slice(0,60))+'</i>':'')
        +'</button>';
    });
    h+="</div>";
  }
  var opts='<option value="">— or pick any other asset —</option>';
  (R.assets||[]).forEach(function(a2){
    var unused=((R.open&&R.open.unused_assets)||[]).indexOf(a2.id)>=0;
    opts+='<option value="'+esc(a2.id)+'">'+(unused?"• ":"")+esc(a2.id)+" ("+esc(a2.kind)+") "
      +esc((a2.catalog&&a2.catalog.role||a2.file).slice(0,46))+'</option>';
  });
  h+='<select data-act="value" data-key="'+esc(x.id)+':asset" data-prefix="'
    +esc(pre+verb+slot+" = ")+'">'+opts+'</select>';
  if(x.stub)
    h+='<input class="spec" data-act="value" data-key="'+esc(x.id)+':spec" data-prefix="'
      +esc(pre+"stub "+slot+" spec = ")+'" placeholder="what must be legible, and by when" value="'
      +esc(x.stub.spec||"")+'">';
  if(x.kind==="text"){
    var st=['title','caption','subtitle','lower-third','kicker','word'],so='';
    st.forEach(function(v){so+='<option value="'+v+'"'+(x.style===v?' selected':'')+'>'
      +v+(x.style===v&&x.style_by!=='creator'?' (suggested)':'')+'</option>';});
    h+='<h2 style="margin-top:12px">This text is a…</h2>'
      +'<select data-act="value" data-key="'+esc(x.id)+':style" data-prefix="'
      +esc(pre+slot+" style = ")+'">'+so+'</select>';
  }
  if(x.anchor_word!==undefined)
    h+='<input class="note" data-act="value" data-key="'+esc(x.id)+':anchorset" data-prefix="'
      +esc(pre+slot+" anchor = ")+'" placeholder="move the anchor: type the exact word'
      +(x.anchor_text?' (now: '+esc(x.anchor_text)+')':'')+'">';
  h+='<input class="note" data-act="value" data-key="'+esc(x.id)+':note" data-prefix="'
    +esc(pre+slot+" ")+'" placeholder="or say what is wrong about '+esc(x.id)+' in plain words">';
  h+='<div class="chips">'
    +'<button class="cand" data-act="line" data-key="'+esc(x.id)+':confirm" data-line="'
      +esc(pre+"confirm "+slot)+'">confirm this placement</button>'
    +'<button class="cand" data-act="line" data-key="'+esc(x.id)+':remove" data-line="'
      +esc(pre+"remove "+slot)+'">remove it</button>'
    +'<button class="cand" data-act="line" data-key="'+esc(x.id)+':stagger" data-line="'
      +esc(pre+"stagger "+slot)+'">keep it staggered</button>'
    +(x.anchor_word===undefined?"":'<button class="cand" data-act="line" data-key="'
      +esc(x.id)+':anchor" data-line="'+esc(pre+slot+" anchor = "+x.anchor_word)
      +'">keep this anchor word</button>')
    +'</div>';
  var det=document.getElementById("det");
  det.innerHTML=h;
  det.querySelectorAll('[data-act="line"]').forEach(function(el){
    el.addEventListener("click",function(){ queue(el.dataset.key, el.dataset.line, el); });
  });
  det.querySelectorAll('[data-act="value"]').forEach(function(el){
    el.addEventListener("change",function(){
      if(!el.value){ delete pending[el.dataset.key]; refresh(); return; }
      queue(el.dataset.key, el.dataset.prefix + el.value);
      el.style.borderColor="#4aa96c";
    });
  });
}

/* --------------------------------------------------------------- panels */
function panels(){
  var h="", dec=[];
  allItems().forEach(function(it){
    var x=it.x;
    if(x.stub) dec.push([x.id,"has to be built — "+(x.stub.spec||"").slice(0,70)]);
    else if(x.confidence==="low"&&x.asset) dec.push([x.id,"picked "+x.asset+", not sure — "+(x.why||"").slice(0,70)]);
    else if(!x.asset&&x.kind!=="text"&&it.lane!=="narration") dec.push([x.id,"nothing bound"]);
    if(x.unsure) dec.push([x.id,"the creator marked this `?`"]);
  });
  if(dec.length){
    h+='<div class="panel warn"><h2>Needs a decision ('+dec.length+')</h2>';
    dec.forEach(function(d){ h+='<p class="q"><a onclick="select(\''+d[0]+'\')">'+esc(d[0])+'</a> — '+esc(d[1])+'</p>'; });
    h+="</div>";
  }
  var qs=(R.open&&R.open.questions)||[];
  if(qs.length){
    h+='<div class="panel warn"><h2>Open questions</h2>';
    qs.forEach(function(q){ h+='<p class="q"><b>'+esc(q.id)+'</b> ['+esc(q.code)+'] '+esc(q.msg)+'</p>'; });
    h+="</div>";
  }
  if((R.alternates||[]).length){
    h+='<div class="panel"><h2>Variants not selected</h2>';
    R.alternates.forEach(function(a){
      h+='<p class="q"><b>'+esc(a.name)+' (variant '+esc(a.variant)+')</b> — ~'+a.est_s
        +'s estimated, '+a.components+' components. '+esc((a.narration||"").slice(0,120))
        +' <a data-act="line" data-key="variant:'+esc(a.cell)+'" data-line="'
        +esc("variant "+a.name+" = "+a.variant)+'">switch to it</a>'
        +' — switching changes the words, so it re-runs the clock.</p>';
    });
    h+="</div>";
  }
  if((PAYLOAD.thumb_misses||[]).length){
    h+='<div class="panel"><h2>Thumbnails</h2><p class="q">'+PAYLOAD.thumb_misses.length
      +' asset(s) could not be read from this machine, so they render as cards: '
      +esc(PAYLOAD.thumb_misses.join(", "))+'. The timeline is unaffected.</p></div>';
  }
  var host=document.getElementById("panels");
  host.innerHTML=h;
  host.querySelectorAll('[data-act="line"]').forEach(function(el){
    el.addEventListener("click",function(){ queue(el.dataset.key, el.dataset.line, null); });
  });
}

/* ------------------------------------------------------------ revisions */
function queue(key,line,el){
  pending[key]=line;
  if(el){ el.parentElement.querySelectorAll(".cand").forEach(function(b){b.classList.remove("sel");});
          el.classList.add("sel"); }
  refresh();
}
function lines(){ return Object.keys(pending).map(function(k){return pending[k];}); }
function refresh(){
  var n=lines().length;
  document.getElementById("cnt").textContent=n+(n===1?" note":" notes");
  document.getElementById("txt").value=lines().join("\n");
}
function toggleOut(){ var o=document.getElementById("out");
  o.style.display=o.style.display==="block"?"none":"block"; refresh(); }
function copyBlock(){
  var t=lines().join("\n");
  if(!t){ alert("Nothing queued yet — click a candidate, pick from the dropdown, or type a note."); return; }
  navigator.clipboard.writeText(t).then(function(){
    document.getElementById("cnt").textContent="copied"; },
    function(){ document.getElementById("out").style.display="block";
      document.getElementById("txt").value=t; document.getElementById("txt").select(); });
}

/* ------------------------------------------------------------- playback */
document.getElementById("seek").addEventListener("input",function(){
  seekTo(this.value/1000*TOTAL); });
document.getElementById("play").addEventListener("click",function(){
  if(playing){ clearInterval(playing); playing=null; this.textContent="▶"; return; }
  this.textContent="❚❚";
  var last=Date.now();
  playing=setInterval(function(){
    var now=Date.now(); seekTo(playhead+(now-last)/1000); last=now;
    if(playhead>=TOTAL){ clearInterval(playing); playing=null;
      document.getElementById("play").textContent="▶"; }
  },50);
});
document.addEventListener("keydown",function(e){
  if(e.target.tagName==="INPUT"||e.target.tagName==="TEXTAREA") return;
  if(e.key==="ArrowRight") seekTo(playhead+(e.shiftKey?1:0.1));
  if(e.key==="ArrowLeft") seekTo(playhead-(e.shiftKey?1:0.1));
});
window.addEventListener("resize",movePh);
header(); tracks(); panels(); preview(); refresh();
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tracks")
    t.add_argument("reel")
    t.add_argument("out", nargs="?", default="REEL-TRACKS.html")
    t.add_argument("--clock", default=None,
                   help="clock.json — gives the preview exact word highlighting")
    args = ap.parse_args()

    reel = json.load(open(args.reel))
    clock = json.load(open(args.clock)) if args.clock else None
    n, misses = build(reel, args.out, clock)
    size = os.path.getsize(args.out) / 1024.0
    print("%d beats · %d thumbnails embedded · %.0f KB -> %s"
          % (len(reel.get("beats", [])), n, size, args.out))
    if misses:
        print("  %d asset(s) not readable here, rendered as cards: %s"
              % (len(misses), ", ".join(misses[:8])))
    print("  open it from disk — no server, no network.")


if __name__ == "__main__":
    main()
