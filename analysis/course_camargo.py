"""Transition strides and level walking for the stairs/ page's terrain course, from Camargo et al. (2021).

Input : analysis/camargo/ (python stairs_camargo.py --download), analysis/data/normative_stairs_camargo.json
Output: analysis/data/course_camargo.json  (embedded in stairs/index.html by: python course_camargo.py --embed)

Every foot contact of a stair or ramp trial is typed by the level it lands on: F = bottom floor, M = a step / the ramp,
T = top landing. A leg cycle (own contact k to own contact k+2) is named by the footholds k-1 … k+2, e.g. up:MMMT is the
cycle that leaves the second-to-last step and lands on the landing, with the other foot on the last step. Each swing
(own foot off → own contact) is also named on its own by (own previous foothold, other foot's foothold, landing
foothold), e.g. up:sw:FFM = the first foot from the floor onto the first step.

What the dataset can and cannot give (see the README): every stair and ramp trial starts from standing one step in
front of the first riser and ends by stopping one step after the last one, so the strides that enter the stairs / ramp
from the floor, and the ones that leave them onto the floor, are gait initiation and termination, not walking. Clean
whole-cycle transitions exist only at the top: ascent onto the landing (up:MMMT, up:MMTT, up:MTTT), and the second
cycle into a descent (dn:TMMM) and the last cycle out of it (dn:MMMF). For the entries the measured swing onto the first
(and second) step is used (up:sw:FFM, up:sw:FMM, dn:sw:TTM, dn:sw:TMM), joined to a level-walking stance.

Level walking: levelground trials at comfortable speed, 'walk' label only (straight walking, no turns, no start / stop).
Curves follow stairs_camargo.cycle(): right-limb convention, left cycles mirrored, ankle zeroed in quiet standing,
pelvis angles in the walking direction; subject means, then the mean across subjects (at least 2 cycles per subject).
"""
import json, pathlib, sys
import numpy as np
from stairs_camargo import (R, HERE, FS, load, contacts, label_at, pelvis_local, standing_pitch, subject_info, resample,
                            stair_footholds, stair_geometry, NAMED, cycle, CURVES)
SWN = 51            # samples per swing

# Obstacle (hurdle) crossing: no open dataset with obstacle geometry was found, so it is modelled from the literature.
# All distances in leg lengths (leg = 0.491 x height).
#  Chardon M et al. (2024) Sensors 24(23):7867, doi:10.3390/s24237867, table 1: 28 young adults of normal BMI (height 1.76 m,
#    leg 0.864 m), barefoot, 15 cm high x 2 cm thick obstacle: leading toe clearance 10.1 cm; trailing foot (2nd metatarsal
#    head) 42.4 cm before the obstacle; leading heel 25.1 cm after it; trailing heel 90.0 cm after it.
#  Lu S-H et al. (2022) Front Aging Neurosci 14:950411, doi:10.3389/fnagi.2022.950411, tables 2 and 4-5: 12 healthy older
#    adults (controls), obstacles of 10 / 20 / 30 % of leg length: leading toe clearance 18.6 / 19.5 / 21.4 % LL (no height
#    effect), trailing 18.0 / 20.0 / 23.0 % LL (increases with height); foot-obstacle distances do not change with height;
#    joint angles when the toe is above the obstacle: leading hip 58.3 / 67.2 / 74.5 deg, knee 90.3 / 106.7 / 118.4 deg;
#    trailing hip 26.5 / 31.8 / 35.0 deg, knee 98.7 / 114.9 / 129.0 deg.
# Model: young-adult clearance and placement (Chardon), held across heights as Lu found; trailing clearance = leading x
# Lu's trailing / leading ratio at that height; crossing hip and knee flexion from Lu.
_LEGC = 0.491 * 1.76
OBSTACLE = dict(heights=[0.1, 0.2, 0.3], lead_clearance=0.101 / _LEGC,
                trail_clearance=[0.101 / _LEGC * r for r in (18.0 / 18.6, 20.0 / 19.5, 23.0 / 21.4)],
                trail_ball_before=0.424 / _LEGC, lead_heel_after=0.251 / _LEGC, trail_heel_after=0.900 / _LEGC,
                thickness=0.02 / _LEGC, lead=dict(hip=[58.3, 67.2, 74.5], knee=[90.3, 106.7, 118.4]),
                trail=dict(hip=[26.5, 31.8, 35.0], knee=[98.7, 114.9, 129.0]))
# what the page uses (stairs 6 in, ramp 9.2 deg)
PAGE_FULL = [f'stair_6_{k}' for k in ('up:FMMM', 'up:MMMM', 'up:MMMT', 'up:MMTT', 'dn:TMMM', 'dn:MMMM', 'dn:MMMF', 'dn:MMFF')] + \
            [f'ramp_9.2_{k}' for k in ('up:FMMM', 'up:MMMM', 'up:MMMT', 'up:MMTT', 'dn:TMMM', 'dn:MMMM', 'dn:MMMF', 'dn:MMFF')]
PAGE_SWING = [f'stair_6_{k}' for k in ('up:sw:FFM', 'up:sw:FMM', 'up:sw:MTT', 'dn:sw:TTM', 'dn:sw:TMM', 'dn:sw:MFF')] + \
             [f'ramp_9.2_{k}' for k in ('up:sw:FFM', 'up:sw:FMM', 'dn:sw:TTM', 'dn:sw:TMM')]


def foot_type(level, lo, hi, tol):
    return 'F' if abs(level - lo) < tol else 'T' if abs(level - hi) < tol else 'M'


def swing_curves(d, side, a, b, pitch0):
    """joint angles over one swing (own foot off a → own contact b), SWN samples, same conventions as cycle()"""
    c = d['col']; i0, i1 = (a - d['t0']) * FS, (b - d['t0']) * FS
    g = lambda n: resample(d['ik'][:, c[n]].astype(float), i0, i1, SWN)
    rot = np.unwrap(np.radians(d['ik'][:, c['pelvis_rotation']].astype(float)))
    head = np.degrees(resample(rot, i0, i1, SWN)).mean()
    tilt, obl, prot = pelvis_local(g('pelvis_tilt'), g('pelvis_list'), np.degrees(resample(rot, i0, i1, SWN)), head)
    if side == 'l': obl, prot = -obl, -prot
    return dict(hip_flexion=g('hip_flexion_' + side), knee_flexion=-g('knee_angle_' + side),
                ankle_dorsiflexion=g('ankle_angle_' + side) - pitch0[side], pelvic_tilt=tilt, pelvic_obliquity=obl,
                pelvic_rotation=prot, duration=b - a)


def standing_off(d, side, ic):
    """foot off of the first step from quiet standing: last moment before contact ic when the heel or toe was still
    within 10 mm of its standing height (first 0.3 s of the trial)"""
    j = 0 if side == 'r' else 6
    hy, ty = d['mk'][:, j + 1], d['mk'][:, j + 4]
    h0, t0 = np.nanmedian(hy[:60]), np.nanmedian(ty[:60])
    k = np.searchsorted(d['t'], ic)
    low = np.minimum(np.abs(hy - h0), np.abs(ty - t0))
    while k > 0 and not low[k] < 10: k -= 1
    return d['t'][k] if k > 0 else None


def trial_windows(d, mode, pitch0, L, geo=None):
    """all typed whole-cycle windows and swings of one trial"""
    C = contacts(d)
    ev = sorted([(ic, fo, s, ft) for s in 'rl' for ic, fo, ft in zip(*C[s])], key=lambda e: e[0])
    if len(ev) < 6: return [], []
    lv = np.array([e[3][1] for e in ev])
    lo, hi = np.percentile(lv, 3), np.percentile(lv, 97)
    tol = 0.3 * 0.0254 * d['cond'] if mode == 'stair' else 0.012
    typ = [foot_type(v, lo, hi, tol) for v in lv]
    idx = np.clip(np.round((lv - lo) / max(hi - lo, 1e-6) * 6), 0, 6).astype(int)     # stairs: 0 floor, 1-5 steps, 6 landing
    labs = [label_at(d, e[0]) for e in ev]
    dirn = lambda l: 'up' if 'ascent' in l else 'dn' if 'descent' in l else None
    W, SW = [], []
    for k in range(len(ev)):
        side = ev[k][2]
        # own next contact and the contact of the other foot in between
        if k + 2 < len(ev) and ev[k + 1][2] != side and ev[k + 2][2] == side:
            a, b = ev[k][0], ev[k + 2][0]
            span = d['t'][(d['t'] >= a) & (d['t'] <= b)]
            ls = set(label_at(d, span))
            dr = {dirn(l) for l in ls} - {None}
            if len(dr) == 1 and not ls & {'idle', 'stand', 'turn1', 'turn2'} and 0.6 < b - a < 2.0:
                prev = typ[k - 1] if k > 0 and ev[k - 1][2] != side else 'X'
                win = prev + typ[k] + typ[k + 1] + typ[k + 2]
                fo = ev[k][1]
                if a < fo < b and fo > ev[k + 1][0]:
                    c = cycle(d, side, a, b, fo, pitch0, L)
                    c['cc'] = (ev[k + 1][0] - a) / (b - a)
                    c['step_len'] = np.hypot(*(ev[k + 2][3][[0, 2]] - ev[k][3][[0, 2]])) / L     # own heel to own heel
                    c['land'] = ev[k + 2][3]; c['land_idx'] = idx[k + 2]
                    W.append((dr.pop() + ':' + win, c))
        # swing into contact k: from own previous contact's foot off, or from standing
        pk = next((j for j in range(k - 1, -1, -1) if ev[j][2] == side), None)
        off = ev[pk][1] if pk is not None else standing_off(d, side, ev[k][0])
        if off is None or not 0.2 < ev[k][0] - off < 1.0: continue
        oth = next((j for j in range(k - 1, -1, -1) if ev[j][2] != side), None)
        frm = typ[pk] if pk is not None else 'F' if abs(np.nanmedian(d['mk'][:60, 1 if side == 'r' else 7]) / 1000 - lo) < 0.05 else '?'
        con = typ[oth] if oth is not None else frm
        l = labs[k] if dirn(labs[k]) else label_at(d, off + 0.02)
        dr = dirn(l)
        if dr and l not in ('idle',):
            c = swing_curves(d, side, off, ev[k][0], pitch0); c['land'] = ev[k][3]; c['land_idx'] = idx[k]
            SW.append((f'{dr}:sw:{frm}{con}{typ[k]}', c))
    return W, SW


def level_windows(d, pitch0, L):
    """steady level walking cycles: every label over the cycle is 'walk'"""
    C = contacts(d)
    ev = sorted([(ic, fo, s, ft) for s in 'rl' for ic, fo, ft in zip(*C[s])], key=lambda e: e[0])
    W = []
    for k in range(1, len(ev) - 2):
        side = ev[k][2]
        if ev[k + 1][2] == side or ev[k + 2][2] != side or ev[k - 1][2] == side: continue
        a, b = ev[k - 1][0], ev[k + 2][0]
        span = d['t'][(d['t'] >= a) & (d['t'] <= b)]
        if set(label_at(d, span)) != {'walk'}: continue
        a, b, fo = ev[k][0], ev[k + 2][0], ev[k][1]
        if not (0.8 < b - a < 1.6 and ev[k + 1][0] < fo < b): continue
        c = cycle(d, side, a, b, fo, pitch0, L)
        c['cc'] = (ev[k + 1][0] - a) / (b - a)
        c['step_len'] = np.hypot(*(ev[k + 2][3][[0, 2]] - ev[k][3][[0, 2]])) / L
        W.append(c)
    return W


FULL = CURVES[:6]
SCAL = ['stance', 'stride_time', 'cc', 'step_len', 'rise', 'land_frac']


def land_frac(c, key, geo):
    """where the ball of the landing foot stood (stairs): distance from the riser behind it (going up: riser k, the
    floor uses riser 1; going down: riser k+1, the landing uses riser 6), along the walking direction, in treads.
    Ball = 73.5 % of the way from the heel marker to the toe marker, as on the page's shoe."""
    if geo is None: return np.nan
    edge = lambda k: geo['z_riser1'] + (k - 1) * geo['tread']
    k = c['land_idx']; zb = c['land'][2] + 0.735 * (c['land'][5] - c['land'][2])
    if key.startswith('up'): return (zb - edge(max(k, 1))) / geo['tread']
    return -(zb - edge(min(k + 1, 6))) / geo['tread']


def average(per, keys, scal, min_cycles=2):
    S = {s: v for s, v in per.items() if len(v) >= min_cycles}
    if len(S) < 3: return None
    sm = {s: {**{k: np.mean([c[k] for c in v], 0) for k in keys}, **{q: np.nanmean([c.get(q, np.nan) for c in v]) for q in scal}} for s, v in S.items()}
    out = {k: np.nanmean([m[k] for m in sm.values()], 0) for k in keys + scal}
    out['subjects'] = len(S); out['cycles'] = int(sum(len(v) for v in S.values()))
    return out


def rnd(v):
    if isinstance(v, np.ndarray): return [round(float(x), 2) for x in v]
    if isinstance(v, (float, np.floating)): return round(float(v), 4)
    return v


def main():
    info = subject_info()
    files = sorted(R.glob('AB*/*/*.npz'))
    st = {}
    for p in files:
        s = standing_pitch(load(p))
        if s: st.setdefault(p.parts[-3], []).append(s)
    pitch0 = {k: {side: float(np.median([x[side] for x in v])) for side in 'rl'} for k, v in st.items()}
    full, swing, lvl, feet = {}, {}, {}, {}
    for p in files:                                   # stair geometry per step height (lab-fixed edges, all subjects)
        if p.parts[-2] != 'stair': continue
        cond = NAMED['stair'][int(p.name.split('_')[1]) - 1]
        d = load(p)
        if abs(d['cond'] - cond) <= 0.3: feet.setdefault(cond, []).extend(stair_footholds(d))
    geo = {c: stair_geometry(F) for c, F in feet.items()}
    for p in files:
        subj, mode = p.parts[-3], p.parts[-2]
        if subj not in pitch0 or subj not in info: continue
        d = load(p)
        if 'mk' not in d: continue
        L = 0.491 * info[subj]['height']
        if mode == 'levelground':
            for c in level_windows(d, pitch0[subj], L): lvl.setdefault(subj, []).append(c)
            continue
        cond = NAMED[mode][int(p.name.split('_')[1]) - 1]
        if abs(d['cond'] - cond) > 0.3: continue
        W, SW = trial_windows(d, mode, pitch0[subj], L)
        g = geo.get(cond) if mode == 'stair' else None
        for key, c in W: c['land_frac'] = land_frac(c, key, g); full.setdefault((mode, cond, key), {}).setdefault(subj, []).append(c)
        for key, c in SW: c['land_frac'] = land_frac(c, key, g); swing.setdefault((mode, cond, key), {}).setdefault(subj, []).append(c)
    out = {'level': {k: rnd(v) for k, v in average(lvl, FULL, SCAL).items()}}
    lv = out['level']
    print(f"level  subj={lv['subjects']} cyc={lv['cycles']} stance={lv['stance']*100:.1f}% T={lv['stride_time']:.2f}s step={lv['step_len']:.2f} L  "
          f"hip {min(lv['hip_flexion']):.0f}..{max(lv['hip_flexion']):.0f} knee {min(lv['knee_flexion']):.0f}..{max(lv['knee_flexion']):.0f}")
    out['full'], out['swing'] = {}, {}
    for (mode, cond, key), per in sorted(full.items()):
        a = average(per, FULL, SCAL)
        if a is None: continue
        out['full'][f'{mode}_{cond:g}_{key}'] = {k: rnd(v) for k, v in a.items()}
    for (mode, cond, key), per in sorted(swing.items()):
        a = average(per, FULL, ['duration', 'land_frac'])
        if a is None: continue
        out['swing'][f'{mode}_{cond:g}_{key}'] = {k: rnd(v) for k, v in a.items()}
    for grp in ('full', 'swing'):
        for k, v in out[grp].items():
            extra = (f"stance={v['stance']*100:.1f}% T={v['stride_time']:.2f}s cc={v['cc']:.2f} step={v['step_len']:.2f} rise={v['rise']:.3f}"
                     if grp == 'full' else f"dur={v['duration']:.2f}s") + f" land={v.get('land_frac')}"
            print(f"{grp:5s} {k:28s} subj={v['subjects']:2d} cyc={v['cycles']:4d} {extra}  knee max {max(v['knee_flexion']):.0f}")
    out['obstacle'] = {k: [round(float(x), 4) for x in v] if isinstance(v, list) else (rnd(v) if not isinstance(v, dict) else {q: list(w) for q, w in v.items()}) for k, v in OBSTACLE.items()}
    json.dump(out, open(HERE / 'data' / 'course_camargo.json', 'w'), separators=(',', ':'))
    page = dict(level=out['level'], full={k: out['full'][k] for k in PAGE_FULL}, swing={k: out['swing'][k] for k in PAGE_SWING},
                obstacle=out['obstacle'])
    json.dump(page, open(HERE / 'data' / 'course_page.json', 'w'), separators=(',', ':'))


def embed():
    """paste data/course_page.json into stairs/index.html (the line starting 'const COURSE = ')"""
    page = HERE.parent / 'stairs' / 'index.html'
    src = page.read_text().split('\n'); js = (HERE / 'data' / 'course_page.json').read_text()
    i = next(i for i, l in enumerate(src) if l.startswith('const COURSE = '))
    src[i] = 'const COURSE = ' + js + ';'
    page.write_text('\n'.join(src)); print('embedded', len(js), 'bytes')


if __name__ == '__main__':
    embed() if '--embed' in sys.argv else main()
