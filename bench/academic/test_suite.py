"""Suite integration with real media/scoring and a fixture replacing the paid CLI."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from .common import read_jsonl, sha256, write_json, write_jsonl
from .suite import execute, prepare, score_run, verify
from .model import infer


class SuiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'data'
        self.out = Path(self.temp.name) / 'run'
        self.selection = Path(self.temp.name) / 'selection.json'
        self.cases = self.root / 'qvh/inputs/cases.jsonl'
        self.refs = self.root / 'qvh/references/answers.jsonl'
        rows = [dict(qid=i, vid=f'video{i}_0.0_10.0', query='cycling', duration=10) for i in [1, 2]]
        write_jsonl(self.cases, rows)
        write_jsonl(self.refs, [{**r, 'relevant_windows': [[2, 4]]} for r in rows])
        write_json(self.selection, dict(inputs_sha256=sha256(self.cases),
                   references_sha256=sha256(self.refs), qids=[1, 2]))

    def test_prepare_is_answer_free_and_freezes_code_and_media_availability(self):
        with patch('bench.academic.budget.infer') as model:
            plan = prepare(self.root, self.selection, self.out)
        model.assert_not_called()
        self.assertEqual(plan['maximum_new_calls'], 8)
        self.assertTrue(all(not r['available'] for r in plan['media'].values()))
        self.assertEqual(verify(self.out), plan)
        self.assertNotIn('relevant_windows', (self.out / 'cases.jsonl').read_text())
        self.assertFalse((self.out / 'execution.json').exists())

    def test_all_media_failures_stay_in_every_condition_and_never_call_model(self):
        prepare(self.root, self.selection, self.out)
        with patch('bench.academic.budget.infer', side_effect=AssertionError('no model should run')) as model:
            state = execute(self.out, 'fixed-model', 1, .1)
        model.assert_not_called()
        self.assertEqual(state['status'], 'complete')
        self.assertEqual(state['budget']['reported_cost_usd'], 0)
        for relative in ['baseline/real-binder.jsonl', 'baseline/direct-vision.jsonl',
                         'temporal/real-temporal.jsonl', 'refined/direct-refined.jsonl']:
            rows = read_jsonl(self.out / relative)
            self.assertEqual([r['qid'] for r in rows], [1, 2])
            self.assertTrue(all(r['error'] and r['pred_relevant_windows'] == [] for r in rows))

    def test_input_changes_refused_before_inference_and_incomplete_runs_cannot_score(self):
        prepare(self.root, self.selection, self.out)
        write_json(self.out / 'state.json', dict(status='budget_or_model_review_required'))
        with self.assertRaisesRegex(ValueError, 'incomplete inference'):
            score_run(self.out)
        rows = read_jsonl(self.cases)
        rows[0]['query'] = 'changed question'
        write_jsonl(self.cases, rows)
        with patch('bench.academic.budget.infer') as model, self.assertRaisesRegex(ValueError, 'inputs changed'):
            execute(self.out, 'fixed-model', 1, .1)
        model.assert_not_called()

    def ready_media(self):
        for case in read_jsonl(self.cases):
            video = self.root / 'qvh/media' / (case['vid'] + '.mp4')
            video.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                            'color=c=blue:s=64x64:r=1:d=10', '-c:v', 'libx264', str(video)],
                           check=True, capture_output=True)
            write_json(video.with_suffix('.source.json'), dict(sha256=sha256(video)))
        prepare(self.root, self.selection, self.out)

    def cli_fixture(self, last_cost=.1):
        self.paid_calls = 0

        def transport(prompt, images, out, model, max_cost):
            if out.name == 'real-binder':
                answer = dict(assets=[dict(id=f'A{i:03d}', role='cycling',
                              shows='a person cycling', binds_to='cycling') for i in range(5)])
            elif out.name == 'real-temporal':
                answer = dict(bindings=[dict(component='request', candidates=[dict(
                    asset='source', first='A001', last='A001', confidence=.9,
                    reason='fixture visible evidence', limitations=[])])])
            else:
                answer = dict(windows=[[2, 4, .9]])

            def paid_cli(*args, **kwargs):
                self.paid_calls += 1
                self.assertNotIn('relevant_windows', kwargs['input'])
                cost = last_cost if out.name == 'direct-refined' and out.parent.name == '2' else .1
                event = dict(type='result', subtype='success', is_error=False,
                             result=json.dumps(answer), modelUsage={model: {}},
                             total_cost_usd=cost, usage={'input_tokens': 1, 'output_tokens': 1})
                return subprocess.CompletedProcess(args[0], 0, json.dumps(event), '')

            with patch('bench.academic.model.subprocess.check_output', return_value='fixture-cli'), \
                    patch('bench.academic.model.subprocess.run', side_effect=paid_cli):
                return infer(prompt, images, out, model, max_cost)
        return transport

    @unittest.skipUnless(os.environ.get('REAL_ACADEMIC_DATA'), 'pinned evaluator data required')
    def test_complete_four_condition_workflow_scores_and_resumes_without_new_calls(self):
        self.ready_media()
        shutil.copytree(Path(os.environ['REAL_ACADEMIC_DATA']) / 'sources', self.root / 'sources')
        with patch('bench.academic.budget.infer', side_effect=self.cli_fixture()):
            state = execute(self.out, 'fixed-model', 4, .5)
            self.assertEqual(state['status'], 'complete')
            self.assertEqual(self.paid_calls, 8)
            self.assertAlmostEqual(state['budget']['reported_cost_usd'], .8)
            self.assertEqual(execute(self.out, 'fixed-model', 4, .5)['status'], 'complete')
            self.assertEqual(self.paid_calls, 8)
        result = score_run(self.out)
        for name in ['real-temporal', 'direct-refined']:
            self.assertEqual(result['conditions'][name]['metrics']['MR-full-mAP'], 100)
            self.assertEqual(result['costs'][name]['model_calls'], 4)
            self.assertAlmostEqual(result['costs'][name]['reported_cost_usd'], .4)
        self.assertEqual(result['primary']['intervals']['left_minus_right']['MR-full-mAP'],
                         dict(mean=0, ci95=[0, 0]))

    def test_last_call_overrun_cannot_be_cleared_by_cached_resume_or_stale_complete_state(self):
        self.ready_media()
        with patch('bench.academic.budget.infer', side_effect=self.cli_fixture(last_cost=.6)):
            first = execute(self.out, 'fixed-model', 4, .5)
            self.assertEqual(first['status'], 'budget_or_model_review_required')
            resumed = execute(self.out, 'fixed-model', 4, .5)
            self.assertEqual(self.paid_calls, 8)
        self.assertEqual(resumed['status'], 'budget_or_model_review_required')
        write_json(self.out / 'state.json', dict(status='complete'))
        with self.assertRaisesRegex(ValueError, 'cost.*review'):
            score_run(self.out)

    def test_whole_run_lock_prevents_concurrent_writes(self):
        prepare(self.root, self.selection, self.out)
        (self.out / 'suite.lock').write_text('another process')
        with patch('bench.academic.budget.infer') as model:
            with self.assertRaisesRegex(ValueError, 'suite lock'):
                execute(self.out, 'fixed-model', 4, .5)
            with self.assertRaisesRegex(ValueError, 'suite lock'):
                score_run(self.out)
        model.assert_not_called()
        self.assertFalse((self.out / 'execution.json').exists())
        self.assertTrue((self.out / 'suite.lock').exists())

    def test_runtime_and_catalogue_schema_are_frozen(self):
        plan = prepare(self.root, self.selection, self.out)
        self.assertIn('Pillow', plan['environment']['packages'])
        schema = next(name for name in plan['source_hashes'] if name.endswith('asset-catalog.schema.json'))
        (self.out / 'code' / schema).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            verify(self.out)
        with patch('bench.academic.suite.environment', return_value={'changed': True}), \
                self.assertRaisesRegex(ValueError, 'runtime environment changed'):
            verify(self.out)


if __name__ == '__main__':
    unittest.main()
