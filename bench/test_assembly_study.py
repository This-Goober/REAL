"""Reporting must retain failed cases and pair identical seeds."""
import copy
import unittest
from bench.assembly_study import METRICS, summarize


class StudyTests(unittest.TestCase):
    def rows(self):
        return [dict(seed=s,condition=c,pipeline_ok=True,structural={},
                     quality={m:1.0 for m in METRICS})
                for s in (1,2) for c in ('published','revised','estimated')]

    def test_failed_cases_stay_in_denominator(self):
        rows=self.rows()
        rows[1].update(pipeline_ok=False,structural=None,quality={m:0.0 for m in METRICS})
        result=summarize(rows,[1,2])
        self.assertEqual(result['conditions']['revised']['pipeline_pass'],1)
        self.assertEqual(result['conditions']['revised']['metrics']['f1@1.0']['mean'],.5)

    def test_missing_and_duplicate_conditions_refused(self):
        rows=self.rows()
        for bad in (rows[:-1],rows+[copy.deepcopy(rows[0])]):
            with self.assertRaises(ValueError): summarize(bad,[1,2])

    def test_paired_differences_use_seed_identity_not_input_order(self):
        rows=self.rows()
        rows[0]['quality']['f1@1.0']=.25
        rows[3]['quality']['f1@1.0']=.75
        a=summarize(rows,[1,2]);b=summarize(list(reversed(rows)),[1,2])
        self.assertEqual(a,b)
        self.assertEqual(a['paired_differences']['revised-minus-published']['f1@1.0']['mean'],.5)


if __name__=='__main__':unittest.main()
