"""Rebuilding must retain who selected a saved text style."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build import preserve_creator


class StyleOwnershipTests(unittest.TestCase):
    def fixture(self, owner='creator', style_owner='creator'):
        layer = dict(id='B1.L2', kind='text', chosen_by=owner, style='title', style_by=style_owner)
        old = dict(beats=[dict(id='B1', layers=[layer], audio=[])])
        new = dict(assets=[], open=dict(questions=[]),
                   beats=[dict(id='B1', layers=[dict(id='B1.L2', kind='text', chosen_by='claude',
                               style='caption', style_by='claude')], audio=[], flags=[])])
        return old, new

    def test_human_selected_style_keeps_its_owner_on_rebuild(self):
        old, new = self.fixture()
        original = copy.deepcopy(old)
        kept, conflicts = preserve_creator(new, old)
        layer = new['beats'][0]['layers'][0]
        self.assertEqual((kept, conflicts), (1, []))
        self.assertEqual((layer['style'], layer['style_by']), ('title', 'creator'))
        self.assertEqual(old, original)

    def test_model_style_is_not_relabelled_as_human_selected(self):
        old, new = self.fixture(style_owner='claude')
        preserve_creator(new, old)
        layer = new['beats'][0]['layers'][0]
        self.assertEqual((layer['style'], layer['style_by']), ('title', 'claude'))

    def test_unconfirmed_layer_uses_new_plan(self):
        old, new = self.fixture(owner='claude')
        kept, conflicts = preserve_creator(new, old)
        self.assertEqual((kept, conflicts), (0, []))
        self.assertEqual(new['beats'][0]['layers'][0]['style'], 'caption')


if __name__ == '__main__':
    unittest.main()
