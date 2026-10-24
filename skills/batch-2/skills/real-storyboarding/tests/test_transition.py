"""A dissolve into a beat is a creator decision the storyboard carries, checks and preserves."""
import copy
from pathlib import Path
import sys
import unittest

S = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(S / 'real-storyboarding/scripts'))
import build  # noqa: E402
import revise  # noqa: E402
from real_core import transition_problems  # noqa: E402


def shot(bid, asset, word, t0, t1, src_in=None):
    L = dict(id=bid + '.L1', z=0, kind='video', asset=asset, anchor_word=0, anchor_text=word,
             offset_ms=0, t0=t0, t1=t1, fit='fill', chosen_by='claude', confidence='high',
             why='bound by tag', base=True)
    if src_in is not None:
        L['src_in'] = src_in
    return L


def reel(src_in=None, first_file_s=6.0):
    return {
        'version': 1, 'reel': {'title': 't', 'fps': 30, 'width': 1080, 'height': 1920},
        'clock': {'mode': 'measured', 'total_s': 10.0},
        'assets': [dict(id='A1', kind='video', dur_s=first_file_s, file='a.mov'),
                   dict(id='A2', kind='video', dur_s=6.0, file='b.mov')],
        'beats': [dict(id='B1', name='one', t0=0.0, t1=5.0, w0=0, w1=0, narration='one',
                       layers=[shot('B1', 'A1', 'one', 0.0, 5.0)], audio=[], flags=[]),
                  dict(id='B2', name='two', t0=5.0, t1=10.0, w0=1, w1=1, narration='two',
                       layers=[shot('B2', 'A2', 'two', 5.0, 10.0, src_in)], audio=[], flags=[])],
        'open': {'unbound_layers': [], 'unused_assets': [], 'unresolved_specs': [], 'questions': []},
    }


class TransitionTests(unittest.TestCase):
    def apply(self, r, line):
        log, unhandled = [], []
        revise.apply_one(r, 'B2', line, {}, log, unhandled)
        return log, unhandled

    def test_refused_without_a_head_handle(self):
        r = reel()
        log, unhandled = self.apply(r, 'transition in = dissolve 1s')
        self.assertEqual(log, [])
        self.assertEqual(len(unhandled), 1)
        self.assertIn('handle', unhandled[0])
        self.assertNotIn('transition_in', r['beats'][1])

    def test_applied_with_handles_then_removed(self):
        r = reel(src_in=0.5)
        log, unhandled = self.apply(r, 'transition in = dissolve 1s')
        self.assertEqual(unhandled, [], unhandled)
        tr = r['beats'][1]['transition_in']
        self.assertEqual((tr['name'], tr['dur_s'], tr['chosen_by']), ('Cross Dissolve', 1.0, 'creator'))
        errs, _warns = build.validate(r)
        self.assertEqual(errs, [])
        log, unhandled = self.apply(r, 'transition in = none')
        self.assertEqual(unhandled, [])
        self.assertNotIn('transition_in', r['beats'][1])

    def test_validate_catches_a_missing_tail_handle(self):
        r = reel(src_in=0.5, first_file_s=5.0)        # B1's file ends with its shot
        r['beats'][1]['transition_in'] = {'name': 'Cross Dissolve', 'dur_s': 1.0, 'chosen_by': 'creator'}
        errs, _warns = build.validate(r)
        self.assertTrue(any('transition in' in e and 'handle after the cut' in e for e in errs), errs)

    def test_first_beat_and_stills(self):
        r = reel(src_in=0.5)
        self.assertTrue(transition_problems(dict(r['beats'][0], transition_in={'dur_s': 1.0}), None,
                                            {a['id']: a for a in r['assets']}))
        r['beats'][0]['layers'][0]['kind'] = 'image'      # a still has unlimited handles
        r['assets'][0]['dur_s'] = None
        self.assertEqual(transition_problems(dict(r['beats'][1], transition_in={'dur_s': 1.0}),
                                             r['beats'][0], {a['id']: a for a in r['assets']}), [])

    def test_preserved_across_a_rebuild(self):
        old = reel(src_in=0.5)
        old['beats'][1]['transition_in'] = {'name': 'Cross Dissolve', 'dur_s': 1.0, 'chosen_by': 'creator',
                                            'why': 'the creator asked for a dissolve into this beat'}
        new = reel(src_in=0.5)
        kept, conflicts = build.preserve_creator(new, old)
        self.assertEqual(conflicts, [])
        self.assertEqual(new['beats'][1]['transition_in'], old['beats'][1]['transition_in'])
        self.assertGreaterEqual(kept, 1)


if __name__ == '__main__':
    unittest.main()
