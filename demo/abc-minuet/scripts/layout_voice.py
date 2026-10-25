"""Lay the per-cell voice takes on one track at the estimated clock's narration starts, keeping the planned gaps
(lead-ins and demo holds) between cells, so the measured alignment lands on the same structure the plan has."""
import glob, json, subprocess
import os; os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # run from the demo folder
C = json.load(open('storyboard/clock-est.json'))
words, beats = C['words'], C['beats']
TAKES = sorted(glob.glob("source/narration/vo-*.mp3"))   # one take per narrated cell, in notebook order
cells = []
for b in beats:
    if b['wordless']:
        continue
    if cells and cells[-1][0] == b['name']:
        cells[-1][2] = b['w1']
    else:
        cells.append([b['name'], b['w0'], b['w1']])

def dur(p):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))

t, plan = words[cells[0][1]]['start'], []
assert len(TAKES) == len(cells), (len(TAKES), [c[0] for c in cells])
for k, (name, w0, w1) in enumerate(cells):
    f = TAKES[k]
    d = dur(f)
    plan.append({"cell": name, "take": f, "at_s": round(t, 3), "dur_s": round(d, 3)})
    if k + 1 < len(cells):
        t += d + max(words[cells[k + 1][1]]['start'] - words[w1]['end'], 0.25)
inputs, flt = [], []
for i, p in enumerate(plan):
    inputs += ['-i', p['take']]
    flt.append(f"[{i}:a]aresample=48000,pan=mono|c0=c0,adelay={int(round(p['at_s'] * 1000))}[a{i}]")
flt.append(''.join(f'[a{i}]' for i in range(len(plan))) + f"amix=inputs={len(plan)}:normalize=0[o]")
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', *inputs, '-filter_complex', ';'.join(flt), '-map', '[o]', 'storyboard/voice-master.wav'], check=True)
json.dump(plan, open('storyboard/voice-layout.json', 'w'), indent=1)
for p in plan:
    print("  %-9s at %6.2fs  %5.2fs" % (p['cell'], p['at_s'], p['dur_s']))
