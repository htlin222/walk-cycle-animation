"""Normative running cycle from the Running Biomechanics Data Set (RBDS).

Fukuchi RK, Fukuchi CA, Duarte M (2017). A public data set of running biomechanics and the effects of running
speed on lower extremity kinematics and kinetics. PeerJ 5:e3298. figshare 10.6084/m9.figshare.4543435 (CC-BY-4.0).
Treadmill running at 2.5, 3.5 and 4.5 m/s; markers 150 Hz, vertical ground reaction force 300 Hz.

Usage: python run_rbds.py            (files in analysis/rbds/: *processed.txt, *markers.txt, *forces.txt, *static.txt, RBDSinfo.txt)
       download them with:  python run_rbds.py --download
Output: analysis/data/normative_run_rbds.json

Per speed, averaged over runners (right and left sides pooled, each aligned to its own foot strike):
  hip / knee / ankle sagittal angles (Visual3D *processed.txt, 101 samples, foot strike = 0 %)
  stance fraction, fore-aft and vertical ground reaction force (N/kg, *processed.txt)
  pelvic tilt / obliquity / rotation and pelvis height (ASIS / PSIS markers, cut at right foot strikes from the force plate;
  tilt is relative to the runner's standing trial)
  stride time, stride length and vertical oscillation in leg lengths (leg = 0.491 x height, Winter thigh + shank)
"""
import numpy as np, json, csv, pathlib, sys, re, urllib.request
HERE = pathlib.Path(__file__).parent
R = HERE / 'rbds'
SPEEDS = {'25': 2.5, '35': 3.5, '45': 4.5}
FS_MK, FS_F = 150.0, 300.0


def download():
    R.mkdir(exist_ok=True)
    meta = json.load(urllib.request.urlopen('https://api.figshare.com/v2/articles/4543435'))
    for f in meta['files']:
        n = f['name']
        if re.search(r'(processed|markers|forces|static)\.txt$', n) or n == 'RBDSinfo.txt':
            p = R / n
            if not p.exists(): urllib.request.urlretrieve(f['download_url'], p); print(n)


def load(path):
    head = open(path).readline().rstrip('\n').split('\t')
    return {h: i for i, h in enumerate(head)}, np.genfromtxt(path, skip_header=1, delimiter='\t')


def resample(x, a, b, n=101):
    return np.interp(np.linspace(a, b, n), np.arange(len(x)), x)


def subject_info():
    rows = list(csv.DictReader(open(R / 'RBDSinfo.txt'), delimiter='\t'))
    info = {}
    for r in rows:
        s = int(r['Subject'])
        info[s] = dict(height=float(r['Height']) / 100, mass=float(r['Mass']),
                       fsi={k: r.get('RFSI' + k, '') for k in SPEEDS})
    return info


def processed(s, sp):
    p = R / f'RBDS{s:03d}processed.txt'
    if not p.exists(): return None
    H, X = load(p)
    if f'RhipAngZ{sp}' not in H: return None
    out = {}
    for side in 'RL':
        c = {k: X[:, H[f'{side}{j}AngZ{sp}']] for k, j in (('hip', 'hip'), ('knee', 'knee'), ('ankle', 'ankle'))}
        if any(np.isnan(v).any() for v in c.values()): return None
        grf = X[:, H[f'{side}grfY{sp}']]
        nan = np.where(np.isnan(grf))[0]
        c['stance'] = (nan[0] if len(nan) else 100) / 100
        c['grf_ap'] = np.nan_to_num(X[:, H[f'{side}grfX{sp}']])         # N/kg, forward +, zero in the air
        c['grf_v'] = np.nan_to_num(grf)
        out[side] = c
    return out


def static_tilt(s):
    H, M = load(R / f'RBDS{s:03d}static.txt')
    g = lambda n: M[:, [H[n + 'X'], H[n + 'Y']]]
    a, p = (g('R.ASIS') + g('L.ASIS')) / 2, (g('R.PSIS') + g('L.PSIS')) / 2
    return float(np.nanmean(np.degrees(np.arctan2(p[:, 1] - a[:, 1], a[:, 0] - p[:, 0]))))


def markers(s, sp, L):
    pm, pf = R / f'RBDS{s:03d}runT{sp}markers.txt', R / f'RBDS{s:03d}runT{sp}forces.txt'
    if not (pm.exists() and pf.exists()): return None
    H, M = load(pm); _, F = load(pf)
    for j in range(M.shape[1]):                                   # fill short marker dropouts
        bad = np.isnan(M[:, j])
        if bad.all(): return None
        if bad.any(): M[bad, j] = np.interp(np.where(bad)[0], np.where(~bad)[0], M[~bad, j])
    g = lambda n: M[:, [H[n + 'X'], H[n + 'Y'], H[n + 'Z']]]
    rA, lA, rP, lP = g('R.ASIS'), g('L.ASIS'), g('R.PSIS'), g('L.PSIS')
    asis, psis = (rA + lA) / 2, (rP + lP) / 2
    # pelvis frame in the lab: X forward, Y up, Z right
    tilt = np.degrees(np.arctan2(psis[:, 1] - asis[:, 1], asis[:, 0] - psis[:, 0]))       # anterior +
    # relative to the runner's standing trial; run/index.html adds a +6° thigh-reference calibration (README, 'Thigh reference')
    tilt -= static_tilt(s)
    obl = np.degrees(np.arctan2(rA[:, 1] - lA[:, 1], np.abs(rA[:, 2] - lA[:, 2])))          # right side up +
    rot = np.degrees(np.arctan2(rA[:, 0] - lA[:, 0], np.abs(rA[:, 2] - lA[:, 2])))          # right side forward +
    pel_y = (rA[:, 1] + lA[:, 1] + rP[:, 1] + lP[:, 1]) / 4 / 1000
    # foot strikes: vertical force rising through 50 N; side = whichever heel is further forward
    fy = F[:, 2]; c = fy > 50                          # contact = vertical force above 50 N,
    k = int(0.04 * FS_F)                                # ignoring dropouts shorter than 40 ms
    for i in np.where(c[1:] < c[:-1])[0] + 1:
        j = i + np.argmax(c[i:i + k]) if c[i:i + k].any() else i
        c[i:j] = True
    on = np.where(c[1:] > c[:-1])[0] + 1; off = np.where(c[1:] < c[:-1])[0] + 1
    rh, lh = g('R.Heel.Bottom'), g('L.Heel.Bottom')
    strikes = []
    for i in on:
        k = int(round(i * FS_MK / FS_F))
        if 2 <= k < len(M) - 2: strikes.append((k, 'R' if rh[k, 0] > lh[k, 0] else 'L', i))
    # step time from every contact (side-independent); strides R→L→R must be two steps long
    step = np.median(np.diff([k for k, _, _ in strikes])) / FS_MK
    ok = [(a[0], c[0]) for a, b, c in zip(strikes, strikes[1:], strikes[2:])
          if (a[1], b[1], c[1]) == ('R', 'L', 'R') and abs((c[0] - a[0]) / FS_MK - 2 * step) < 0.08 * step]
    ct = []
    for i in on:
        j = off[off > i]
        if len(j) and (j[0] - i) / FS_F < 0.5: ct.append((j[0] - i) / FS_F)
    if len(ok) < 5: return None
    cyc = lambda x: np.mean([resample(x, a, b) for a, b in ok], 0)
    Ts = np.array([(b - a) / FS_MK for a, b in ok])
    py = cyc(pel_y)
    return dict(stride_time=Ts.mean(), contact_time=np.median(ct), tilt=cyc(tilt), obl=cyc(obl), rot=cyc(rot),
                pel_y=(py - py.mean()) / L, vo=np.ptp(py) / L, vo_m=np.ptp(py), n=len(ok))


def main():
    info = subject_info()
    out = {}
    for sp, v in SPEEDS.items():
        J = {k: [] for k in ('hip', 'knee', 'ankle', 'grf_ap', 'grf_v')}; st = []; MK = []; fsi = []
        for s in sorted(info):
            L = 0.491 * info[s]['height']
            P = processed(s, sp)
            if P is None: continue
            for side in 'RL':
                for k in J: J[k].append(P[side][k])
                st.append(P[side]['stance'])
            m = markers(s, sp, L)
            if m: MK.append(m)
            fsi.append(info[s]['fsi'][sp])
        n_sub = len(J['hip']) // 2
        mean = {k: np.mean(J[k], 0) for k in J}
        sd = {k: np.std(J[k], 0) for k in J}
        st_t = np.mean([m['stride_time'] for m in MK])
        L_mean = 0.491 * np.mean([info[s]['height'] for s in info])
        res = dict(
            speed=v, runners=n_sub, runners_markers=len(MK),
            hip_flexion=mean['hip'], knee_flexion=mean['knee'], ankle_dorsiflexion=mean['ankle'],
            grf_ap=mean['grf_ap'], grf_v=mean['grf_v'],
            hip_sd=sd['hip'], knee_sd=sd['knee'], ankle_sd=sd['ankle'],
            pelvic_tilt=np.mean([m['tilt'] for m in MK], 0), pelvic_obliquity=np.mean([m['obl'] for m in MK], 0),
            pelvic_rotation=np.mean([m['rot'] for m in MK], 0), pelvis_height=np.mean([m['pel_y'] for m in MK], 0),
            stance=float(np.mean(st)), stance_sd=float(np.std(st)),
            stride_time=float(st_t), cadence=float(120 / st_t),
            contact_time=float(np.mean([m['contact_time'] for m in MK])),
            stride=float(v * st_t / L_mean), leg_m=float(L_mean),
            vertical_oscillation=float(np.mean([m['vo'] for m in MK])), vertical_oscillation_m=float(np.mean([m['vo_m'] for m in MK])),
            foot_strike={k: fsi.count(k) for k in sorted(set(fsi)) if k},
        )
        out[sp] = {k: ([round(float(x), 3) for x in val] if isinstance(val, np.ndarray) else val) for k, val in res.items()}
        print(f"{v} m/s  runners={n_sub} (markers {len(MK)})  stance={res['stance']*100:.1f}%  contact={res['contact_time']*1000:.0f} ms  "
              f"stride T={st_t:.3f}s cadence={res['cadence']:.0f} spm  stride={res['stride']:.2f} L  VO={res['vertical_oscillation_m']*100:.1f} cm "
              f"({res['vertical_oscillation']:.3f} L)  tilt={np.mean(res['pelvic_tilt']):.1f}±{np.ptp(res['pelvic_tilt'])/2:.1f}  "
              f"hip {mean['hip'].min():.0f}..{mean['hip'].max():.0f}  knee {mean['knee'].min():.0f}..{mean['knee'].max():.0f}  "
              f"ankle {mean['ankle'].min():.0f}..{mean['ankle'].max():.0f}  FSI {res['foot_strike']}")
    json.dump(out, open(HERE / 'data' / 'normative_run_rbds.json', 'w'))


if __name__ == '__main__':
    if '--download' in sys.argv: download()
    main()
