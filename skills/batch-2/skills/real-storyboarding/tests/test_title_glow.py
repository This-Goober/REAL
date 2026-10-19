"""Native Basic Title channel conformance; visual FCP import is a separate check."""
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

S = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(S / 'real-compile/scripts'))
import adapt
from fcpxml import Story, BuildError, order_children
from real_core import Frames

MOTI = Path('/Applications/Final Cut Pro.app/Contents/PlugIns/MediaProviders/'
            'MotionEffect.fxp/Contents/Resources/PETemplates.localized/'
            'Titles.localized/Bumper:Opener.localized/Basic Title.localized/Basic Title.moti')


class TitleGlowTests(unittest.TestCase):
    def build(self, **extra):
        layer = dict(id='B1.L1', kind='text', style='caption', content='two\nlines',
                     t0=0, t1=2, font_size=55, position=[0, 90], **extra)
        spec, _ = adapt.layer_spec(layer, {}, {}, Frames('30'), 1080, 1920, {}, [], '.')
        maker = Story(dict(frame_rate='30', width=1080, height=1920), do_probe=False)
        element, _, _ = maker._make_item(spec, 0, 60)
        order_children(element)
        return ET.fromstring(element.render())

    def test_glow_only_survives_adapter_without_face_stroke_or_shadow(self):
        title = self.build(face=False, shadow=False,
                           glow=dict(color=[1, .88, .26, 1], opacity=1, blur=1, radius=0))
        style = title.find('text-style-def/text-style')
        self.assertEqual(style.get('fontSize'), '55')
        self.assertFalse({'fontColor', 'strokeColor', 'shadowColor'} & style.attrib.keys())
        groups = {p.get('name'): p for p in title.findall('param') if p.get('enabled')}
        self.assertEqual({k: v.get('enabled') for k, v in groups.items()},
                         {'Glow': '1', 'Face': '0', 'Outline': '0', 'Drop Shadow': '0'})
        self.assertEqual(title.find('text/text-style').text, 'two\nlines')
        self.assertEqual(title.find('adjust-transform').get('position'), '0 4.6875')
        self.assertEqual(title[0].tag, 'param')

    @unittest.skipUnless(MOTI.exists(), 'requires installed Apple Basic Title')
    def test_export_prefix_and_group_ids_match_apple_template(self):
        root = ET.parse(MOTI).getroot()
        title = self.build(face=False, shadow=False, glow={})
        # The native export identifies Main/Title/Style as these object IDs.
        layer = root.find(".//layer[@id='999166631']")
        text = layer.find("scenenode[@id='999166633']")
        style = text.find("style[@id='999166635']")
        self.assertIsNotNone(style)
        for p in title.findall('param'):
            parts = p.get('key').split('/')
            self.assertEqual(parts[:5], ['9999', '999166631', '999166633', '5', '999166635'])
            # Basic Title omits default-valued leaf channels. Group channels
            # are explicit; their IDs and names must resolve, never guessed.
            group = style.find("parameter[@id='%s']" % parts[5])
            self.assertIsNotNone(group)
            if len(parts) == 6:
                self.assertEqual(group.get('name'), p.get('name'))
        # This shipped preset serializes the default-valued leaf channels
        # omitted from Basic Title, providing an independent ID/name check.
        preset = MOTI.parents[5] / 'LibraryContent/Text Styles.localized/2D Styles.localized/Deep Glow.molo'
        preset_style = ET.parse(preset).find('.//style')
        for p in title.findall('param'):
            parts = p.get('key').split('/')[5:]
            node = preset_style
            for part in parts:
                node = node.find("parameter[@id='%s']" % part)
                self.assertIsNotNone(node)
            self.assertEqual(node.get('name'), p.get('name'))

    def test_regular_caption_output_does_not_gain_motion_parameters(self):
        title = self.build()
        self.assertEqual(title.findall('param'), [])
        self.assertEqual(title.find('text-style-def/text-style').get('fontColor'), '1 1 1 1')

    def test_invalid_glow_values_are_refused(self):
        for glow in (True, {'color': [1, 1, 0]}, {'opacity': 2},
                     {'blur': float('nan')}, {'radius': -1}, {'typo': 2}):
            with self.subTest(glow=glow), self.assertRaises(BuildError):
                self.build(glow=glow)


if __name__ == '__main__':
    unittest.main(verbosity=2)
