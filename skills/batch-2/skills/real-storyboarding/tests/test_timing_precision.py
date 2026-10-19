"""Independent frame-boundary fixtures for initial timing, revisions and retiming."""
import copy
from pathlib import Path
import sys
import unittest

S = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(S / 'real-storyboarding/scripts'))
import clock
import build
import revise
from real_core import Frames


class PrecisionTests(unittest.TestCase):
    def test_exact_half_frame_endpoints_use_ties_to_even(self):
        # These measured endpoints failed the frozen E11 retiming run. At
        # 30 fps they are exactly 256.5 and 610.5 frames respectively.
        frames = Frames('30')
        for seconds, expected in [(8.55, 256), (20.35, 610), (8.65, 260)]:
            with self.subTest(seconds=seconds):
                self.assertEqual(frames.f(seconds), expected)

    def fixture(self):
        # 7.270 + .4 * (7.470 - 7.270) = 7.350; use a non-tie
        # whose explicit end is immediately below the half-frame at 9.25.
        words = [dict(i=0, w='first', start=0, end=.2),
                 dict(i=1, w='cue', start=7.269, end=7.471),
                 dict(i=2, w='last', start=10, end=10.2)]
        item = dict(id='B1.L1', component='C1.1', source_component='C1.1',
                    beat='B1', anchor_word=1, offset_ms=0, placement='inline',
                    base=False, dur_source='explicit', dur_s=1.9, order=1,
                    t0=1, t1=2.9, kind='text')
        beat = dict(id='B1', w0=0, w1=2, wordless=False, t0=0, t1=10.2,
                    layers=[item], audio=[dict(kind='narration', t0=0, t1=10.2)])
        C = dict(words=words, beats=[copy.deepcopy(beat)], placements=[copy.deepcopy(item)],
                 rates={'cut_into_word':.4}, total_s=10.2)
        return C, beat, item

    def assert_frames(self, item):
        # Independently specified expected frames: start=7.3498, end=9.2498.
        self.assertAlmostEqual(item['t0'], 7.3498)
        self.assertAlmostEqual(item['t1'], 9.2498)
        self.assertEqual((Frames('30').f(item['t0']), Frames('30').f(item['t1'])), (220,277))

    def test_initial_derivation_does_not_round_across_frame_boundary(self):
        C, _, _ = self.fixture()
        clock.derive(C, C['rates'])
        self.assert_frames(C['placements'][0])

    def test_creator_reanchor_does_not_round_across_frame_boundary(self):
        C, beat, item = self.fixture()
        revise.reanchor(item, beat, C, [])
        self.assert_frames(item)

    def test_retime_preserves_precision_for_creator_moved_layer(self):
        C, beat, item = self.fixture()
        C['placements'][0]['anchor_word'] = 0  # creator moved away from the plan
        reel = dict(beats=[beat], clock={})
        build.retime(reel, C)
        self.assert_frames(item)

    def test_both_sides_of_half_frame_remain_distinct_at_common_rates(self):
        for rate in ('24','25','30','60','29.97'):
            f = Frames(rate)
            half = (277.5 * f.num / f.den)
            for delta, expected in [(-.0001,277),(.0001,278)]:
                C = {'words':[dict(i=0,start=half+delta-.08,end=half+delta+.12)]}
                with self.subTest(rate=rate,delta=delta):
                    self.assertEqual(f.f(revise.word_time(C,0)),expected)


if __name__ == '__main__':
    unittest.main()
