"""A caption's look is a creator decision the revision grammar can state: size, colour,
shadow, glow, face, and the words with their line breaks."""
import copy
import sys
import unittest
from pathlib import Path

S = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(S / 'real-storyboarding/scripts'))
import revise  # noqa: E402


def reel():
    return {
        'version': 1, 'reel': {'title': 't', 'fps': 30, 'width': 1080, 'height': 1920},
        'clock': {'mode': 'measured', 'total_s': 6.0}, 'assets': [],
        'beats': [dict(id='B1', name='one', t0=0.0, t1=6.0, w0=0, w1=3, narration='it shows its work',
                       layers=[dict(id='B1.L1', z=0, kind='video', asset=None, anchor_word=0, anchor_text='it',
                                    offset_ms=0, t0=0.0, t1=6.0, fit='fill', chosen_by='claude',
                                    confidence='low', why='t', base=True),
                               dict(id='B1.L2', z=1, kind='text', content='it shows its work', style='caption',
                                    style_by='claude', anchor_word=1, anchor_text='shows', offset_ms=0,
                                    t0=1.0, t1=2.9, fit='fit', chosen_by='claude', confidence='high', why='t')],
                       audio=[], flags=[])],
        'open': {'unbound_layers': [], 'unused_assets': [], 'unresolved_specs': [], 'questions': []},
    }


class CaptionLookTests(unittest.TestCase):
    def apply(self, r, line):
        log, unhandled = [], []
        revise.apply_one(r, 'B1', line, {}, log, unhandled)
        return r['beats'][0]['layers'][1], log, unhandled

    def test_size_color_shadow_text(self):
        r = reel()
        for line in ('L2 size = 60', 'L2 color = #B82E24', 'L2 shadow = on', 'L2 text = it shows / its work'):
            L, log, unhandled = self.apply(r, line)
            self.assertEqual(unhandled, [], line)
        self.assertEqual(L['font_size'], 60)
        self.assertEqual([round(x, 3) for x in L['color']], [0.722, 0.18, 0.141, 1])
        self.assertIs(L['shadow'], True)
        self.assertEqual(L['content'], 'it shows\nits work')
        self.assertEqual(L['style_by'], 'creator')

    def test_colours_in_other_spellings(self):
        for val, rgb in (('vermilion', [0.722, 0.18, 0.141]), ('255 255 255', [1, 1, 1]), ('0.5, 0.5, 0.5', [0.5, 0.5, 0.5])):
            L, _log, unhandled = self.apply(reel(), 'L2 colour = ' + val)
            self.assertEqual(unhandled, [], val)
            self.assertEqual([round(x, 3) for x in L['color'][:3]], rgb)

    def test_position(self):
        for val, pos in (('center', [0, 0]), ('bottom', [0, -620]), ('0 300', [0.0, 300.0])):
            L, _log, unhandled = self.apply(reel(), 'L2 position = ' + val)
            self.assertEqual(unhandled, [], val)
            self.assertEqual(L['position'], pos)
        _L, _log, unhandled = self.apply(reel(), 'L2 position = somewhere')
        self.assertEqual(len(unhandled), 1)

    def test_hold_until_the_next_caption(self):
        r = reel()
        log, unhandled = [], []
        revise.apply_one(r, 'B1', 'add text = "its / work" anchor 3', {"words": [
            {"i": i, "w": w, "start": float(i), "end": float(i) + 0.8} for i, w in enumerate("it shows its work".split())]},
            log, unhandled)
        self.assertEqual(unhandled, [])
        new = r['beats'][0]['layers'][2]
        self.assertEqual(new['content'], 'its\nwork')             # " / " breaks the line
        self.assertIsInstance(new['source_component'], str)        # the reel schema requires one
        for line in ('L2 hold = next', 'L3 hold = next'):
            self.apply(r, line)
        from real_core import settle_holds
        self.assertEqual(settle_holds(r), 2)
        first, second = r['beats'][0]['layers'][1], r['beats'][0]['layers'][2]
        self.assertAlmostEqual(first['t1'], second['t0'])          # held until the next caption
        self.assertAlmostEqual(second['t1'], 6.0)                  # the last holds to the beat's end
        # a dissolve into the next beat ends the hold where the dissolve starts
        r['beats'].append(dict(id='B2', name='two', t0=6.0, t1=9.0, w0=4, w1=4, narration='x', layers=[],
                               audio=[], flags=[], transition_in={'name': 'Cross Dissolve', 'dur_s': 1.0}))
        settle_holds(r)
        self.assertAlmostEqual(second['t1'], 5.5)
        # off releases it
        L, _log, unhandled = self.apply(r, 'L3 hold = off')
        self.assertNotIn('hold_to_next', r['beats'][0]['layers'][2])
        _L, _log, unhandled = self.apply(reel(), 'L2 hold = forever')
        self.assertEqual(len(unhandled), 1)

    def test_refusals(self):
        L, _log, unhandled = self.apply(reel(), 'L1 size = 60')
        self.assertEqual(len(unhandled), 1)              # not a text layer
        self.assertNotIn('font_size', reel()['beats'][0]['layers'][0])
        for line in ('L2 size = big', 'L2 color = reddish', 'L2 shadow = maybe'):
            _L, _log, unhandled = self.apply(reel(), line)
            self.assertEqual(len(unhandled), 1, line)

    def test_look_survives_a_rebuild(self):
        import build
        old = reel()
        for line in ('L2 size = 60', 'L2 color = #B82E24', 'L2 shadow = on', 'L2 text = it shows / its work'):
            self.apply(old, line)
        new = reel()
        build.preserve_creator(new, old)
        L = new['beats'][0]['layers'][1]
        self.assertEqual((L['font_size'], L['shadow'], L['content']), (60, True, 'it shows\nits work'))


if __name__ == '__main__':
    unittest.main()
