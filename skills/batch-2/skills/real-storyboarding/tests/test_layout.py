"""Static compositing must survive the reel -> XML handoff."""
import copy
from pathlib import Path
import sys
import unittest
import subprocess
import tempfile
import xml.etree.ElementTree as ET
S=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(S/'real-compile/scripts'))
sys.path.insert(0,str(S/'real-storyboarding/scripts'))
sys.path.insert(0,str(S/'real-brainstorm/scripts'))
import ballpark
import adapt
import notebook
import build
from real_core import Frames,validate_document,SchemaError
from fcpxml import build_transform,build_blend,Clock,Story,probe
from fractions import Fraction

class LayoutTests(unittest.TestCase):
 def test_probed_video_audio_metadata_matches_actual_streams(self):
  with tempfile.TemporaryDirectory() as tmp:
   for has_audio in (False, True):
    with self.subTest(has_audio=has_audio):
     path=Path(tmp)/('with-audio.mp4' if has_audio else 'silent.mp4')
     cmd=['ffmpeg','-v','error','-f','lavfi','-i','color=s=32x32:r=30']
     if has_audio:cmd+=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
     subprocess.run(cmd+['-t','0.2','-c:v','mpeg4','-c:a','aac',str(path)],check=True,capture_output=True)
     self.assertEqual(probe(str(path))['has_audio'],has_audio)
     maker=Story({'frame_rate':'30','width':720,'height':1280})
     media=maker._resolve_media(str(path),'video')
     maker.res.asset(media)
     resource=next(ET.fromstring(el.render()) for el in maker.res.elements if ET.fromstring(el.render()).tag=='asset')
     self.assertEqual(resource.get('hasAudio'),'1' if has_audio else '0')
     self.assertEqual(resource.get('audioChannels'), '2' if has_audio else None)
     clip,_,_=maker._make_item(dict(type='video',src=str(path),volume_db=-60),0,6)
     xml=ET.fromstring(clip.render())
     self.assertEqual(xml.find('adjust-volume') is not None,has_audio)
     self.assertEqual(xml.get('audioRole'), 'dialogue' if has_audio else None)
     self.assertEqual(xml.get('srcEnable'), None if has_audio else 'video')
 def test_failed_probe_does_not_claim_known_stream_metadata(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'invalid.mp4';path.write_text('not a media file')
   self.assertEqual(probe(str(path)),{})

 def test_faded_title_retains_editable_text_and_frame_timed_effect(self):
  layer=dict(id='B1.L3',kind='text',style='subtitle',content='By the road',t0=3,t1=5.5,font_size=52,font_face='Bold',stroke_width=3,shadow=True,shadow_offset='4 315',shadow_blur=4,fade_in=4/30,fade_out=6/30)
  spec,_=adapt.layer_spec(layer,{}, {},Frames('30'),720,1280,{'markers':False},[],'.')
  maker=Story({'frame_rate':'30','width':720,'height':1280},do_probe=False)
  el,_,_=maker._make_item(spec,90,75)
  xml=ET.fromstring(el.render())
  self.assertEqual(xml.find('text/text-style').text,'By the road')
  style=xml.find('text-style-def/text-style')
  self.assertEqual((style.get('fontSize'),style.get('fontFace'),style.get('strokeWidth')),('52','Bold','3'))
  self.assertEqual(style.get('shadowOffset'),'4 315')
  kfs=xml.findall('adjust-blend/param/keyframeAnimation/keyframe')
  base=Fraction(xml.get('start').removesuffix('s'))
  self.assertEqual([round((Fraction(k.get('time').removesuffix('s'))-base)*30) for k in kfs],[0,4,69,75])
  self.assertEqual([float(k.get('value')) for k in kfs],[0,1,1,0])
 def test_fades_preserve_peak_opacity_instead_of_forcing_opaque(self):
  xml=ET.fromstring(build_blend({'fade_in':.2,'fade_out':.2,'opacity':.65},Clock('30'),0,60).render())
  self.assertEqual([float(k.get('value')) for k in xml.findall('.//keyframe')],[0,.65,.65,0])
 def test_fades_refuse_invalid_or_overlapping_durations(self):
  for bad in [{'fade_in':-1},{'fade_out':True},{'fade_in':float('nan')},{'fade_out':float('inf')},{'fade_in':.6,'fade_out':.5}]:
   with self.subTest(bad=bad),self.assertRaises(adapt.Refusal):adapt.apply_layout({},dict(t0=2,t1=3,**bad))

 def test_short_and_ambiguous_lyrics_keep_all_words(self):
  for text in ['I see it now', 'The river flows', 'And I still carry those days with me']:
   comp=notebook.make_component('narration: '+text,1,'C1',set())
   self.assertEqual(comp['type'],'narration')
   self.assertEqual(comp['text'],text)
   self.assertEqual(comp['words'],len(text.split()))
   rough=ballpark.make_component('narration: '+text,1)
   self.assertEqual((rough['type'],rough['text'],rough['words']),('narration',text,len(text.split())))

 def test_overlay_transform_and_opacity_export(self):
  layer=dict(id='B1.L2',kind='video',asset='piano',t0=0,t1=5,src_in=12,src_out=17,fit='fit',transform={'position':[0,-455],'scale':1},opacity=.65)
  asset=dict(file='piano.mp4',dur_s=210,w=720,h=330)
  spec,_=adapt.layer_spec(layer,{}, {'piano':asset},Frames('30'),720,1280,{'markers':False},[],'.')
  self.assertEqual(spec['start'],12)
  clock=Clock('30')
  t=ET.fromstring(build_transform(spec['transform'],clock,360,1280).render())
  b=ET.fromstring(build_blend(spec,clock,360,150).render())
  self.assertEqual(t.attrib['position'],'0 -35.546875')
  self.assertEqual(b.attrib['amount'],'0.65')
  self.assertEqual(spec['volume_db'],-60)
 def test_fill_scale_composes_with_inset(self):
  spec=adapt.apply_layout({'transform':{'scale':2}}, {'id':'L','transform':{'scale':[.5,.25],'position':[8,-9]},'opacity':0})
  self.assertEqual(spec['transform'],{'scale':[1,.5],'position':[8,-9]})
  self.assertEqual(spec['opacity'],0)
 def test_bad_layout_refuses_instead_of_silently_dropping_it(self):
  for bad in [{'opacity':65},{'opacity':True},{'opacity':float('nan')},{'transform':{'position':[1]}},{'transform':{'scale':0}},{'transform':{'from':{}}},{'transform':{'rotation':float('inf')}}]:
   with self.subTest(bad=bad),self.assertRaises(adapt.Refusal):adapt.apply_layout({},bad)
 def test_creator_layout_survives_rebuild(self):
  l=dict(id='B1.L1',asset='v',chosen_by='creator',opacity=.65,fade_in=.2,fade_out=.3,transform={'position':[0,-455]})
  old={'beats':[{'id':'B1','layers':[l]}]}
  new={'assets':[{'id':'v'}],'beats':[{'id':'B1','layers':[{'id':'B1.L1','asset':'v'}],'flags':[]}],'open':{'questions':[]}}
  build.preserve_creator(new,old)
  got=new['beats'][0]['layers'][0]
  self.assertEqual((got['fade_in'],got['fade_out']),(.2,.3));self.assertEqual(got['opacity'],.65);self.assertEqual(got['transform'],l['transform'])
if __name__=='__main__':unittest.main(verbosity=2)
