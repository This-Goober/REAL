"""Temporal evidence and source-coordinate regressions; no model/network calls."""
import copy
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

SKILLS = Path(__file__).resolve().parents[2]
SB = SKILLS / 'real-storyboarding/scripts'
CO = SKILLS / 'real-compile/scripts'
sys.path.insert(0, str(CO))
sys.path.insert(0, str(SB))
import ground
import bind
import build
import adapt
import revise


def fixture():
    nb = {'cells': [{'id': 'C1', 'groups': [{'parallel': False, 'components': [
        dict(id='C1.1', type='video', text='a person preparing food', dur_s=2, tags=[])]}]}]}
    cat = {'assets': [dict(id='v', f='video.mp4', k='video', dur=12, observations=[
        dict(id=f'o{i}', start=i*2, end=i*2+2, description='visible evidence') for i in range(6)])]}
    answer = {'bindings': [{'component': 'C1.1', 'candidates': [dict(
        asset='v', first='o3', last='o4', confidence=.9, reason='Preparing food across both views', limitations=[])]}]}
    return nb, cat, answer


class GroundTests(unittest.TestCase):
    def test_complete_event_and_alternative_boundaries(self):
        nb, cat, answer = fixture()
        answer['bindings'][0]['candidates'].append(dict(asset='v', first='o3', last='o3', confidence=.6,
                                                       reason='A narrower alternative', limitations=['shorter context']))
        events = ground.resolve(ground.prepare(nb, cat), answer)['bindings']['C1.1']
        self.assertEqual([(e['source_in'], e['source_out']) for e in events], [(6,10),(6,8)])
        self.assertEqual(events[0]['evidence'], ['o3','o4'])

    def test_confidence_ranking_is_stable_without_changing_values(self):
        nb,cat,answer=fixture()
        first=answer['bindings'][0]['candidates'][0];first['confidence']=.3
        answer['bindings'][0]['candidates'].append(dict(first,first='o1',last='o1',confidence=.8))
        events=ground.resolve(ground.prepare(nb,cat),answer)['bindings']['C1.1']
        self.assertEqual([(e['source_in'],e['confidence']) for e in events],[(2,.8),(6,.3)])

    def test_bad_ids_confidence_and_duplicate_proposals_refused(self):
        nb, cat, answer = fixture()
        for patch in ({'first':'invented'}, {'last':'o1'}, {'confidence':float('nan')}, {'confidence':True}, {'confidence':1.1}):
            bad=copy.deepcopy(answer);bad['bindings'][0]['candidates'][0].update(patch)
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                ground.resolve(ground.prepare(nb,cat),bad)
        answer['bindings'][0]['candidates'] *= 2
        with self.assertRaisesRegex(ValueError,'duplicate'):
            ground.resolve(ground.prepare(nb,cat),answer)

    def test_unobserved_gaps_and_invalid_catalogue_refused(self):
        nb,cat,answer=fixture();cat['assets'][0]['observations'][4]['start']=9
        with self.assertRaisesRegex(ValueError,'unobserved'):
            ground.resolve(ground.prepare(nb,cat),answer)
        cat['assets'][0]['observations'][4]['end']=15
        with self.assertRaises(ValueError):ground.prepare(nb,cat)

    def test_explicit_tags_and_reference_exclusions(self):
        nb,cat,answer=fixture();extra=copy.deepcopy(cat['assets'][0]);extra.update(id='other',tags=['chosen'])
        cat['assets'].append(extra);nb['cells'][0]['groups'][0]['components'][0]['tags']=['chosen']
        request=ground.prepare(nb,cat)
        self.assertEqual(request['components'][0]['asset_ids'],['other'])
        with self.assertRaises(ValueError):ground.resolve(request,answer)
        extra['beat']='reference'
        self.assertEqual(ground.prepare(nb,cat)['components'],[])

    def test_stale_and_tampered_groundings_rejected(self):
        nb,cat,answer=fixture();resolved=ground.resolve(ground.prepare(nb,cat),answer)
        bad=copy.deepcopy(resolved);bad['bindings']['C1.1'][0]['source_in']=0
        with self.assertRaises(ValueError):ground.apply(nb,cat,{'C1.1':{}},bad)
        cat['assets'][0]['observations'][0]['description']='changed'
        with self.assertRaises(ValueError):ground.apply(nb,cat,{'C1.1':{}},resolved)

    def test_empty_grounding_stubs_and_creator_choice_survives(self):
        nb,cat,answer=fixture();answer['bindings'][0]['candidates']=[]
        resolved=ground.resolve(ground.prepare(nb,cat),answer)
        b={'C1.1':dict(asset='v', chosen_by='claude')}
        ground.apply(nb,cat,b,resolved)
        self.assertIsNone(b['C1.1']['asset']);self.assertIsNotNone(b['C1.1']['stub'])
        b={'C1.1':dict(asset='v', chosen_by='creator',src_in=3)}
        ground.apply(nb,cat,b,resolved);self.assertEqual(b['C1.1']['src_in'],3)

    def test_partial_match_cannot_be_high_confidence_binding(self):
        nb,cat,answer=fixture();answer['bindings'][0]['candidates'][0]['limitations']=['object identity uncertain']
        b={'C1.1':{}}
        ground.apply(nb,cat,b,ground.resolve(ground.prepare(nb,cat),answer))
        self.assertEqual(b['C1.1']['confidence'],'low');self.assertIn('uncertain',b['C1.1']['why'])
        answer['bindings'][0]['candidates'][0]['limitations']=[]
        nb['cells'][0]['groups'][0]['components'][0]['unsure']=True
        ground.apply(nb,cat,b,ground.resolve(ground.prepare(nb,cat),answer))
        self.assertEqual(b['C1.1']['confidence'],'low')


class SourceTests(unittest.TestCase):
    def test_window_bounds_for_video_and_explicit_audio(self):
        for entry in ({'src_in':-1},{'src_in':float('nan')},{'src_in':9},
                      {'src_in':6,'src_out':7},{'src_in':6,'src_out':15}):
            with self.subTest(entry=entry):self.assertTrue(adapt.source_problems(entry,{'dur_s':12},4))
        self.assertFalse(adapt.source_problems({'src_in':6,'src_out':10},{'dur_s':12},4))

    def test_source_coordinates_survive_creator_preservation(self):
        old={'beats':[{'id':'B1','layers':[dict(id='B1.L1',asset='v',chosen_by='creator',src_in=6,src_out=10)]}]}
        new={'open':{'questions':[]},'assets':[{'id':'v'}],'beats':[{'id':'B1','layers':[dict(id='B1.L1',asset='v')]}]}
        build.preserve_creator(new,old)
        self.assertEqual(new['beats'][0]['layers'][0]['src_in'],6)
        self.assertEqual(new['beats'][0]['layers'][0]['src_out'],10)

    def test_creator_revision_keeps_linked_audio_in_sync_and_clears_swapped_source(self):
        layer=dict(id='B1.L1',asset='v',kind='video',source_component='C1.1',t0=0,t1=2,src_in=6,src_out=10)
        audio=dict(id='B1.A1',asset='v',kind='source',source_video_component='C1.1',t0=0,t1=2,src_in=6,src_out=10)
        reel={'assets':[dict(id='v',kind='video',dur_s=12),dict(id='other',kind='video',dur_s=12)],
              'open':{'unbound_layers':[]},'beats':[{'id':'B1','layers':[layer],'audio':[audio]}]}
        log,unhandled=[],[]
        revise.apply_one(reel,'B1','L1 source = 8-12',None,log,unhandled)
        self.assertEqual(unhandled,[]);self.assertEqual((layer['src_in'],audio['src_in']),(8,8))
        self.assertEqual((layer['t0'],layer['t1']),(0,2))
        revise.apply_one(reel,'B1','L1 source = 8-12',None,log,unhandled)
        self.assertEqual(unhandled,[])  # confirming an already matching audio choice is safe
        revise.apply_one(reel,'B1','L1 source = -1-4',None,log,unhandled)
        self.assertEqual(len(unhandled),1);self.assertEqual(layer['src_in'],8)
        revise.apply_one(reel,'B1','layer L1 = other',None,log,unhandled)
        self.assertNotIn('src_in',layer);self.assertNotIn('src_out',layer)
        old={'beats':[{'id':'B1','layers':[dict(id='B1.L1',asset='v',chosen_by='creator')]}]}
        layer.update(src_in=6,src_out=10)
        reel['open']['questions']=[]
        build.preserve_creator(reel,old)
        self.assertNotIn('src_in',layer)

    def test_cli_to_fcpxml_keeps_video_and_own_audio_source_in(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            def run(script,*args,ok=True):
                proc=subprocess.run([sys.executable,str(script),*args],cwd=root,text=True,capture_output=True)
                if ok:self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
                return proc
            source=root/'video.mp4'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=160x90:r=30:d=12',
                            '-f','lavfi','-i','sine=frequency=440:duration=12','-c:v','libx264','-pix_fmt','yuv420p',
                            '-c:a','aac','-shortest',str(source)],check=True,capture_output=True)
            (root/'NOTEBOOK.md').write_text('---\nreel: Source test\naspect: 16:9\n---\n\n## scene\n\n<video clip of preparing food ~2s | audio of the raw take at full volume>\n')
            run(SB/'notebook.py','parse','NOTEBOOK.md','-o','notebook.json')
            run(SB/'clock.py','time','notebook.json','-o','clock.json')
            nb=json.loads((root/'notebook.json').read_text());_,cat,answer=fixture()
            cat['assets'][0].update(f=str(source),w=160,h=90,fps=30,rotation=0,shows='preparing food')
            (root/'catalog.json').write_text(json.dumps(cat))
            request=ground.prepare(nb,cat);answer['bindings'][0]['component']=request['components'][0]['id']
            (root/'groundings.json').write_text(json.dumps(ground.resolve(request,answer)))
            run(SB/'bind.py','bind','notebook.json','catalog.json','--groundings','groundings.json','-o','bindings.json')
            run(SB/'build.py','build','notebook.json','clock.json','bindings.json','-o','reel.json','--fps','30','--assets-root',str(root))
            reel=json.loads((root/'reel.json').read_text())
            self.assertEqual(reel['beats'][0]['layers'][0]['src_in'],6)
            self.assertEqual(reel['beats'][0]['audio'][0]['src_in'],6)
            run(CO/'adapt.py','reel.json','-o','story.json','--no-stubs')
            story=json.loads((root/'story.json').read_text())
            self.assertEqual(story['beats'][0]['start'],6)
            self.assertEqual(story['connected'][0]['start'],6)
            run(CO/'fcpxml.py','build','story.json','out.fcpxml')
            tree=ET.parse(root/'out.fcpxml')
            clips=tree.findall('.//spine//asset-clip')
            self.assertGreaterEqual(len(clips),2)
            self.assertTrue(all(Fraction(c.attrib['start'].removesuffix('s'))==6 for c in clips))
            # Distinct explicit audio intervals must not be merged into one source run.
            second=copy.deepcopy(reel['beats'][0]['audio'][0]);second.update(id='B1.A2',t0=1,t1=2,src_in=8)
            reel['beats'][0]['audio'][0]['t1']=1;reel['beats'][0]['audio'].append(second)
            (root/'reel.json').write_text(json.dumps(reel))
            run(CO/'adapt.py','reel.json','-o','two-audio.json','--no-stubs')
            audio=json.loads((root/'two-audio.json').read_text())['connected']
            self.assertEqual([a['start'] for a in audio],[6,8])
            reel['beats'][0]['layers'][0]['src_out']=7
            (root/'reel.json').write_text(json.dumps(reel))
            rejected=run(CO/'adapt.py','reel.json','-o','bad-story.json','--no-stubs',ok=False)
            self.assertNotEqual(rejected.returncode,0);self.assertIn('selected source window',rejected.stdout)
            self.assertFalse((root/'bad-story.json').exists())


if __name__=='__main__':unittest.main(verbosity=2)
