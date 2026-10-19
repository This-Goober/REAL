"""Replay accounting checks: malformed/missing output, gating and provenance."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import replay_oneshot as replay

XML = '''<fcpxml version="1.13"><resources>
<format id="f" frameDuration="1/30s" width="1080" height="1920"/>
<asset id="a" duration="2s"><media-rep src="file:///media/clip01.mp4"/></asset>
</resources><library><event><project name="test"><sequence format="f" duration="1s">
<spine><asset-clip ref="a" offset="0s" start="0s" duration="1s"/></spine>
</sequence></project></event></library></fcpxml>'''


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.folder = self.project / replay.CONDITIONS[0]
        self.folder.mkdir()
        self.xml = self.folder / 'timeline.fcpxml'
        self.xml.write_text(XML)
        (self.project / 'truth.json').write_text(json.dumps(dict(fps=30, w=1080, h=1920,
            total_f=30, events=[dict(kind='video', asset='clip01', f0=0, f1=30, z=0, src_in=0)])))

    def score(self):
        return replay.score_case(1, replay.CONDITIONS[0], self.project, Path('validator'), Path('dtd'))

    def test_invalid_but_parseable_output_retains_raw_score_only(self):
        answers = [SimpleNamespace(returncode=0, stdout='', stderr=''),
                   SimpleNamespace(returncode=3, stdout='', stderr='invalid DTD')]
        with patch.object(replay.subprocess, 'run', side_effect=answers):row = self.score()
        self.assertEqual(row['quality']['f1@1.0'], 1)
        self.assertEqual(row['valid_quality']['f1@1.0'], 0)
        self.assertTrue(row['parsed'])
        self.assertFalse(row['dtd_valid'])

    def test_missing_xml_receives_zero_without_running_validator(self):
        self.xml.unlink()
        with patch.object(replay.subprocess, 'run') as run:row = self.score()
        run.assert_not_called()
        self.assertEqual(row['quality']['f1@1.0'], 0)
        self.assertFalse(row['available'])

    def test_unsupported_construct_is_explicit_not_silently_ignored(self):
        self.xml.write_text(XML.replace('<asset-clip ref="a"', '<clip ref="a"'))
        answer = SimpleNamespace(returncode=0, stdout='', stderr='')
        with patch.object(replay.subprocess, 'run', return_value=answer):row = self.score()
        self.assertEqual(row['reader_coverage_issues'], ['spine:clip'])
        self.assertEqual(row['quality']['f1@1.0'], 0)
        self.assertFalse(row['parsed'])

    def test_malformed_xml_receives_zero(self):
        self.xml.write_text('<fcpxml>')
        answer = SimpleNamespace(returncode=1, stdout='', stderr='invalid XML')
        with patch.object(replay.subprocess, 'run', return_value=answer):row = self.score()
        self.assertEqual(row['quality']['f1@1.0'], 0)
        self.assertIn('ParseError', row['failure'])

    def test_summary_preserves_missing_case_and_pairs_by_seed(self):
        rows=[]
        for s in (1,2):
            for c in replay.CONDITIONS:
                value=0.0 if s==2 and c==replay.CONDITIONS[1] else 1.0
                rows.append(dict(seed=s, condition=c, available=bool(value), parsed=bool(value),
                    dtd_valid=bool(value), semantic_valid=bool(value),
                    quality={m:value for m in replay.SCORES},valid_quality={m:value for m in replay.SCORES}))
        report=replay.summarize(rows[::-1], [1,2])
        self.assertEqual(report['conditions'][replay.CONDITIONS[1]]['raw']['f1@1.0']['mean'], .5)
        self.assertEqual(report['paired_real_minus_model'][replay.CONDITIONS[1]]['quality']['mean'], .5)
        with self.assertRaises(ValueError):replay.summarize(rows[:-1], [1,2])
        with self.assertRaises(ValueError):replay.summarize(rows+[rows[0]], [1,2])

    def test_prompt_audit_detects_stale_inputs_and_modified_xml(self):
        folder=self.project/'oneshot-claude-sonnet-5-5';folder.mkdir()
        (self.project/'NOTEBOOK.md').write_text('notebook')
        (self.project/'revisions.txt').write_text('')
        (self.project/'measured.json').write_text(json.dumps({'words':[dict(i=0,w='hello',start=0,end=1)]}))
        (self.project/'asset-catalog.json').write_text(json.dumps({'assets':[dict(id='clip01',f='Videos/clip01.mp4',k='video',dur=2,w=1080,h=1920)]}))
        prompt="""NOTEBOOK.md (the creator's script):
----------------------------------
notebook
----------------------------------
ASSET CATALOGUE file://here/<relative path>):
- clip01: Videos/clip01.mp4 (video, 2.0s, 1080x1920)

MEASURED WORD TIMES (index:word[start-end] in seconds):
0:hello[0.000-1.000]

CREATOR REVISIONS:
(none)

FCPXML RULES (these are notes)
"""
        (folder/'prompt.txt').write_text(prompt)
        from oneshot_llm import extract_xml
        (folder/'response.txt').write_text(XML)
        (folder/'timeline.fcpxml').write_text(extract_xml(XML))
        (folder/'run.json').write_text(json.dumps(dict(model='claude-sonnet-5-5',got_xml=True)))
        self.assertTrue(replay.audit_prompt(self.project,folder)['passed'])
        (self.project/'NOTEBOOK.md').write_text('another project')
        self.assertFalse(replay.audit_prompt(self.project,folder)['checks']['notebook'])
        (folder/'timeline.fcpxml').write_text(extract_xml(XML)+'\nchanged')
        self.assertFalse(replay.audit_prompt(self.project,folder)['checks']['response_extraction'])


if __name__=='__main__':unittest.main()
