"""Scoring, leakage, and provenance regressions (no network/model calls)."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from .common import validate_spans, write_jsonl
from .data import prepare_qvh
from .medit import cut_f1, pair_metrics, score as medit_score, timecode_seconds, union_iou
from .pilot import binder_predict, catalogue_from, load_binder, DEFAULT_SKILLS
from .qvh import score as qvh_score
from .model import infer, extract_answer


class MetricsTests(unittest.TestCase):
    def test_perfect_and_disjoint(self):
        self.assertTrue(all(v == 1 for v in pair_metrics([[0, 2], [4, 6]], [[0, 2], [4, 6]]).values()))
        self.assertTrue(all(v == 0 for v in pair_metrics([[10, 12]], [[0, 2], [4, 6]]).values()))

    def test_union_does_not_fill_gaps_or_double_count(self):
        self.assertAlmostEqual(union_iou([[0, 2], [4, 6]], [[0, 6]]), 2 / 3)
        self.assertEqual(union_iou([[0, 2], [0, 2]], [[0, 2]]), 1)

    def test_duplicate_predictions_cannot_claim_one_reference_twice(self):
        self.assertAlmostEqual(cut_f1([[0, 2], [0, 2]], [[0, 2]], 0.5), 2 / 3)

    def test_greedy_matching_is_by_iou_not_input_order(self):
        self.assertEqual(cut_f1([[0, 3], [0, 2]], [[0, 2], [1, 3]], 0.5), 1)

    def test_empty_prediction_scores_zero(self):
        self.assertTrue(all(v == 0 for v in pair_metrics([], [[0, 2]]).values()))

    def test_timecodes_integer_and_fractional(self):
        self.assertEqual(timecode_seconds('00:00:01:15', 30), 1.5)
        self.assertAlmostEqual(timecode_seconds('00:01:00:00', '30000/1001'), 60.06)
        self.assertEqual(timecode_seconds('00:00:01:59', 60), 1 + 59 / 60)

    def test_invalid_timecodes_fail_instead_of_guessing(self):
        for tc, fps in [('00:00:00:30', 30), ('00:61:00:00', 30), ('00:00:00;01', 30), ('00:00:00:01', 0)]:
            with self.subTest(tc=tc, fps=fps), self.assertRaises(ValueError):
                timecode_seconds(tc, fps)

    def test_bad_spans_fail(self):
        for spans in ([[0, float('nan')]], [[2, 1]], [[-1, 2]], [[0, 11]], [[True, 2]]):
            with self.subTest(spans=spans), self.assertRaises(ValueError):
                validate_spans(spans, 10)

    def test_medit_averages_all_editors(self):
        refs = [{'qid': 'q', 'vid': 'v', 'references': [
            {'annotator_index': i, 'timecodes': [[f'00:00:0{s}:00', f'00:00:0{s+1}:00']]}
            for i, s in enumerate([0, 3, 6])]}]
        preds = [{'qid': 'q', 'vid': 'v', 'cuts': [[0, 1]]}]
        basis = {'v': {'fps': 30, 'duration': 10, 'provenance': 'test fixture'}}
        result = medit_score(preds, refs, basis)
        self.assertAlmostEqual(result['metrics']['mIoU'], 1 / 3)
        self.assertAlmostEqual(result['metrics']['F1@0.5'], 1 / 3)
        with self.assertRaises(ValueError):
            medit_score(preds, refs, {})
        with self.assertRaises(ValueError):
            medit_score([], refs, basis)


class AdapterTests(unittest.TestCase):
    def test_direct_confidence_order_is_canonical_and_values_unchanged(self):
        from .pilot import direct_prediction
        raw={'windows':[[0,2,.2],[2,4,.8],[4,6,.8]]}
        windows=[{'start':i,'end':i+2} for i in range(0,6,2)]
        result=direct_prediction(raw,{'duration':6},windows)
        self.assertEqual(result,[[2,4,.8],[4,6,.8],[0,2,.2]])
        self.assertEqual(raw['windows'][0],[0,2,.2])

    def test_fresh_selection_excludes_entire_original_source_videos(self):
        from .common import read_jsonl
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            write_jsonl(root/'sources/qvh/data/highlight_val_release.jsonl',[
                dict(qid=i,vid=f'{v}_0.0_150.0',query='query',duration=150,relevant_windows=[[10,20]])
                for i,v in enumerate(['old','new1','old','new2'])])
            write_jsonl(root/'exclude.jsonl',[dict(vid='old_150.0_300.0')])
            chosen=prepare_qvh(root,0,exclude_inputs=root/'exclude.jsonl')
            self.assertEqual({c['qid'] for c in chosen},{1,3})
            self.assertEqual(json.loads((root/'qvh/manifest.json').read_text())['excluded_source_videos'],['old'])

    def test_selection_is_answer_independent_and_public_inputs_have_no_answers(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / 'sources/qvh/data/highlight_val_release.jsonl'
            rows = [{'qid': i, 'vid': 'v' + str(i), 'query': 'query', 'duration': 10,
                     'relevant_windows': [[0, 1]], 'saliency_scores': [[4, 4, 4]]} for i in range(8)]
            write_jsonl(path, rows)
            before = prepare_qvh(root, 3)
            for r in rows:
                r['relevant_windows'] = [[8, 9]]
            write_jsonl(path, list(reversed(rows)))
            after = prepare_qvh(root, 3)
            self.assertEqual(before, after)
            self.assertTrue(all(set(r) == {'qid', 'vid', 'query', 'duration'} for r in after))

    def test_actual_binder_selects_visible_content_without_oracle_tags(self):
        windows = [{'id': f'A{i:03}', 'start': 2*i, 'end': 2*i+2} for i in range(3)]
        descriptions = ['dog playing ball running jumping grass', 'dog playing ball running jumping grass', 'person cooking food']
        answer = {'assets': [{'id': w['id'], 'role': d, 'shows': d, 'binds_to': d}
                             for w, d in zip(windows, descriptions)]}
        cat = catalogue_from(answer, windows, Path('source.mp4'))
        pred, evidence = binder_predict('dog playing ball running jumping grass', cat, windows, load_binder(DEFAULT_SKILLS))
        self.assertEqual(pred[0][:2], [0, 4])
        self.assertEqual(len(pred), 1)
        self.assertTrue(all(not a['tags'] for a in cat['assets']))
        answer['assets'].pop()
        with self.assertRaises(ValueError):
            catalogue_from(answer, windows, Path('source.mp4'))


class TransportTests(unittest.TestCase):
    def test_json_surrounding_prose_is_not_a_failed_prediction(self):
        answer, mode = extract_answer('Explanation.\n{"windows":[[0,2,0.5]]}\n')
        self.assertEqual(answer, {'windows': [[0, 2, 0.5]]})
        self.assertEqual(mode, 'json-with-surrounding-text')
        for text in ('{"windows":[]} {"windows":[]}', '{broken {"windows":[]}',
                     '{"windows":[]} }', '[]', 'no answer'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                extract_answer(text)

    def test_stream_transport_and_no_tool_context(self):
        event = {'type': 'result', 'subtype': 'success', 'result': '{"ok":true}', 'total_cost_usd': 0.01}
        proc = SimpleNamespace(returncode=0, stdout=json.dumps({'type': 'system'}) + '\n' + json.dumps(event), stderr='')
        with tempfile.TemporaryDirectory() as d, patch('subprocess.run', return_value=proc) as run, \
                patch('subprocess.check_output', return_value='test-cli'):
            self.assertEqual(infer('test prompt', [], d, 'test-model'), {'ok': True})
            args, kwargs = run.call_args
            cmd = args[0]
            self.assertEqual(cmd[cmd.index('--input-format') + 1], 'stream-json')
            self.assertEqual(cmd[cmd.index('--output-format') + 1], 'stream-json')
            self.assertEqual(cmd[cmd.index('--tools') + 1], '')
            self.assertIn('--safe-mode', cmd)
            self.assertNotEqual(kwargs['cwd'], str(Path.cwd()))
            with self.assertRaises(ValueError):
                infer('different prompt', [], d, 'test-model')

    def test_transport_failure_is_preserved_and_not_reused(self):
        proc = SimpleNamespace(returncode=1, stdout='', stderr='transport failed')
        with tempfile.TemporaryDirectory() as d, patch('subprocess.run', return_value=proc), \
                patch('subprocess.check_output', return_value='test-cli'):
            with self.assertRaisesRegex(RuntimeError, 'transport failed'):
                infer('test prompt', [], d, 'test-model')
            record = json.loads((Path(d) / 'run.json').read_text())
            self.assertFalse(record['ok'])
            with self.assertRaisesRegex(RuntimeError, 'previous inference failed'):
                infer('test prompt', [], d, 'test-model')


@unittest.skipUnless(os.environ.get('REAL_ACADEMIC_DATA'), 'set REAL_ACADEMIC_DATA for pinned upstream checks')
class UpstreamTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(os.environ['REAL_ACADEMIC_DATA'])
        from .common import read_jsonl
        self.refs = read_jsonl(self.root / 'sources/qvh/data/highlight_val_release.jsonl')

    def test_reproduces_official_sample_scores(self):
        from .common import read_jsonl
        pred = read_jsonl(self.root / 'sources/qvh/standalone_eval/sample_val_preds.jsonl')
        expected = json.loads((self.root / 'sources/qvh/standalone_eval/sample_val_preds_metrics_raw.json').read_text())
        result = qvh_score(self.root, pred, self.refs)
        self.assertEqual(result['n'], 1550)
        for key, value in result['metrics'].items():
            self.assertEqual(value, expected['brief'][key], key)

    def test_failures_count_and_ids_are_strict(self):
        refs = self.refs[:2]
        pred = [{'qid': r['qid'], 'vid': r['vid'], 'pred_relevant_windows': [], 'error': 'fixture'} for r in refs]
        result = qvh_score(self.root, pred, refs)
        self.assertEqual(result['failed'], 2)
        self.assertTrue(all(v == 0 for v in result['metrics'].values()))
        with self.assertRaises(ValueError):
            qvh_score(self.root, pred[:1], refs)
        with self.assertRaises(ValueError):
            qvh_score(self.root, pred + pred[:1], refs)

    def test_perfect_qvh_predictions_score_100(self):
        refs = self.refs[:8]
        pred = [{'qid': r['qid'], 'vid': r['vid'], 'pred_relevant_windows':
                 [[s, e, 1.0] for s, e in r['relevant_windows']]} for r in refs]
        self.assertTrue(all(v == 100 for v in qvh_score(self.root, pred, refs)['metrics'].values()))


if __name__ == '__main__':
    unittest.main()
