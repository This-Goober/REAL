"""Build a local, synthetic REAL interaction demo using the production scripts.

No inference, generated content media, native editor access, or publication.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bench'))
import project
import run_real
import fcpxml_edl
from repair import diff, event_key

SKILLS = ROOT / 'skills/batch-2/skills'
SB = SKILLS / 'real-storyboarding/scripts'
CO = SKILLS / 'real-compile/scripts'


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def layer(reel):
    return next(x for b in reel['beats'] for x in b['layers'] if x['id'] == 'B4.L3')


def command(log, *args, cwd=None):
    run = subprocess.run([sys.executable, *map(str, args)], cwd=cwd,
                         capture_output=True, text=True)
    log.append(dict(args=list(map(str, args)), returncode=run.returncode,
                    stdout=run.stdout, stderr=run.stderr))
    if run.returncode:
        raise RuntimeError(run.stdout + run.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--pool', type=Path, required=True)
    args = parser.parse_args()
    out, pool = args.out.resolve(), args.pool.resolve()
    out.mkdir(parents=True, exist_ok=False)
    fixture = out / 'project'
    # Reproduce the already documented development notebook (seed 1, seven
    # beats). The pool is existing synthetic media, not newly generated footage.
    project.build_project(str(fixture), str(pool), 1, 7, 'normal')
    result = run_real.run(str(fixture), 'estimated', str(SKILLS))
    if not result['ok']:
        raise RuntimeError(result['error'])
    before, after = fixture / 'before', fixture / 'after'
    (fixture / 'real-estimated').rename(before)
    shutil.copytree(before, after, ignore=shutil.ignore_patterns('run.json'))
    revision = out / 'revision.txt'
    revision.write_text('B4: L3 anchor = velvet\n')
    log = []
    command(log, SB / 'revise.py', 'apply', after / 'reel.json', revision,
            '-o', after / 'reel.json', '--clock', after / 'clock.json')
    command(log, CO / 'adapt.py', after / 'reel.json', '-o', after / 'story.json',
            '--assets-root-local', fixture / 'media')
    command(log, CO / 'compile.py', 'build', after / 'story.json', after / 'timeline.fcpxml',
            '--target', 'fcpxml')
    for state in [before, after]:
        # The XML's absolute paths already name this machine's media. The
        # validator's optional local-root remap is for a different, flat tree.
        command(log, CO / 'compile.py', 'validate', state / 'timeline.fcpxml')
        command(log, CO / 'compile.py', 'report', state / 'timeline.fcpxml', state / 'report.html')
        # Relative asset paths resolve from the media folder; previews embed
        # thumbnails and subsequently open from disk without a server.
        command(log, SB / 'tracks.py', 'tracks', state / 'reel.json', state / 'REEL-TRACKS.html',
                '--clock', state / 'clock.json', cwd=fixture / 'media')
    a, b = read(before / 'reel.json'), read(after / 'reel.json')
    first, last = layer(a), layer(b)
    assert a['clock']['mode'] == b['clock']['mode'] == 'estimated'
    assert first['anchor_text'] == 'nickel' and last['anchor_text'] == 'velvet'
    assert first['asset'] == last['asset'] == 'img07'
    assert first['dur_s'] == last['dur_s'] == .8
    edl_a, edl_b = [fcpxml_edl.parse(str(p / 'timeline.fcpxml')) for p in [before, after]]
    key = ('image', 'img07', '')
    changed, collateral, details = diff(edl_a, edl_b, key)
    event_a = next(e for e in edl_a['events'] if event_key(e) == key)
    event_b = next(e for e in edl_b['events'] if event_key(e) == key)
    # Independently derive the expected cut from the supplied clock and the
    # documented 40%-into-word convention, then quantize absolute endpoints.
    word = next(w for w in read(after / 'clock.json')['words'] if w['i'] == last['anchor_word'])
    start = word['start'] + .4 * (word['end'] - word['start'])
    expected = [round(start * 30), round((start + .8) * 30)]
    assert [event_b['f0'], event_b['f1']] == expected
    assert changed and collateral == 0 and last['chosen_by'] == 'creator'
    command(log, SB / 'build.py', 'build', before / 'notebook.json', before / 'clock.json',
            before / 'bindings.json', '-o', out / 'rebuilt-reel.json',
            '--assets-root', fixture / 'media', '--stubs-dir', out / 'stubs',
            '--preserve', after / 'reel.json')
    rebuilt = layer(read(out / 'rebuilt-reel.json'))
    assert all(rebuilt[k] == last[k] for k in ['asset', 'anchor_text', 'anchor_word',
                                               't0', 't1', 'dur_s', 'chosen_by'])
    summary = dict(fixture='development seed 1, seven beats', timing='estimated; no recorded narration',
                   target='B4.L3', asset='img07', revision=revision.read_text().strip(),
                   old_anchor=first['anchor_text'], new_anchor=last['anchor_text'],
                   before_frames=[event_a['f0'],event_a['f1']], after_frames=expected,
                   fps=30, requested_duration_s=.8, target_correct=True,
                   collateral_identity_or_boundary_changes=collateral,
                   unchanged_other_placements=sum(e['kind'] != 'gap' for e in edl_a['events']) - 1,
                   creator_choice_survives_rebuild=True, clock_unchanged=a['clock'] == b['clock'],
                   limits='Illustrative synthetic demo; no participant or native-editor validation; '
                          'frame identity/boundary metric excludes effects, color and audio quality')
    write(out / 'verification.json', summary)
    write(out / 'commands.json', log)
    write(out / 'sources.json', {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in [Path(__file__), ROOT / 'bench/project.py', ROOT / 'bench/run_real.py',
                    ROOT / 'bench/fcpxml_edl.py', ROOT / 'bench/repair.py',
                    *sorted(SB.glob('*.py')), *sorted(CO.glob('*.py'))]})
    shutil.copyfile(ROOT / 'demo/README.md', out / 'WALKTHROUGH.md')
    (out / 'index.html').write_text(page(summary))
    print(json.dumps(summary, indent=2))


def page(s):
    return f'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>REAL — local correction demo</title>
<style>body{{font:18px/1.5 system-ui,sans-serif;background:#f5f7f9;color:#182735;
max-width:900px;margin:60px auto;padding:0 24px}}h1{{font-size:40px;line-height:1.15}}
.tag{{color:#375b76;font-weight:650}}.cards{{display:flex;gap:20px;flex-wrap:wrap}}
.card{{background:white;border:1px solid #cbd5df;border-radius:12px;padding:24px;flex:1;min-width:260px}}
a{{color:#125d8a}}.button{{display:inline-block;background:#155a82;color:white;padding:10px 18px;
border-radius:6px;text-decoration:none}}table{{border-collapse:collapse;width:100%;background:white}}
th,td{{padding:12px;text-align:left;border-bottom:1px solid #dce3e9}}
.note{{color:#526371;font-size:16px}}code{{background:#e6edf2;padding:3px 6px}}</style>
<p class="tag">REAL / reproducible interaction demo</p>
<h1>Move one image.<br>Keep the other placements.</h1>
<p>In beat 4, the image <b>img07</b> appears on the word <b>nickel</b>.
Move it to <b>velvet</b> and keep its requested 0.8-second duration.</p>
<p class="note">Synthetic benchmark notebook and labelled placeholder media.
Timing is estimated; no narration is recorded. The tracks pages show sampled
thumbnails, not continuous video playback.</p>
<div class="cards"><section class="card"><h2>1. Inspect and correct</h2>
<p>Open the tracks page. Click <b>B4.L3</b>, then type <b>velvet</b> in the anchor field.
Use “copy revision block” to see the requested correction.</p>
<a class="button" href="project/before/REEL-TRACKS.html">Open before</a></section>
<section class="card"><h2>2. Inspect the rebuilt result</h2>
<p>The saved after-state applies <code>{html.escape(s['revision'])}</code> through REAL's scripts.
Typing in the first page alone does not rebuild it.</p>
<a class="button" href="project/after/REEL-TRACKS.html">Open after</a></section></div>
<h2>What changed?</h2><table><tr><th>Property</th><th>Before</th><th>After</th></tr>
<tr><td>Anchor word</td><td>nickel</td><td>velvet</td></tr>
<tr><td>Image / requested duration</td><td>img07 / 0.8 s</td><td>img07 / 0.8 s</td></tr>
<tr><td>Start → end frame (30 fps)</td><td>{s['before_frames'][0]} → {s['before_frames'][1]}</td>
<td>{s['after_frames'][0]} → {s['after_frames'][1]}</td></tr>
<tr><td>Other placement identities and boundaries</td><td colspan="2">{s['unchanged_other_placements']} unchanged</td></tr>
<tr><td>Rebuild with creator choices preserved</td><td colspan="2">The new anchor survives</td></tr></table>
<p><a href="project/before/report.html">Before export report</a> ·
<a href="project/after/report.html">After export report</a> ·
<a href="verification.json">Recorded checks</a> · <a href="WALKTHROUGH.md">Presenter walkthrough</a></p>
<h2>Final Cut files</h2><p><a href="project/before/timeline.fcpxml">Before FCPXML</a> ·
<a href="project/after/timeline.fcpxml">After FCPXML</a></p>
<p class="note">Import is handled by the creator. Keep this local folder in place.
These files have structural validation; this demo has not been imported into Final Cut.
Preservation here concerns placement identity and boundaries, not every effect or visual property.</p></html>'''


if __name__ == '__main__':
    main()
