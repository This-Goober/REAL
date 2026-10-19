"""Frozen selection and media mirror case handling; no network."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from .common import sha256, write_json, write_jsonl
from .data import media_url
from .preflight import run


class PreflightTests(unittest.TestCase):
    def test_uppercase_source_preserves_filename_but_uses_lowercase_folder(self):
        mirror = {'template': 'https://example.test/{initial}/{vid}.mp4'}
        self.assertEqual(media_url(mirror, 'VUV77-5ERxA_360.0_510.0'),
                         'https://example.test/v/VUV77-5ERxA_360.0_510.0.mp4')
        for vid in ['lower_0.0_10.0', '_under_0.0_10.0', '-dash_0.0_10.0']:
            self.assertTrue(media_url(mirror, vid).endswith('/' + vid + '.mp4'))

    def test_missing_media_retained_without_replacing_frozen_cases(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            rows = [dict(qid=i, vid=f'Video{i}_0.0_10.0', query='query', duration=10) for i in [1, 2]]
            write_jsonl(p / 'cases.jsonl', rows)
            digest = sha256(p / 'cases.jsonl')
            write_json(p / 'manifest.json', dict(inputs_sha256=digest, qids=[1, 2]))
            def head(vid, mirrors):
                return dict(vid=vid, available=vid.startswith('Video1'), reported_bytes=100)
            with patch('bench.academic.preflight.media_head', side_effect=head):
                result = run(p / 'cases.jsonl', p / 'manifest.json', p / 'out.json')
            self.assertEqual(result['n_queries'], 2)
            self.assertEqual(result['available_queries'], 1)
            self.assertEqual(len(result['media']), 2)
            self.assertEqual(sha256(p / 'cases.jsonl'), digest)
            write_jsonl(p / 'cases.jsonl', list(reversed(rows)))
            with self.assertRaisesRegex(ValueError, 'frozen selection'):
                run(p / 'cases.jsonl', p / 'manifest.json', p / 'out.json')


if __name__ == '__main__':
    unittest.main()
