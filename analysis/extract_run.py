"""Build the running data embedded in run/index.html.

Input : analysis/data/normative_run_rbds.json  (output of run_rbds.py: legs, pelvis, timing per speed)
        CMU running clips in analysis/bvh/ (subject 9: 09_01-06, 09_11; subject 35: 35_18, 35_22, 35_25, 35_26)
Output: analysis/data/cmu_run_curves.json, analysis/data/run_styles.json

Upper body: every clean CMU running cycle is phase-aligned to the RBDS 3.5 m/s thigh curve (cross-correlation),
averaged within each runner, then across the two runners, and Fourier-smoothed (8 harmonics).
Arm swing grows with leg swing (the arms cancel the legs' angular momentum about the vertical axis; Hinrichs 1987),
so the upper-arm swing is scaled about its mean by RBDS thigh range at that speed / CMU thigh range.
"""
import json, pathlib, numpy as np
from analyze import analyze
HERE = pathlib.Path(__file__).parent; D = HERE / 'data'
N = json.load(open(D / 'normative_run_rbds.json'))
CLIPS = {'09': ['09_01', '09_02', '09_03', '09_04', '09_05', '09_06', '09_11'], '35': ['35_18', '35_22', '35_25', '35_26']}
NAMES = {'25': 'jog', '35': 'run', '45': 'fast'}
thigh = lambda sp: np.array(N[sp]['hip_flexion'][:100]) - np.array(N[sp]['pelvic_tilt'][:100])
ref = thigh('35')


def four(x, K=8):
    X = np.fft.rfft(x); X[K + 1:] = 0; return np.fft.irfft(X, len(x))


raw, per_subject, stats = {}, {}, []
for subj, clips in CLIPS.items():
    acc = []
    for n in clips:
        r = analyze(str(HERE / 'bvh' / f'{n}.bvh'), 0.45, 1.1)
        if r is None: continue
        s, c, L = r
        c = {k: np.array(v) for k, v in c.items()}
        best = max(range(100), key=lambda k: np.corrcoef(np.roll(c['thigh'], -k), ref)[0, 1])
        rr = np.corrcoef(np.roll(c['thigh'], -best), ref)[0, 1]
        raw[n] = {k: [round(float(x), 3) for x in v] for k, v in c.items()}
        acc.append({k: np.roll(v, -best) for k, v in c.items()})
        stats.append(dict(clip=n, r=round(float(rr), 3), speed=round(s['speed'], 2), cadence=round(s['cadence']), elbow=round(s['elbow_mean'])))
        print(f"{n}  r={rr:.3f}  {s['speed']:.2f} L/s  {s['cadence']:.0f} spm  thigh ROM {np.ptp(c['thigh']):.0f}°  elbow {s['elbow_mean']:.0f}°  trunk {np.mean(c['thorax']):.1f}°")
    per_subject[subj] = {k: np.mean([a[k] for a in acc], 0) for k in acc[0]}
json.dump(raw, open(D / 'cmu_run_curves.json', 'w'))
C = {k: np.mean([per_subject[s][k] for s in per_subject], 0) for k in per_subject['09']}
cmu_thigh_rom = np.ptp(C['thigh'])

out = {}
for sp, name in NAMES.items():
    n = N[sp]
    k_arm = np.ptp(thigh(sp)) / cmu_thigh_rom
    ua = four(C['uarm']); fa = four(C['farm']); um = ua.mean()
    ua_s = um + k_arm * (ua - um)
    up = dict(lumbar=four(C['lumbar'] - C['lumbar'].mean()), thorax=four(C['thorax']), head=four(C['head'] - C['head'].mean()),
              uarm=ua_s, farm=ua_s + (fa - ua),                                   # keep the recorded elbow angle
              shx=four(C['sh_x'] - C['sh_x'].mean()), shy=four(C['sh_y'] - C['sh_y'].mean()),
              throt=four(C['throt'] - C['throt'].mean()))
    legs = {k: n[k][:100] for k in ('hip_flexion', 'knee_flexion', 'ankle_dorsiflexion', 'pelvic_tilt', 'pelvic_rotation', 'pelvic_obliquity', 'pelvis_height', 'grf_ap')}
    out[name] = dict(speed=n['speed'], stance=round(n['stance'], 4), stride=round(n['stride'], 3), cad=round(n['cadence'], 1), stride_time=round(n['stride_time'], 4), leg_m=round(n['leg_m'], 4),
                     contact=round(n['contact_time'], 3), vo=round(n['vertical_oscillation'], 4), vo_m=round(n['vertical_oscillation_m'], 4),
                     runners=n['runners'], foot_strike=n['foot_strike'], arm_scale=round(float(k_arm), 3),
                     legs=legs, curves={k: [round(float(x), 3) for x in v] for k, v in up.items()})
    print(f"{name}: {n['speed']} m/s  stance {n['stance']*100:.1f}%  stride {n['stride']:.2f} L  {n['cadence']:.0f} spm  arm scale {k_arm:.2f}")
json.dump(out, open(D / 'run_styles.json', 'w'))
print('upper-body mean trunk lean %.1f°, elbow %.0f°' % (C['thorax'].mean(), (C['farm'] - C['uarm']).mean()))
