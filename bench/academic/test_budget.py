"""Spending admission and interruption handling; transport is always a fixture."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from .budget import Budget, BudgetStopped
from .common import write_json, write_jsonl
from .temporal import run as temporal_run


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.calls = 0

    def transport(self, cost=.4, reported='fixed', missing_cost=False):
        def call(prompt, images, out, model, max_cost):
            if (out / 'run.json').exists():
                return {'cached': True}
            self.calls += 1
            write_json(out / 'request.json', dict(max_cost_usd=max_cost))
            record = dict(request_sha256='fixture', ok=True, modelUsage={reported: {}})
            if not missing_cost:
                record['total_cost_usd'] = cost
            write_json(out / 'run.json', record)
            return {'windows': []}
        return call

    def test_cap_and_cached_reuse(self):
        budget = Budget(self.root, .7, 'fixed', self.transport())
        budget('query', [], self.root / 'first', 'fixed', .5)
        with self.assertRaisesRegex(BudgetStopped, 'remaining allowance'):
            budget('query', [], self.root / 'second', 'fixed', .5)
        self.assertEqual(self.calls, 1)
        self.assertTrue(budget('query', [], self.root / 'first', 'fixed', .5)['cached'])
        self.assertEqual(self.calls, 1)
        self.assertEqual(budget.status()['reported_cost_usd'], .4)

    def test_unknown_cost_and_actual_model_drift_halt_further_calls(self):
        for folder, transport in [('unknown', self.transport(missing_cost=True)),
                                  ('drift', self.transport(reported='changed'))]:
            with self.subTest(folder=folder):
                root = self.root / folder
                budget = Budget(root, 5, 'fixed', transport)
                with self.assertRaises(BudgetStopped):
                    budget('q', [], root / 'first', 'fixed', 1)
                count = self.calls
                with self.assertRaises(BudgetStopped):
                    budget('q', [], root / 'second', 'fixed', 1)
                self.assertEqual(self.calls, count)

    def test_overrun_preserves_actual_cost_and_stops(self):
        budget = Budget(self.root, 5, 'fixed', self.transport(cost=1.1))
        with self.assertRaises(BudgetStopped):
            budget('q', [], self.root / 'first', 'fixed', 1)
        self.assertEqual(budget.status()['reported_cost_usd'], 1.1)
        with self.assertRaises(BudgetStopped):
            budget('q', [], self.root / 'second', 'fixed', 1)
        self.assertEqual(self.calls, 1)

    def test_interruption_is_never_automatically_retried(self):
        transport = Mock(side_effect=RuntimeError('process interrupted'))
        budget = Budget(self.root, 5, 'fixed', transport)
        with self.assertRaisesRegex(RuntimeError, 'interrupted'):
            budget('q', [], self.root / 'first', 'fixed', 1)
        with self.assertRaises(BudgetStopped):
            budget('q', [], self.root / 'first', 'fixed', 1)
        with self.assertRaises(BudgetStopped):
            budget('q', [], self.root / 'second', 'fixed', 1)
        transport.assert_called_once()
        self.assertFalse(budget.status()['complete_cost_accounting'])

    def test_lock_blocks_concurrent_caller(self):
        transport = Mock()
        budget = Budget(self.root, 5, 'fixed', transport)
        (self.root / 'budget.lock').write_text('another caller')
        with self.assertRaisesRegex(BudgetStopped, 'budget lock'):
            budget('q', [], self.root / 'first', 'fixed', 1)
        transport.assert_not_called()
        self.assertTrue((self.root / 'budget.lock').exists())

    def test_missing_catalogue_is_retained_as_a_failed_temporal_case(self):
        root, cached, out = self.root / 'data', self.root / 'cached', self.root / 'out'
        write_jsonl(root / 'qvh/inputs/cases.jsonl',
                    [dict(qid=1, vid='v_0.0_10.0', query='cycling', duration=10)])
        write_json(cached / 'manifest.json', dict(test_fixture=True))
        model = Mock()
        rows = temporal_run(root, cached, out, model='fixed', infer_fn=model)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['pred_relevant_windows'], [])
        self.assertIn('FileNotFoundError', rows[0]['error'])
        model.assert_not_called()
        manifest = json.loads((out / 'manifest.json').read_text())
        self.assertEqual(manifest['catalogue_hashes'], {'1': None})


if __name__ == '__main__':
    unittest.main()
