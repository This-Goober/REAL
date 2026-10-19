"""Independent invariants for paired, clustered public-benchmark comparisons."""
import os
from pathlib import Path
import unittest

import numpy as np

from .common import read_jsonl
from .compare import compare, paired_bootstrap, per_query, source_id


class ClusterTests(unittest.TestCase):
    def test_preserves_query_weighting_with_unequal_cluster_sizes(self):
        result = paired_bootstrap([[0], [0], [100]], [[0], [0], [0]], ['a', 'a', 'b'])
        self.assertAlmostEqual(result['left'][0]['mean'], 100 / 3)
        self.assertEqual(result['left'][0]['ci95'], [0, 100])
        self.assertEqual(result['left_minus_right'], result['left'])

    def test_pairing_removes_shared_variation_and_is_repeatable(self):
        values = [[0], [100], [20], [30]]
        a = paired_bootstrap(values, values, ['a', 'a', 'b', 'c'])
        self.assertEqual(a['left_minus_right'], [dict(mean=0, ci95=[0, 0])])
        self.assertEqual(a, paired_bootstrap(values, values, ['a', 'a', 'b', 'c']))
        self.assertLess(a['left'][0]['ci95'][0], a['left'][0]['ci95'][1])

    def test_one_source_is_not_treated_as_many_independent_queries(self):
        with self.assertRaisesRegex(ValueError, 'source videos'):
            paired_bootstrap([[0], [100]], [[100], [0]], ['a', 'a'])
        with self.assertRaisesRegex(ValueError, 'finite paired'):
            paired_bootstrap([[np.nan], [0]], [[0], [0]], ['a', 'b'])

    def test_original_source_id_survives_underscores_and_different_excerpts(self):
        self.assertEqual(source_id('original_video_with_under_0.0_150.0'),
                         source_id('original_video_with_under_150.0_300.0'))
        with self.assertRaises(ValueError):
            source_id('ambiguous-video')


@unittest.skipUnless(os.environ.get('REAL_ACADEMIC_DATA'), 'pinned evaluator data required')
class OfficialTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(os.environ['REAL_ACADEMIC_DATA'])

    def test_full_1550_sample_reproduced_from_unrounded_query_contributions(self):
        base = self.root / 'sources/qvh'
        aggregate, rows = per_query(self.root,
            read_jsonl(base / 'standalone_eval/sample_val_preds.jsonl'),
            read_jsonl(base / 'data/highlight_val_release.jsonl'))
        self.assertEqual(len(rows), 1550)
        self.assertEqual(aggregate['metrics']['MR-full-mAP'], 32.2)

    def test_reordered_ids_pair_correctly_and_failed_cases_score_zero(self):
        refs = [dict(qid=i, vid=f'source{i}_0.0_10.0', duration=10, relevant_windows=[[2, 4]])
                for i in [1, 2]]
        good = [dict(qid=r['qid'], vid=r['vid'], pred_relevant_windows=[[2, 4, .9]]) for r in refs]
        fail = [dict(qid=r['qid'], vid=r['vid'], pred_relevant_windows=[], error='timeout') for r in refs]
        result = compare(self.root, good, list(reversed(fail)), refs)
        self.assertEqual(result['official_scores']['right']['failed'], 2)
        self.assertEqual(result['intervals']['left_minus_right']['MR-full-mAP'],
                         dict(mean=100, ci95=[100, 100]))
        same = compare(self.root, good, list(reversed(good)), refs)
        self.assertEqual(same['intervals']['left_minus_right']['MR-full-mAP']['ci95'], [0, 0])
        with self.assertRaisesRegex(ValueError, 'match reference ids'):
            compare(self.root, good[:-1], fail, refs)


if __name__ == '__main__':
    unittest.main()
