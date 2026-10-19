"""Sequential admission checks for model calls using persisted cost records.

This is a local stop rule, not a billing guarantee: the provider may exceed a
per-call limit within an in-flight response. Unknown cost or a limit overrun
halts further calls. Cached results can still be read without spending again.
"""
from pathlib import Path
import json
import os

from .common import finite, write_json
from .model import infer


class BudgetStopped(RuntimeError):
    pass


def needs_review(state):
    return (not state['complete_cost_accounting'] or state['per_call_overruns']
            or state['model_drift_records']
            or state['reported_cost_usd'] > state['total_allowance_usd'] + 1e-9)


class Budget:
    def __init__(self, out, total_cap, model, transport=None):
        if not finite(total_cap) or total_cap <= 0:
            raise ValueError('finite positive total allowance required')
        self.out = Path(out).resolve()
        self.total_cap = total_cap
        self.model = model
        self.transport = transport or infer
        self.out.mkdir(parents=True, exist_ok=True)

    def status(self):
        calls, unknown, overruns, drift = [], [], [], []
        for path in sorted(self.out.rglob('run.json')):
            record = json.loads(path.read_text())
            if 'request_sha256' not in record:
                continue
            calls.append(record)
            cost = record.get('total_cost_usd')
            if not finite(cost) or cost < 0:
                unknown.append(str(path.relative_to(self.out)))
            request_file = path.with_name('request.json')
            request = json.loads(request_file.read_text()) if request_file.exists() else {}
            limit = request.get('max_cost_usd')
            if finite(cost) and finite(limit) and cost > limit:
                overruns.append(str(path.relative_to(self.out)))
            if ((record.get('ok') or record.get('modelUsage'))
                    and set(record.get('modelUsage', {})) != {self.model}):
                drift.append(str(path.relative_to(self.out)))
        spent = sum(r['total_cost_usd'] for r in calls
                    if finite(r.get('total_cost_usd')) and r['total_cost_usd'] >= 0)
        pending = [str(p.relative_to(self.out)) for p in self.out.rglob('pending-call.json')
                   if not p.with_name('run.json').exists()]
        state = dict(total_allowance_usd=self.total_cap, reported_cost_usd=spent,
                     remaining_known_allowance_usd=max(0, self.total_cap - spent),
                     model_calls=len(calls), unknown_cost_records=unknown,
                     per_call_overruns=overruns, model_drift_records=drift,
                     pending_calls=pending, complete_cost_accounting=not unknown and not pending)
        write_json(self.out / 'budget-status.json', state)
        return state

    def __call__(self, prompt, images, out, model, max_cost=1.0):
        lock = self.out / 'budget.lock'
        try:
            handle = lock.open('x')
        except FileExistsError as exc:
            raise BudgetStopped('another caller holds the budget lock; do not auto-retry') from exc
        try:
            with handle:
                handle.write(str(os.getpid()))
            return self._call(prompt, images, out, model, max_cost)
        finally:
            lock.unlink(missing_ok=True)

    def _call(self, prompt, images, out, model, max_cost):
        out = Path(out).resolve()
        if not out.is_relative_to(self.out) or model != self.model:
            raise ValueError('call is outside the frozen run or model revision')
        if not finite(max_cost) or max_cost <= 0:
            raise ValueError('finite positive call allowance required')
        # infer verifies request identity and never retries a saved failure.
        if (out / 'run.json').exists():
            return self.transport(prompt, images, out, model, max_cost)
        if (out / 'request.json').exists():
            raise BudgetStopped('saved request has no final call record; do not retry')
        state = self.status()
        if state['unknown_cost_records'] or state['per_call_overruns'] or state['model_drift_records']:
            raise BudgetStopped('unknown cost, per-call overrun, or model drift requires review')
        if state['reported_cost_usd'] + max_cost > self.total_cap + 1e-9:
            raise BudgetStopped('remaining allowance cannot cover one full call cap')
        # An interruption before a result must not be silently retried. The
        # transport normally writes run.json even on failure; this marker
        # records a crash before it can do so.
        pending = out / 'pending-call.json'
        if pending.exists():
            raise BudgetStopped('interrupted call has no final cost record')
        outstanding = list(self.out.rglob('pending-call.json'))
        if any(not p.with_name('run.json').exists() for p in outstanding):
            raise BudgetStopped('another interrupted call has unknown cost')
        write_json(pending, dict(model=model, max_cost_usd=max_cost))
        try:
            answer = self.transport(prompt, images, out, model, max_cost)
            state = self.status()
            if (state['model_drift_records'] or state['per_call_overruns']
                    or not state['complete_cost_accounting']):
                raise BudgetStopped('call cost or reported model revision requires review')
            return answer
        finally:
            if (out / 'run.json').exists():
                pending.unlink(missing_ok=True)
            self.status()
