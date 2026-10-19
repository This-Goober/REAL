"""Coordinate conformance tests derived from Apple's FCPXML animation example.

https://developer.apple.com/documentation/professional-video-applications/animation
These use fixed expected values and independently authored XML, not just an
export/import round trip that could repeat the same unit error on both sides.
"""
from pathlib import Path
import sys, tempfile, unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT/'skills/batch-2/skills/real-compile/scripts'))
sys.path.insert(0, str(ROOT/'bench'))
from fcpxml import Story, Clock, build_transform
import fcpxml_edl

class GeometryTests(unittest.TestCase):
    def test_static_translation_uses_height_for_both_axes(self):
        # Apple's example: XML 10 10 moves 108 px in a 1080 px high frame.
        for width, height, xy in [(1920,1080,[108,108]), (720,1280,[128,128])]:
            with self.subTest(width=width,height=height):
                maker=Story(dict(frame_rate='30',width=width,height=height),do_probe=False)
                spec=dict(type='video',src='video.mp4',asset_duration=10,
                          transform=dict(position=xy,scale=[.6,.8],rotation=15,anchor=[2,3]))
                el,_,_=maker._make_item(spec,0,60)
                tr=ET.fromstring(el.render()).find('adjust-transform')
                self.assertEqual(tr.get('position'),'10 10')
                self.assertEqual(tr.get('scale'),'0.6 0.8')
                self.assertEqual(tr.get('rotation'),'15')
                self.assertEqual(tr.get('anchor'),'2 3')

    def test_portrait_piano_and_title_land_inside_frame(self):
        maker=Story(dict(frame_rate='30',width=720,height=1280),do_probe=False)
        piano,_,_=maker._make_item(dict(type='video',src='piano.mp4',asset_duration=210,
            transform={'position':[0,-475],'scale':1},opacity=.65),0,60)
        tr=ET.fromstring(piano.render()).find('adjust-transform')
        self.assertEqual(tr.get('position'),'0 -37.109375')
        # Interpret XML via documented percent-height semantics: a 330px high
        # fitted piano clip must occupy y=950..1280 in the 720x1280 frame.
        center_y=640-float(tr.get('position').split()[1])*1280/100
        self.assertEqual((center_y-165,center_y+165),(950,1280))
        for y,expected in [(-140,'0 -10.9375'),(380,'0 29.6875'),(300,'0 23.4375')]:
            with self.subTest(title_y=y):
                title,_,_=maker._make_item(dict(type='title',text='Visible',position=[0,y]),0,60)
                pos=ET.fromstring(title.render()).find('adjust-transform').get('position')
                self.assertEqual(pos,expected)
                self.assertEqual(640-float(pos.split()[1])*1280/100,640-y)

    def test_animated_translation_matches_apple_example_without_scaling_scale(self):
        spec={'from':{'position':[-54,108],'scale':1},
              'to':{'position':[108,216],'scale':.75},'duration':10}
        tr=ET.fromstring(build_transform(spec,Clock('30'),60,1080).render())
        pos=tr.findall("param[@name='position']/keyframeAnimation/keyframe")
        scale=tr.findall("param[@name='scale']/keyframeAnimation/keyframe")
        self.assertEqual([k.get('value') for k in pos],['-5 10','10 20'])
        self.assertEqual([k.get('time') for k in pos],['2s','12s'])
        self.assertEqual([k.get('value') for k in scale],['1 1','0.75 0.75'])

    def test_independent_benchmark_reader_interprets_native_percent_coordinates(self):
        # Deliberately authored without invoking the REAL XML generator.
        xml='''<fcpxml version="1.13"><resources>
        <format id="r1" width="1920" height="1080" frameDuration="1/30s"/>
        <effect id="r2" name="Basic Title" uid="title"/></resources>
        <library><event><project name="Apple coordinates"><sequence format="r1" duration="1s">
        <spine><title ref="r2" offset="0s" start="3600s" duration="1s">
        <text><text-style ref="ts1">Visible</text-style></text>
        <text-style-def id="ts1"><text-style fontSize="52"/></text-style-def>
        <adjust-transform position="-5 10"/></title></spine></sequence>
        </project></event></library></fcpxml>'''
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'known-coordinates.fcpxml';path.write_text(xml)
            edl=fcpxml_edl.parse(path)
        self.assertEqual(edl['events'][0]['position'],(-54,108))

if __name__=='__main__':unittest.main(verbosity=2)
