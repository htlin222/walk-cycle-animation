"""Normative stair and ramp walking from the Camargo et al. (2021) lower-limb biomechanics dataset.

Camargo J, Ramanathan A, Flanagan W, Young A (2021). A comprehensive, open-source dataset of lower limb biomechanics
in multiple conditions of stairs, ramps, and level-ground ambulation and transitions. J Biomech 119:110320.
Data: Mendeley Data 10.17632/fcgm3chfff.1, 10.17632/k9kvm5tn3f.1, 10.17632/jj3r5f9pnf.1 (CC-BY-4.0).
22 adults; stairs at 4 step heights (4, 5, 6, 7 in), ramps at 6 inclines (5.2-18°), OpenSim inverse kinematics and
markers at 200 Hz.

Usage: pip install mat-io                     (reads the MATLAB table objects inside the .mat files)
       python stairs_camargo.py --download   (reads only the needed members out of the three 5-10 GB zips with HTTP
                                              range requests: ik, gcRight / gcLeft, conditions and heel / toe markers of
                                              every stair and ramp trial, plus level walking at comfortable speed;
                                              ≈ 18 MB per subject → analysis/camargo/, not committed)
       python stairs_camargo.py              (→ analysis/data/normative_stairs_camargo.json, data/stairs_page.json)
       python stairs_camargo.py --embed      (pastes data/stairs_page.json into stairs/index.html)

Per mode (stair / ramp × ascent / descent) and condition (step height / incline), averaged within each subject, then
across subjects (left and right cycles pooled, each aligned to its own foot contact; left pelvis curves mirrored):
  hip / knee / ankle sagittal angles (OpenSim IK; ankle relative to the subject's quiet standing at the trial start)
  pelvic tilt / obliquity / rotation, re-expressed in the walking direction (OpenSim's tilt and list are about the lab
  axes, and the subjects walk along the lab's z axis), pelvis height over the cycle, mean tilt vs level walking
  stance fraction, stride time, cadence, stride length and rise per stride (leg = 0.491 x height, Winter thigh + shank)
  stairs: tread depth, riser height and where the heel and toe stood on the tread (foot markers, see stair_geometry())
Foot contact and foot off come from the heel / toe markers (contacts()), not the dataset's gait-event files.
Only steady-state cycles are used (steady()).
"""
import io, json, os, pathlib, re, sys, zipfile, zlib, struct, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np
HERE = pathlib.Path(__file__).parent
R = HERE / 'camargo'
PARTS = ['https://data.mendeley.com/public-files/datasets/fcgm3chfff/files/9c30f2e4-2d39-4d95-b691-1163c927455e/file_downloaded',
         'https://data.mendeley.com/public-files/datasets/k9kvm5tn3f/files/2b976163-2870-458c-816d-30e07f17ad90/file_downloaded',
         'https://data.mendeley.com/public-files/datasets/jj3r5f9pnf/files/2800004c-be9c-40fa-b9bd-50ad3ec1b085/file_downloaded']
INFO = 'https://data.mendeley.com/public-files/datasets/fcgm3chfff/files/d0f204d7-903c-4064-aff6-7080b2b5acb8/file_downloaded'
IK = ['pelvis_tilt', 'pelvis_list', 'pelvis_rotation', 'pelvis_tx', 'pelvis_ty', 'pelvis_tz',
      'hip_flexion_r', 'knee_angle_r', 'ankle_angle_r', 'hip_flexion_l', 'knee_angle_l', 'ankle_angle_l']
MK = [f'{s}_{m}_{a}' for s in 'RL' for m in ('Heel', 'Toe_Tip') for a in 'xyz']
UA = {'User-Agent': 'curl/8'}


# ---------- download: a seekable view of a remote zip, one range request per member ----------
def get(url, a, b):
    req = urllib.request.Request(url, headers={**UA, 'Range': f'bytes={a}-{b - 1}'})
    for k in range(5):
        try: return urllib.request.urlopen(req, timeout=120).read()
        except Exception:
            if k == 4: raise


class Remote(io.RawIOBase):
    def __init__(self, url):
        r = urllib.request.urlopen(urllib.request.Request(url, headers={**UA, 'Range': 'bytes=0-0'}))
        self.url, self.size, self.pos = r.geturl(), int(r.headers['Content-Range'].split('/')[1]), 0
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, o, w=0):
        self.pos = o if w == 0 else self.pos + o if w == 1 else self.size + o; return self.pos
    def readinto(self, buf):
        n = min(len(buf), self.size - self.pos)
        if n <= 0: return 0
        d = get(self.url, self.pos, self.pos + n); buf[:len(d)] = d; self.pos += len(d); return len(d)


def member(url, zi):
    h = get(url, zi.header_offset, zi.header_offset + 30)
    n, m = struct.unpack('<HH', h[26:30])
    a = zi.header_offset + 30 + n + m
    d = get(url, a, a + zi.compress_size)
    return zlib.decompress(d, -15) if zi.compress_type == zipfile.ZIP_DEFLATED else d


def table(raw):
    from matio import load_from_mat     # pip install mat-io: reads MATLAB table objects inside v7 .mat files
    p = R / f'_tmp{os.getpid()}.mat'; p.write_bytes(raw)
    try: return load_from_mat(str(p))
    finally: p.unlink()


def convert(files):
    """one trial's .mat files → one compact .npz (float32 IK and heel / toe markers at 200 Hz from t0, gait events, label runs)"""
    c = table(files['conditions'])
    lab = c['labels']; t0 = float(lab['Header'].iloc[0])
    L = [str(x).strip("[]'") for x in lab['Label']]
    runs = [(L[i], float(lab['Header'].iloc[i])) for i in range(len(L)) if i == 0 or L[i] != L[i - 1]]
    ik = table(files['ik'])['data']
    t = ik['Header'].values; assert np.allclose(np.diff(t), 0.005)
    out = dict(t0=t[0], ik=ik[IK].values.astype(np.float32),
               labels=np.array([r[0] for r in runs]), label_t=np.array([r[1] for r in runs]),
               cond=float(np.ravel(c.get('stairHeight', c.get('rampIncline', [0])))[0]))
    for side in [s for s in ('Right', 'Left') if 'gc' + s in files]:
        g = table(files['gc' + side])['data']; tt = g['Header'].values
        for col, k in (('HeelStrike', 'hs'), ('ToeOff', 'to')):
            out[side[0].lower() + k] = tt[np.where(np.diff(g[col].values) < -50)[0] + 1]
    if 'markers' in files:
        m = table(files['markers'])['data']; assert np.allclose(m['Header'].values, t)
        out['mk'] = np.round(np.nan_to_num(m[MK].values, nan=-32768)).clip(-32768, 32767).astype(np.int16)   # mm
    return out


def download(only=None):
    R.mkdir(exist_ok=True)
    p = R / 'SubjectInfo.mat'
    if not p.exists(): p.write_bytes(urllib.request.urlopen(urllib.request.Request(INFO, headers=UA)).read())
    for url in PARTS:
        rf = Remote(url); z = zipfile.ZipFile(io.BufferedReader(rf, 1 << 20)); url = rf.url     # central directory only
        trials = {}
        for zi in z.infolist():
            q = zi.filename.split('/')
            if len(q) != 5 or q[2] not in ('stair', 'ramp', 'levelground') or not q[4].endswith('.mat'): continue
            if q[3] not in (('ik', 'conditions') if q[2] == 'levelground' else ('ik', 'gcRight', 'gcLeft', 'conditions', 'markers')): continue
            if q[2] == 'levelground' and '_normal_' not in q[4]: continue     # level reference: comfortable speed only
            if only and q[0] not in only: continue
            trials.setdefault((q[0], q[2], q[4][:-4]), {})[q[3]] = zi
        have = lambda k: (R / k[0] / k[1] / (k[2] + '.npz')).exists() and (k[1] == 'levelground' or 'mk' in np.load(R / k[0] / k[1] / (k[2] + '.npz')))
        todo = [(k, v) for k, v in sorted(trials.items()) if not have(k)]
        print(f'{url[-60:]}: {len(trials)} trials, {len(todo)} to fetch')

        def fetch(item):
            (s, mode, name), zis = item
            if not all(k in zis for k in ('ik', 'conditions') + (() if mode == 'levelground' else ('gcRight', 'gcLeft'))): return f'{s} {name}: incomplete'
            raw = {k: member(url, zi) for k, zi in zis.items()}
            return (s, mode, name, raw)
        with ThreadPoolExecutor(8) as ex:
            for r in ex.map(fetch, todo):
                if isinstance(r, str): print(r); continue
                s, mode, name, raw = r
                try: out = convert(raw)
                except Exception as e: print(s, name, 'unreadable:', e); continue
                d = R / s / mode; d.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(d / (name + '.npz'), **out)
                print(s, mode, name)


# ---------- analysis ----------
FS = 200.0
MODES = {('stair', 'ascent'): 'stairascent', ('stair', 'descent'): 'stairdescent',
         ('ramp', 'ascent'): 'rampascent', ('ramp', 'descent'): 'rampdescent'}


def resample(x, a, b, n=101):
    return np.interp(np.linspace(a, b, n), np.arange(len(x)), x)


def subject_info():
    from matio import load_from_mat
    T = load_from_mat(str(R / 'SubjectInfo.mat'))['data']
    return {str(s).strip("[]'"): dict(height=float(h), mass=float(m)) for s, h, m in zip(T['Subject'], T['Height'], T['Weight'])}


def rz(a):
    c, s = np.cos(a), np.sin(a); o, l = np.zeros_like(a), np.ones_like(a)
    return np.stack([np.stack([c, -s, o], -1), np.stack([s, c, o], -1), np.stack([o, o, l], -1)], -2)


def rx(a):
    c, s = np.cos(a), np.sin(a); o, l = np.zeros_like(a), np.ones_like(a)
    return np.stack([np.stack([l, o, o], -1), np.stack([o, c, -s], -1), np.stack([o, s, c], -1)], -2)


def ry(a):
    c, s = np.cos(a), np.sin(a); o, l = np.zeros_like(a), np.ones_like(a)
    return np.stack([np.stack([c, o, s], -1), np.stack([o, l, o], -1), np.stack([-s, o, c], -1)], -2)


def pelvis_local(tilt, lst, rot, heading):
    """OpenSim ground→pelvis is Rz(tilt)·Rx(list)·Ry(rotation) about the LAB axes, and the subjects walk along lab z,
    so the reported 'tilt' is really obliquity there. Re-express in the walking direction (heading about vertical) and
    decompose again: returns anterior tilt, obliquity (right side up) and rotation (right side forward), degrees."""
    d = np.radians
    M = ry(-d(heading)) @ rz(d(tilt)) @ rx(d(lst)) @ ry(d(rot))
    b = np.arcsin(np.clip(M[..., 2, 1], -1, 1)); a = np.arctan2(-M[..., 0, 1], M[..., 1, 1]); c = np.arctan2(-M[..., 2, 0], M[..., 2, 2])
    return -np.degrees(a), -np.degrees(b), np.degrees(c)      # OpenSim tilt + = posterior, list + = right side down


def load(p):
    d = dict(np.load(p)); d['t'] = d['t0'] + np.arange(len(d['ik'])) / FS
    if 'mk' in d: d['mk'] = np.where(d['mk'] == -32768, np.nan, d['mk'].astype(float))
    d['col'] = {k: i for i, k in enumerate(IK)}
    return d


def label_at(d, t):
    return d['labels'][np.clip(np.searchsorted(d['label_t'], t, 'right') - 1, 0, len(d['labels']) - 1)]


def at(d, name, t):
    return np.interp(t, d['t'], d['ik'][:, d['col'][name]])


def contacts(d, tol=10.0):
    """Foot contact and foot off of every stance, from the heel and toe-tip markers. The dataset's gcRight / gcLeft
    events come from heavily smoothed heel-marker speed and fall 50-200 ms after the foot lands (worst in descent, where
    the toes land first). Each of their stances is used as a seed: the heel and toe heights at its middle are the resting
    levels, and the stance is grown both ways while the heel or the toe stays within tol mm of its resting height."""
    out = {}
    for side, j in (('r', 0), ('l', 6)):
        hy, ty = d['mk'][:, j + 1].astype(float), d['mk'][:, j + 4].astype(float)
        ic, fo, ft = [], [], []
        for hs in d[side + 'hs']:
            to = d[side + 'to'][d[side + 'to'] > hs]
            if not len(to) or to[0] - hs > 2.0: continue
            a, b = np.searchsorted(d['t'], hs), np.searchsorted(d['t'], to[0])
            if b - a < 10: continue
            m = slice(a + (b - a) * 3 // 10, a + (b - a) * 7 // 10)
            low = np.minimum(np.abs(hy - np.median(hy[m])), np.abs(ty - np.median(ty[m])))
            mid = (a + b) // 2; k0 = k1 = mid
            if low[mid] > tol or np.isnan(low[mid]): continue
            while k0 > 0 and low[k0 - 1] < tol: k0 -= 1
            while k1 < len(low) - 1 and low[k1 + 1] < tol: k1 += 1
            if ic and d['t'][k0] <= ic[-1]: continue
            ic.append(d['t'][k0]); fo.append(d['t'][k1])
            ft.append(np.concatenate([np.median(d['mk'][m, j:j + 3], 0), np.median(d['mk'][m, j + 3:j + 6], 0)]) / 1000)
        out[side] = (np.array(ic), np.array(fo), np.array(ft).reshape(-1, 6))
    return out


def steady(d, mode, direction, riser):
    """Steady-state cycles on the stairs / ramp. Foot contacts of both feet in time order; a step (one contact to the
    next, either foot) is 'on the terrain' when the foot lands higher (ascent) or lower (descent) than the other foot by
    more than half the expected amount: half a riser on stairs, half of step length x tan(incline) on ramps. Level
    walking, the top landing and turning fail it. A cycle (contact k to contact k+2 of one foot) counts when the steps
    (k-2→k-1) … (k+2→k+3) all pass, i.e. the footholds k-1 … k+2 of both feet in and around the cycle are all on the
    stairs / ramp, not the floor or the landing, and every label over the cycle is the mode or its transitions
    ('walk-stairascent', 'stairascent', 'stairascent-walk')."""
    m = MODES[(mode, direction)]; sgn = 1 if direction == 'ascent' else -1
    ok_lab = {m, 'walk-' + m, m + '-walk'}
    C = contacts(d)
    ev = sorted([(t, s, f) for s in 'rl' for t, f in zip(C[s][0], C[s][2])], key=lambda e: e[0])
    ts = np.array([e[0] for e in ev]); ft = np.array([e[2] for e in ev]).reshape(-1, 6)
    good = []
    for i in range(len(ev) - 1):                    # foot level and position: heel marker at mid-stance
        dy, dh = sgn * (ft[i + 1, 1] - ft[i, 1]), np.hypot(ft[i + 1, 0] - ft[i, 0], ft[i + 1, 2] - ft[i, 2])
        good.append(dy > 0.5 * riser if mode == 'stair' else (dh > 0.3 and dy > 0.5 * dh * np.tan(np.radians(d['cond']))))
    out = []
    for i in range(2, len(ev) - 3):
        j = i + 2                                    # same foot, next heel strike
        if ev[j][1] != ev[i][1] or ev[i + 1][1] == ev[i][1]: continue
        if not all(good[i - 2:j + 1]): continue      # steps (i-2→i-1) … (j→j+1)
        span = d['t'][(d['t'] >= ts[i]) & (d['t'] <= ts[j])]
        labs = set(label_at(d, span))
        if m not in labs or not labs <= ok_lab: continue
        side = ev[i][1]; to = C[side][1]; to = to[(to > ts[i]) & (to < ts[j])]
        if len(to) != 1: continue
        out.append((side, ts[i], ts[j], to[0]))
    return out


def standing_pitch(d):
    """foot pitch (toe up +) of each leg in quiet standing at the trial start, from IK angles in this page's convention:
    thigh = hip flexion - anterior pelvic tilt, shank = thigh - knee flexion, foot = shank + ankle dorsiflexion"""
    if d['labels'][0] != 'idle': return None
    t1 = d['label_t'][1] if len(d['label_t']) > 1 else d['t'][-1]
    k = (d['t'] < t1 - 0.1)
    if k.sum() < 60: return None
    I = d['ik'][k]; c = d['col']
    tilt, _, _ = pelvis_local(I[:, c['pelvis_tilt']], I[:, c['pelvis_list']], I[:, c['pelvis_rotation']], np.median(I[:, c['pelvis_rotation']]))
    return {s: float(np.median(I[:, c['hip_flexion_' + s]] - tilt + I[:, c['knee_angle_' + s]] + I[:, c['ankle_angle_' + s]])) for s in 'rl'}


def cycle(d, side, a, b, to, pitch0, L):
    """one gait cycle → 101-sample curves (right-side convention) + timing / distance"""
    c = d['col']; i0, i1 = (a - d['t0']) * FS, (b - d['t0']) * FS
    g = lambda n: resample(d['ik'][:, c[n]].astype(float), i0, i1)
    rot = np.unwrap(np.radians(d['ik'][:, c['pelvis_rotation']].astype(float)))
    head = np.degrees(resample(rot, i0, i1)).mean()
    tilt, obl, prot = pelvis_local(g('pelvis_tilt'), g('pelvis_list'), np.degrees(resample(rot, i0, i1)), head)
    if side == 'l': obl, prot = -obl, -prot
    ty = g('pelvis_ty'); rise = ty[-1] - ty[0]
    T = b - a
    dx = np.hypot(g('pelvis_tx')[-1] - g('pelvis_tx')[0], g('pelvis_tz')[-1] - g('pelvis_tz')[0])
    return dict(hip_flexion=g('hip_flexion_' + side), knee_flexion=-g('knee_angle_' + side),
                ankle_dorsiflexion=g('ankle_angle_' + side) - pitch0[side],
                pelvic_tilt=tilt, pelvic_obliquity=obl, pelvic_rotation=prot - prot.mean(),
                pelvis_height=(ty - ty[0] - rise * np.linspace(0, 1, 101)) / L,
                stance=(to - a) / T, stride_time=T, stride=dx / L, stride_m=dx, rise=rise / L, rise_m=rise)


def stair_footholds(d):
    """Every stair contact of one trial with its step number: 0 = floor, 1-5 = steps, 6 = top landing. Contacts are
    grouped by heel height (a gap of more than half a riser starts a new step). Returns [(step, direction, heel xyz,
    toe xyz)] in metres, or [] when the trial does not show all seven levels."""
    C = contacts(d); P = []
    for s in 'rl':
        for ic, fo, ft in zip(*C[s]):
            lab = label_at(d, (ic + fo) / 2)
            dirn = 'ascent' if 'ascent' in lab else 'descent' if 'descent' in lab else None
            if dirn: P.append((ft, dirn))
    if not P: return []
    lv = np.sort([p[0][1] for p in P]); r = 0.0254 * d['cond']
    cl = [[lv[0]]]
    for v in lv[1:]:
        if v - cl[-1][-1] > r / 2: cl.append([v])
        else: cl[-1].append(v)
    if len(cl) != 7: return []
    cen = np.array([np.median(c) for c in cl])
    return [(int(np.argmin(np.abs(cen - ft[1]))), dirn, ft[:3], ft[3:]) for ft, dirn in P]


def stair_geometry(F):
    """Stair edges from where feet stood (all subjects, one step height; walking +z = up). Riser k+1 (the vertical face
    in front of tread k going up) can be no closer than the farthest toe tip on tread k going up and the farthest heel
    on tread k going down: it is put at the 98th percentile of both. Returns tread depth, riser height and the heel / toe
    marker positions on the tread in the walking direction (m): heel from the tread's back edge, toe tip past its front
    edge (negative = short of it). Steps 2-4 only, so every foot used has a full step behind and ahead."""
    zs, lv = {}, {}
    for k in range(1, 6):
        up = [f for f in F if f[0] == k and f[1] == 'ascent']; dn = [f for f in F if f[0] == k and f[1] == 'descent']
        zs[k + 1] = max(np.percentile([f[3][2] for f in up], 98), np.percentile([f[2][2] for f in dn], 98))
        lv[k] = np.median([f[2][1] for f in up + dn])
    tread = (zs[6] - zs[2]) / 4; z1 = zs[2] - tread                      # risers 2..6 measured, riser 1 extrapolated
    edge = lambda k: z1 + (k - 1) * tread                               # riser k: front of tread k-1, back of tread k
    rel = {}
    for dirn in ('ascent', 'descent'):        # in the walking direction: tread from its back edge to its front edge
        G = [f for f in F if 2 <= f[0] <= 4 and f[1] == dirn]
        back = (lambda k: edge(k)) if dirn == 'ascent' else (lambda k: edge(k + 1))   # going down, +z is behind
        fwd = 1 if dirn == 'ascent' else -1
        rel[dirn] = dict(heel_from_back=float(np.median([fwd * (f[2][2] - back(f[0])) for f in G])),
                         toe_past_front=float(np.median([fwd * (f[3][2] - back(f[0])) - tread for f in G])))
    return dict(tread=float(tread), riser=float((lv[5] - lv[1]) / 4), feet=rel,
                risers=[float(zs[k] - zs[k - 1]) for k in range(3, 7)])


def level_tilt(d):
    """mean anterior pelvic tilt while walking straight on level ground ('walk' label, comfortable speed)"""
    c = d['col']; v = []
    for k, lab in enumerate(d['labels']):
        if lab != 'walk': continue
        t1 = d['label_t'][k + 1] if k + 1 < len(d['labels']) else d['t'][-1]
        m = (d['t'] >= d['label_t'][k]) & (d['t'] < t1)
        if m.sum() < 200: continue
        I = d['ik'][m].astype(float)
        v.append(pelvis_local(I[:, c['pelvis_tilt']], I[:, c['pelvis_list']], I[:, c['pelvis_rotation']], np.median(I[:, c['pelvis_rotation']]))[0].mean())
    return v


# condition from the trial name: stair_<i>_… = 4-7 in, ramp_<i>_… = 5.2-18°; trials whose recorded value disagrees are dropped
NAMED = {'stair': [4, 5, 6, 7], 'ramp': [5.2, 7.8, 9.2, 11, 12.4, 18]}


def mean_curves(cycles, keys):
    return {k: np.mean([c[k] for c in cycles], 0) for k in keys}


CURVES = ['hip_flexion', 'knee_flexion', 'ankle_dorsiflexion', 'pelvic_tilt', 'pelvic_obliquity', 'pelvic_rotation', 'pelvis_height']
SCALARS = ['stance', 'stride_time', 'stride', 'stride_m', 'rise', 'rise_m']


def main():
    info = subject_info()
    files = sorted(R.glob('AB*/*/*.npz'))
    # quiet standing at the start of each trial: foot pitch → ankle offset, per subject
    st = {}
    for p in files:
        s = standing_pitch(load(p))
        if s: st.setdefault(p.parts[-3], []).append(s)
    pitch0 = {k: {side: float(np.median([x[side] for x in v])) for side in 'rl'} for k, v in st.items()}
    level = {}
    for p in files:
        if p.parts[-2] == 'levelground': level.setdefault(p.parts[-3], []).extend(level_tilt(load(p)))
    level = {k: float(np.mean(v)) for k, v in level.items() if v}
    per = {}; feet = {}; dropped = []
    for p in files:
        subj, mode = p.parts[-3], p.parts[-2]
        if mode == 'levelground' or subj not in pitch0 or subj not in info: continue
        d = load(p); L = 0.491 * info[subj]['height']
        if 'mk' not in d: continue
        cond = NAMED[mode][int(p.name.split('_')[1]) - 1]
        if abs(d['cond'] - cond) > 0.3: dropped.append(p.name); continue
        if mode == 'stair': feet.setdefault(cond, []).extend(stair_footholds(d))
        for direction in ('ascent', 'descent'):
            for side, a, b, to in steady(d, mode, direction, 0.0254 * cond):
                c = cycle(d, side, a, b, to, pitch0[subj], L)
                per.setdefault((mode, direction, cond), {}).setdefault(subj, []).append(c)
    out = {}
    for (mode, direction, cond), S in sorted(per.items()):
        S = {k: v for k, v in S.items() if len(v) >= 2}                       # at least two cycles per subject
        subj_mean = {k: {**mean_curves(v, CURVES), **{q: np.mean([c[q] for c in v]) for q in SCALARS}} for k, v in S.items()}
        M = {k: np.mean([m[k] for m in subj_mean.values()], 0) for k in CURVES + SCALARS}
        SD = {k: np.std([m[k] for m in subj_mean.values()], 0) for k in ('hip_flexion', 'knee_flexion', 'ankle_dorsiflexion')}
        L_mean = 0.491 * np.mean([info[k]['height'] for k in S])
        T = M['stride_time']
        res = dict(mode=mode, direction=direction, condition=cond, unit='in' if mode == 'stair' else 'deg',
                   subjects=len(S), cycles=int(sum(len(v) for v in S.values())),
                   **{k: M[k] for k in CURVES}, **{k + '_sd': SD[k] for k in SD},
                   stance=float(M['stance']), stance_sd=float(np.std([m['stance'] for m in subj_mean.values()])),
                   stride_time=float(T), cadence=float(120 / T), stride=float(M['stride']), stride_m=float(M['stride_m']),
                   rise=float(M['rise']), rise_m=float(M['rise_m']), speed=float(M['stride_m'] / T), leg_m=float(L_mean),
                   pelvis_travel=float(np.ptp(M['pelvis_height'])),
                   tilt_vs_level=float(np.mean([subj_mean[k]['pelvic_tilt'].mean() - level[k] for k in S if k in level])))
        if mode == 'stair':
            g = stair_geometry(feet[cond]); res['geometry'] = g
        key = f'{mode}_{direction}_{cond:g}'
        out[key] = {k: ([round(float(x), 3) for x in v] if isinstance(v, np.ndarray) else round(v, 4) if isinstance(v, float) else v) for k, v in res.items()}
        r = out[key]
        print(f"{key:22s} subj={r['subjects']:2d} cyc={r['cycles']:3d} stance={r['stance']*100:.1f}% T={T:.2f}s cad={r['cadence']:.0f} "
              f"stride={r['stride_m']:.2f} m ({r['stride']:.2f} L) rise={r['rise_m']*100:.1f} cm speed={r['speed']:.2f} "
              f"pelvis {r['pelvis_travel']*L_mean*100:.1f} cm tilt {np.mean(r['pelvic_tilt']):.1f} ({r['tilt_vs_level']:+.1f} vs level)  hip {min(r['hip_flexion']):.0f}..{max(r['hip_flexion']):.0f}  "
              f"knee {min(r['knee_flexion']):.0f}..{max(r['knee_flexion']):.0f}  ankle {min(r['ankle_dorsiflexion']):.0f}..{max(r['ankle_dorsiflexion']):.0f}"
              + (f"  tread {g['tread']*100:.1f} riser {g['riser']*100:.1f} cm  feet {g['feet']}" if mode == 'stair' else ''))
    print('level-ground pelvic tilt %.1f° (%d subjects); dropped (recorded condition ≠ trial name): %s' % (np.mean(list(level.values())), len(level), dropped))
    out['_standing'] = dict(subjects=len(pitch0), foot_pitch_median=round(float(np.median([v[s] for v in pitch0.values() for s in 'rl'])), 2))
    json.dump(out, open(HERE / 'data' / 'normative_stairs_camargo.json', 'w'))
    page_data(out)


def page_data(out):
    """compact copy for stairs/index.html (100 samples, leg-length units) → analysis/data/stairs_page.json.
    Upper body: the walk page's neutral CMU curves (data/styles.json, clip 104_02); the whole trunk leans by the
    measured change in pelvic tilt from level walking, since trunk and pelvis tilt together on slopes (Leroux 2002)."""
    up = json.load(open(HERE / 'data' / 'styles.json'))['neutral']
    P = {}
    for k, r in out.items():
        if k.startswith('_'): continue
        L = r['leg_m']
        e = dict(mode=r['mode'], dir=r['direction'], cond=r['condition'], subjects=r['subjects'], cycles=r['cycles'],
                 stance=r['stance'], cad=round(r['cadence'], 1), stride=r['stride'], rise=r['rise'], leg_m=L,
                 lean=round(r['tilt_vs_level'], 2), legs={c: r[c][:100] for c in CURVES[:6]})
        if r['mode'] == 'stair':
            g = r['geometry']; f = g['feet'][r['direction']]
            # the ball of the foot (73.5 % of the way from heel to toe, as on the page's shoe) as a fraction of the tread:
            # the drawn shoe is longer than the subjects' and the drawn tread follows the drawn stride, so the load-bearing
            # point is placed proportionally rather than copying heel or toe distances
            m = g['tread'] + f['toe_past_front'] - f['heel_from_back']
            e.update(tread_m=round(g['tread'], 4), riser_m=round(g['riser'], 4),
                     heel_back=round(f['heel_from_back'] / L, 4), toe_front=round(f['toe_past_front'] / L, 4),
                     ball_frac=round((f['heel_from_back'] + 0.735 * m) / g['tread'], 4))
        P[k] = e
    P['_upper'] = dict(clip=up['clip'], curves=up['curves'])
    json.dump(P, open(HERE / 'data' / 'stairs_page.json', 'w'), separators=(',', ':'))


def embed():
    """paste data/stairs_page.json into stairs/index.html (the line starting 'const STAIRS = ')"""
    page = HERE.parent / 'stairs' / 'index.html'
    src = page.read_text().split('\n'); js = (HERE / 'data' / 'stairs_page.json').read_text()
    i = next(i for i, l in enumerate(src) if l.startswith('const STAIRS = '))
    src[i] = 'const STAIRS = ' + js + ';'
    page.write_text('\n'.join(src)); print('embedded', len(js), 'bytes')


if __name__ == '__main__':
    if '--download' in sys.argv: download([a for a in sys.argv[2:] if a.startswith('AB')] or None)
    elif '--embed' in sys.argv: embed()
    else: main()
