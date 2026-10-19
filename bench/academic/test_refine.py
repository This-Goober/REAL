"""Comparator failure accounting and provenance checks, with no model calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from .common import read_jsonl, sha256, write_json, write_jsonl
from .pilot import direct_prompt
from .refine import run


class RefinementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cached, self.out = self.root / 'cached', self.root / 'out'
        self.cases = self.root / 'cases.jsonl'
        self.case = dict(qid=1, vid='video', query='a person cycling', duration=4)
        write_jsonl(self.cases, [self.case])
        write_json(self.cached / 'manifest.json', dict(inputs_sha256=sha256(self.cases),
                   qids=[1], max_cost_per_call_usd=1.0))
        self.base = self.cached / '1'
        images = self.base / 'evidence'
        images.mkdir(parents=True)
        (images / 'sheet.jpg').write_bytes(b'same image bytes for transport mock')
        self.digest = sha256(images / 'sheet.jpg')
        write_json(images / 'evidence.json', dict(windows=[dict(start=0,end=2),dict(start=2,end=4)],
                   sheets=[dict(file='sheet.jpg', sha256=self.digest)]))
        write_json(self.base / 'direct-vision/answer.json', dict(windows=[[0,2,.8]]))
        write_json(self.base / 'direct-vision/request.json', dict(prompt=direct_prompt(self.case),
                   images=[dict(sha256=self.digest)]))
        write_json(self.base / 'direct-vision/run.json', self.record(.2))
        write_jsonl(self.cached / 'direct-vision.jsonl',
                    [dict(qid=1,vid='video',pred_relevant_windows=[[0,2,.8]])])

    def record(self, cost):
        return dict(ok=True, modelUsage={'fixed-model': {}}, total_cost_usd=cost, wall_s=1)

    def invoke(self):
        return run(self.cases, self.cached, self.out, 'fixed-model')

    def test_same_images_both_call_costs_and_no_answers(self):
        def fake(prompt, images, out, model, cap):
            self.assertEqual([sha256(p) for p in images], [self.digest])
            self.assertIn('a person cycling', prompt)
            self.assertIn('[[0,2,0.8]]', prompt)
            self.assertNotIn('relevant_windows', prompt)
            self.assertEqual((model, cap), ('fixed-model', 1.0))
            write_json(out / 'run.json', self.record(.3))
            return dict(windows=[[0,4,.7]])
        with patch('bench.academic.refine.infer', side_effect=fake) as model:
            rows = self.invoke()
        self.assertEqual(model.call_count, 1)
        self.assertEqual(rows[0]['pred_relevant_windows'], [[0,4,.7]])
        costs = json.loads((self.out / 'costs.json').read_text())
        self.assertEqual(costs['reported_cost_usd'], .5)
        self.assertEqual(costs['model_calls'], 2)
        self.assertTrue(costs['cost_complete'])

    def test_failed_first_call_remains_in_denominator_without_retry(self):
        write_jsonl(self.cached / 'direct-vision.jsonl',
                    [dict(qid=1,vid='video',pred_relevant_windows=[],error='timeout')])
        write_json(self.base / 'direct-vision/run.json', dict(ok=False, error='timeout'))
        with patch('bench.academic.refine.infer') as model:
            rows = self.invoke()
        model.assert_not_called()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['pred_relevant_windows'], [])
        self.assertIn('timeout', rows[0]['error'])
        self.assertFalse(json.loads((self.out / 'costs.json').read_text())['cost_complete'])

    def test_bad_refinement_does_not_fall_back_and_keeps_cost(self):
        def fake(prompt, images, out, model, cap):
            write_json(out / 'run.json', self.record(.3))
            return dict(windows=[[0,3,.9]])  # Not on the declared grid.
        with patch('bench.academic.refine.infer', side_effect=fake):
            rows = self.invoke()
        self.assertEqual(rows[0]['pred_relevant_windows'], [])
        self.assertIn('grid', rows[0]['error'])
        self.assertEqual(json.loads((self.out / 'costs.json').read_text())['reported_cost_usd'], .5)

    def test_model_drift_and_reference_leakage_refused_before_inference(self):
        write_json(self.base / 'direct-vision/run.json',
                   dict(ok=True,modelUsage={'changed-model':{}}))
        with patch('bench.academic.refine.infer') as model, self.assertRaisesRegex(ValueError, 'revision'):
            self.invoke()
        model.assert_not_called()
        write_jsonl(self.cases, [{**self.case, 'relevant_windows': [[0,4]]}])
        with patch('bench.academic.refine.infer') as model, self.assertRaisesRegex(ValueError, 'answer-free'):
            self.invoke()
        model.assert_not_called()

    def test_changed_cached_predictions_refused(self):
        write_jsonl(self.cached / 'direct-vision.jsonl',
                    [dict(qid=1,vid='video',pred_relevant_windows=[[0,4,.8]])])
        with patch('bench.academic.refine.infer') as model:
            rows = self.invoke()
        model.assert_not_called()
        self.assertIn('differs', rows[0]['error'])


if __name__ == '__main__':
    unittest.main()
