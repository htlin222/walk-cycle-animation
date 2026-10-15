"""Build the per-style upper-body curves embedded in index.html.

Input : analysis/data/cmu_sagittal_curves.json  (output of analyze.py on CMU BVH clips)
        analysis/data/normative_gait_wbds.json  (clinical normative gait, Fukuchi et al. 2018 via PhysioGaitNorm)
Output: analysis/data/styles.json

Each clip is phase-aligned to the clinical thigh curve (cross-correlation), Fourier-smoothed (8 harmonics),
and stride / cadence / pelvic bounce are the recording's own measured values (in leg lengths).
"""
import json, pathlib, numpy as np
D = pathlib.Path(__file__).parent / 'data'
C = json.load(open(D / 'cmu_sagittal_curves.json'))
N = json.load(open(D / 'normative_gait_wbds.json'))
norm_thigh = np.array(N['hip_flexion'][:100]) - np.array(N['pelvic_tilt'][:100])

def four(x, K=8):
    X = np.fft.rfft(x); X[K + 1:] = 0; return np.fft.irfft(X, len(x))

STY = {'neutral': ('104_02', None), 'happy': ('82_12', None), 'sad': ('82_10', '82_12')}
STATS = {'neutral': dict(stride=1.44, cad=96, bounce=0.033),
         'happy':   dict(stride=1.78, cad=117, bounce=0.047),
         'sad':     dict(stride=1.50, cad=101, bounce=0.025)}
out = {}
for s, (clip, headref) in STY.items():
    c = {k: np.array(v) for k, v in C[clip].items()}
    best = max(range(100), key=lambda k: np.corrcoef(np.roll(c['thigh'], -k), norm_thigh)[0, 1])
    r = lambda x: four(np.roll(x, -best))
    ref = np.mean(C[headref]['head']) if headref else np.mean(c['head'])
    o = dict(lumbar=r(c['lumbar'] - c['lumbar'].mean()), thorax=r(c['thorax']), head=r(c['head']) - ref,
             uarm=r(c['uarm']), farm=r(c['farm']), shx=r(c['sh_x'] - c['sh_x'].mean()),
             shy=r(c['sh_y'] - c['sh_y'].mean()), throt=r(c['throt'] - c['throt'].mean()))
    out[s] = dict(curves={k: [round(float(x), 3) for x in v] for k, v in o.items()}, **STATS[s], clip=clip)
    print(s, clip, 'phase shift', best)
json.dump(out, open(D / 'styles.json', 'w'))
