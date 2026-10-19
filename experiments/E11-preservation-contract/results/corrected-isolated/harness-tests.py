"""Protect preservation diagnostics against false passes and lost failures."""
import copy
import unittest

from bench.preservation_study import CHECKS, compare_edls, choice_changes, summarize


def edl(events):
    return dict(fps=30, w=1080, h=1920, total_f=90, events=events)


def event(**changes):
    return dict(kind='image', asset='img01', f0=10, f1=40, **changes)


class ComparisonTests(unittest.TestCase):
    def test_duplicate_placements_are_not_collapsed(self):
        self.assertFalse(compare_edls(edl([event(), event()]), edl([event()]))['exact'])

    def test_one_frame_boundary_error_fails(self):
        changed = event()
        changed['f1'] += 1
        result = compare_edls(edl([event()]), edl([changed]))
        self.assertFalse(result['exact'])
        self.assertEqual(len(result['missing']), 1)
        self.assertEqual(len(result['extra']), 1)

    def test_source_in_and_project_format_errors_fail(self):
        for field, value in [('fps', 25), ('w', 1920), ('total_f', 91)]:
            actual = edl([event()])
            actual[field] = value
            self.assertFalse(compare_edls(edl([event()]), actual)['exact'])
        self.assertFalse(compare_edls(edl([event()]), edl([event(src_in=1)]))['exact'])


class ChoiceTests(unittest.TestCase):
    def fixture(self):
        return dict(beats=[dict(layers=[dict(id='B1.L2', kind='text', chosen_by='creator',
                    content='Remember this', anchor_word=5, anchor_text='cue', dur_source='explicit',
                    dur_s=2, t0=3, t1=5, style='caption', font_size=55)])])

    def test_derived_times_may_change(self):
        before = self.fixture()
        after = copy.deepcopy(before)
        after['beats'][0]['layers'][0].update(t0=2.4, t1=4.4)
        self.assertEqual(choice_changes(before, after), [])

    def test_saved_choices_and_ownership_must_not_change(self):
        before = self.fixture()
        for key, val in [('anchor_word', 6), ('dur_s', 1), ('chosen_by', 'claude'),
                         ('content', 'Changed'), ('font_size', 64)]:
            with self.subTest(key=key):
                after = copy.deepcopy(before)
                after['beats'][0]['layers'][0][key] = val
                self.assertTrue(choice_changes(before, after))

    def test_missing_or_duplicate_layers_are_visible(self):
        before = self.fixture()
        after = copy.deepcopy(before)
        after['beats'][0]['layers'] = []
        self.assertTrue(choice_changes(before, after))
        after = copy.deepcopy(before)
        after['beats'][0]['layers'] *= 2
        with self.assertRaises(ValueError):
            choice_changes(before, after)


class AccountingTests(unittest.TestCase):
    def rows(self):
        return [dict(seed=seed, scale=scale, eligible=True, status='complete',
                     **{key: True for key in CHECKS})
                for seed in (1, 2) for scale in ('faster', 'slower')]

    def test_failed_cases_stay_in_fixed_denominator(self):
        rows = self.rows()
        rows[0].update(status='failed', **{key: False for key in CHECKS})
        group = summarize(rows, (1, 2))['scales']['faster']
        self.assertEqual(group['denominator'], 2)
        self.assertEqual(group['failed'], 1)
        self.assertEqual(group['all_checks_passed'], 1)

    def test_ineligible_case_is_retained(self):
        rows = self.rows()
        rows[0] = dict(seed=1, scale='faster', status='ineligible', eligible=False)
        group = summarize(rows, (1, 2))['scales']['faster']
        self.assertEqual((group['denominator'], group['ineligible'], group['all_checks_passed']), (2, 1, 1))

    def test_missing_duplicate_or_unexpected_rows_rejected(self):
        rows = self.rows()
        unexpected = copy.deepcopy(rows)
        unexpected[0]['seed'] = 3
        for bad in (rows[:-1], rows + [rows[0]], unexpected):
            with self.assertRaises(ValueError):
                summarize(bad, (1, 2))

    def test_result_does_not_depend_on_row_order(self):
        rows = self.rows()
        rows[0]['retimed_exact'] = False
        self.assertEqual(summarize(rows, (1, 2)), summarize(rows[::-1], (1, 2)))


if __name__ == '__main__':
    unittest.main()
