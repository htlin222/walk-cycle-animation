"""Countermovement jump and standing broad jump from CMU motion capture → analysis/data/jump_cmu.json (per-clip stats, averaged
phase-normalised curves) and analysis/data/jump_styles.json (the subset embedded as const JUMP in jump/index.html).

Usage: python jump_cmu.py            (BVH files in analysis/bvh/, cgspeed / Shriinivas/cmubvh conversion)

There is no force plate in CMU, so the phases are found from the whole-body centre of mass (COM), using the same events that
McMahon et al. (2018) define on the force plate:
  weighing     quiet stance before the movement
  unweighting  movement onset → peak downward COM velocity (force back at body weight)
  braking      peak downward velocity → COM velocity zero (bottom of the countermovement)
  propulsion   bottom → take-off
  flight       take-off → touchdown
  landing      touchdown → COM velocity zero again (deepest point of the landing)
  recovery     deepest landing point → standing again (not one of McMahon's phases; closes the loop)
COM = Dempster segment masses and centre-of-mass positions as tabulated by Winter (2009), from the BVH joint centres.
Units: CMU lengths are 0.45 inch (1/0.45 in = 0.05644 m), 120 fps. With these units a free parabola through the airborne COM
gives g = 9.7–10.4 m/s² for every kept jump, an independent check of both scale and frame rate.
Take-off / touchdown: feet 3 cm up finds the flight; the edges are then moved to where the COM joins / leaves free fall.
Jumps are kept only if they start from quiet stance and pass the physics checks below (QUALITY).
Each jump is time-normalised phase by phase, averaged within an actor, then across actors.
Flight physics checks: a parabola fitted to the airborne COM gives g, and flight time T gives h = g T² / 8 (Linthorne 2001).
"""
import json, pathlib, numpy as np
from bvh import parse, fk
HERE = pathlib.Path(__file__).parent; D = HERE / 'data'
G = 9.81
UNIT = 0.0254 / 0.45
CLIPS = {
    'cmj':   {'13': ['13_39', '13_40', '13_41', '13_42'], '16': ['16_01', '16_02'], '49': ['49_02', '49_03']},
    'broad': {'13': ['13_11', '13_13', '13_19', '13_32'], '16': ['16_05', '16_06', '16_07', '16_09', '16_10'],
              '118': [f'118_{i}' for i in range(18, 30)]},
}
# Not used: subjects 141 / 143 ("Jumping Heights", "Jumping Distances"). At their stated 120 fps the airborne COM falls
# at ≈ 38 m/s² (≈ 4 g, so probably 60 fps), and even at 60 fps the fit gives 8.2–9.6 m/s² (length scale also off).
# Subject 49 jumps up and down repeatedly; only jumps that start from quiet stance are kept.
QUALITY = dict(g=1.0, rms_mm=4.0, phase=dict(unweighting=0.9, braking=0.6, propulsion=0.6, landing=0.6))   # |g − 9.81| < 1 m/s², parabola rms < 4 mm, ground phases 50 ms … max s
ARM_SWING = 60                                             # degrees of shoulder range that count as an arm swing
NP = 40                                                    # samples per phase
PHASES = ['unweighting', 'braking', 'propulsion', 'flight', 'landing', 'recovery']
# Dempster via Winter (2009) Table 4.1: segment mass / body mass, COM as fraction of the segment from its proximal end
SEG = [('UpLeg', 'Leg', 0.100, 0.433), ('Leg', 'Foot', 0.0465, 0.433), ('Foot', 'ToeBase', 0.0145, 0.5),
       ('Arm', 'ForeArm', 0.028, 0.436), ('ForeArm', 'Hand', 0.016, 0.430), ('Hand', 'FingerBase', 0.006, 0.506)]


def smooth(x, w):
    k = np.ones(w) / w; p = w // 2
    return np.convolve(np.pad(x, (p, p), mode='edge'), k, 'valid')


def load(name):
    J, Dm, ft = parse(str(HERE / 'bvh' / f'{name}.bvh')); Dm = Dm[1:]       # drop T-pose frame
    fps = 1 / ft
    P = fk(J, Dm) * UNIT; N = [j['name'] for j in J]
    return {n: P[:, i] for i, n in enumerate(N)}, fps


def com(g):
    c = 0.497 * ((g['LeftUpLeg'] + g['RightUpLeg']) / 2 + (g['LeftArm'] + g['RightArm']) / 2) / 2      # trunk: hips ↔ shoulders midpoint
    c = c + 0.081 * (g['Neck1'] + g['Head_End']) / 2      # head and neck: COM at the ear canal (Winter), ≈ midway upper neck ↔ crown
    for a, b, m, f in SEG:
        for s in ('Left', 'Right'): c = c + m * (g[s + a] + f * (g[s + b] - g[s + a]))
    return c                                                                                            # masses sum to 1.000


def fitg(t, y):
    c = np.polyfit(t, y, 2); r = y - np.polyval(c, t)
    return -2 * c[0], float(np.sqrt(np.mean(r ** 2)))


def jumps(name):
    g, fps = load(name); dt = 1 / fps
    L = np.mean([np.linalg.norm(g[s + 'UpLeg'] - g[s + 'Leg'], axis=1).mean() + np.linalg.norm(g[s + 'Leg'] - g[s + 'Foot'], axis=1).mean() for s in ('Left', 'Right')])
    C = com(g)
    # every foot joint gets its own floor level (2nd percentile of its height); the floor is the lowest of them
    FJ = [s + j for s in ('Left', 'Right') for j in ('Foot', 'ToeBase', 'ToeBase_End')]
    fl = {n: np.percentile(g[n][:, 1], 2) for n in FJ}; floor = min(fl.values())
    lift = np.min([g[n][:, 1] - fl[n] for n in FJ], 0)       # how far the lowest-lifted foot joint is off its floor level
    y = C[:, 1] - floor
    w = max(3, int(round(0.025 * fps)) | 1)
    vy = np.gradient(smooth(y, w), dt)
    air = lift > 0.03                                         # heels and toes of both feet 3 cm up
    segs, i = [], 0
    while i < len(air):
        if air[i]:
            j = i
            while j < len(air) and air[j]: j += 1
            if 0.2 < (j - i) * dt < 0.9: segs.append((i, j))
            i = j
        else: i += 1
    out, prev = [], 0
    for to, td in segs:
        # The 3 cm rule finds flights robustly, but starts them late and ends them early. Refine with the force-plate
        # definition: in the air the only force is gravity, so take-off / touchdown are where the COM joins / leaves the
        # free-fall parabola (y'' = −g) fitted to the core of the flight, within 3 mm.
        tc = np.arange(to, td) * dt
        c1 = np.polyfit(tc, y[to:td] + G * tc ** 2 / 2, 1)            # y = c1[0]·t + c1[1] − g t²/2 (g fixed)
        par = lambda i: c1[0] * i * dt + c1[1] - G * (i * dt) ** 2 / 2
        while to > 0 and abs(y[to - 1] - par(to - 1)) < 0.003: to -= 1
        while td < len(y) - 1 and abs(y[td] - par(td)) < 0.003: td += 1
        a = max(prev, to - int(2.0 * fps)); prev = td
        bot = a + int(np.argmin(y[a:to]))
        pnv = a + int(np.argmin(vy[a:bot])) if bot - a > 3 else None
        if pnv is None or vy[pnv] > -0.3: print(f'  {name} @{to*dt:.2f}s skipped: no countermovement'); continue
        on = pnv
        while on > 0 and vy[on] < -0.08: on -= 1               # movement onset: COM starts moving down
        q0 = on - int(0.15 * fps)                               # quiet stance: COM still for 150 ms before the onset
        if q0 < a or np.abs(vy[q0:on]).max() > 0.15: print(f'  {name} @{to*dt:.2f}s skipped: no quiet stance before'); continue
        e = min(len(y), td + int(0.8 * fps))
        land = td + int(np.argmin(y[td:e]))
        stand = np.median(y[max(0, on - int(0.5 * fps)):on])
        rec = land
        while rec < min(len(y) - 1, land + int(1.2 * fps)) and y[rec] < stand - 0.015: rec += 1
        if rec >= len(y) - 1 or y[rec] < stand - 0.015:
            rec = land + int(np.argmax(y[land:min(len(y), land + int(1.2 * fps))]))
        st = max(0, on - int(0.5 * fps))
        # sagittal frame: facing direction at movement onset (perpendicular to the hip line, horizontal)
        r = (g['RightUpLeg'][st:on + 1] - g['LeftUpLeg'][st:on + 1]).mean(0); r[1] = 0
        f = np.cross([0, 1, 0], r); f /= np.linalg.norm(f)
        P2 = lambda p: np.stack([(p[:, [0, 2]] @ f[[0, 2]]), p[:, 1] - floor], 1)    # (forward, up) in m
        mid = lambda n: P2((g['Left' + n] + g['Right' + n]) / 2)
        hip, ank, toe, Cs = mid('UpLeg'), mid('Foot'), mid('ToeBase'), P2(C)
        ang = lambda p, q: np.degrees(np.arctan2(q[:, 0] - p[:, 0], p[:, 1] - q[:, 1]))     # segment p→q hanging below p, forward +
        angU = lambda p, q: np.degrees(np.arctan2(q[:, 0] - p[:, 0], q[:, 1] - p[:, 1]))    # segment p→q above p, forward lean +
        thigh = ang(hip, mid('Leg')); shank = ang(mid('Leg'), ank)
        pitch = np.degrees(np.arctan2(toe[:, 1] - ank[:, 1], toe[:, 0] - ank[:, 0]))
        uarm = np.degrees(np.unwrap(np.radians(ang(mid('Arm'), mid('ForeArm')))))
        farm = np.degrees(np.unwrap(np.radians(ang(mid('ForeArm'), mid('Hand')))))
        k360 = 360 * np.round(np.median(uarm[st:on + 1]) / 360); uarm, farm = uarm - k360, farm - k360   # arms hang at ≈ 0°, overhead ≈ 180°
        q = dict(hipx=(hip[:, 0] - ank[:, 0]) / L, hipy=(hip[:, 1] - ank[:, 1]) / L,       # hip relative to ankle
                 comx=(Cs[:, 0] - hip[:, 0]) / L, comy=(Cs[:, 1] - hip[:, 1]) / L,        # COM relative to hip
                 pitch=pitch, knee=thigh - shank, thigh=thigh,
                 lumbar=angU(P2(g['Hips']), P2(g['Spine1'])), thorax=angU(P2(g['Spine1']), P2(g['Neck1'])),
                 head=angU(P2(g['Head']), P2(g['Head_End'])), uarm=uarm, farm=farm,
                 com_y=Cs[:, 1] / L, lift=lift / L)
        # standing references, taken over the quiet stance
        ref = {k: float(np.median(q[k][st:on + 1])) for k in ('pitch', 'lumbar', 'thorax', 'head')}
        for k in ref: q[k] = q[k] - ref[k]
        # ankle height above its standing height (the page follows it during toe-off and toe-strike, when the foot rolls
        # over the toes and no longer pivots on the ball)
        q['ank_dy'] = (ank[:, 1] - np.median(ank[st:on + 1, 1])) / L
        ev = [on, pnv, bot, to, td, land, rec]
        cur = {}
        for k, v in q.items():
            parts = [np.interp(np.linspace(st, on, 12), np.arange(len(v)), v)]
            for a_, b_ in zip(ev[:-1], ev[1:]): parts.append(np.interp(np.linspace(a_, b_, NP), np.arange(len(v)), v))
            cur[k] = parts
        tt = np.arange(to, td) * dt
        gC, rC = fitg(tt - tt[0], Cs[to:td, 1]); gH, rH = fitg(tt - tt[0], hip[to:td, 1])
        T = (td - to) * dt
        xb = lambda i: toe[i, 0]
        dur = {p: (b_ - a_) * dt for p, a_, b_ in zip(PHASES, ev[:-1], ev[1:])}
        out.append(dict(clip=name, L=L, T=T, dur=dur, curves=cur,
            stats=dict(flight_time=T, h_flight_time=G * T * T / 8, h_com=float(Cs[to:td, 1].max() - Cs[to, 1]),
                       v_takeoff=float(vy[to]), v_takeoff_from_T=G * T / 2, g_com=gC, g_com_rms_mm=rC * 1000, g_hip=gH, g_hip_rms_mm=rH * 1000,
                       depth=float(Cs[on, 1] - Cs[bot, 1]), depth_L=float((Cs[on, 1] - Cs[bot, 1]) / L), land_depth=float(Cs[on, 1] - Cs[land, 1]),
                       knee_bottom=float(q['knee'][bot]), knee_land=float(q['knee'][land]), trunk_bottom=float(q['thorax'][bot]),
                       com_td_minus_to=float(Cs[td, 1] - Cs[to, 1]), com_to_minus_stand=float(Cs[to, 1] - stand),
                       arm_back=float(q['uarm'][on:to].min()), arm_takeoff=float(q['uarm'][to]), arm_max=float(q['uarm'][on:td].max()),
                       distance=float(xb(land) - xb(on)), distance_L=float((xb(land) - xb(on)) / L), vx_takeoff=float(np.gradient(Cs[:, 0], dt)[to]),
                       time_to_takeoff=(to - on) * dt, leg_m=L)))
    return out


def summarise(style):
    per_subj, rows, swing = {}, [], {}
    for subj, clips in CLIPS[style].items():
        J = []
        for j in (j for n in clips for j in jumps(n)):
            s, lim = j['stats'], QUALITY['phase']
            bad = [k for k, v in lim.items() if not 0.05 < j['dur'][k] < v]
            if abs(s['g_com'] - G) > QUALITY['g'] or s['g_com_rms_mm'] > QUALITY['rms_mm'] or bad:
                print(f"  {j['clip']} rejected: g {s['g_com']:.2f} m/s², rms {s['g_com_rms_mm']:.1f} mm, phases {bad}"); continue
            J.append(j)
        for j in J:
            s = j['stats']
            rows.append(dict(clip=j['clip'], subject=subj, **{k: round(float(v), 4) for k, v in s.items()}, **{'dur_' + k: round(v, 4) for k, v in j['dur'].items()}))
            print(f"{style:5s} {j['clip']:7s} T={s['flight_time']:.3f}s  h(gT²/8)={s['h_flight_time']*100:4.1f}  h(COM)={s['h_com']*100:4.1f} cm  "
                  f"g COM={s['g_com']:5.2f} (rms {s['g_com_rms_mm']:.1f} mm)  g hip={s['g_hip']:5.2f}  depth={s['depth']*100:4.1f} cm  knee={s['knee_bottom']:.0f}°  "
                  f"land={s['land_depth']*100:.1f} cm  dist={s['distance']:.2f} m  arm {s['arm_back']:.0f}→{s['arm_takeoff']:.0f}°  "
                  + ' '.join(f"{k[:4]}={v*1000:.0f}" for k, v in j['dur'].items()))
        if not J: continue
        # arm swing: only some actors swing their arms. Lees et al. (2004) show the swing adds height (+8.6 cm) and is part of
        # a maximal jump, so the arm curves come from the jumps that use one (shoulder range > 60°), averaged the same way.
        A = [j for j in J if j['stats']['arm_max'] - j['stats']['arm_back'] > ARM_SWING]
        if A: swing[subj] = {k: [np.mean([j['curves'][k][p] for j in A], 0) for p in range(7)] for k in ('uarm', 'farm')}
        per_subj[subj] = dict(n=len(J), curves={k: [np.mean([j['curves'][k][p] for j in J], 0) for p in range(7)] for k in J[0]['curves']},
                              dur={p: float(np.mean([j['dur'][p] for j in J])) for p in PHASES},
                              stats={k: float(np.mean([j['stats'][k] for j in J])) for k in J[0]['stats']})
    S = list(per_subj.values())
    curves = {k: [np.mean([s['curves'][k][p] for s in S], 0) for p in range(7)] for k in S[0]['curves']}
    for k in ('uarm', 'farm'): curves[k] = [np.mean([swing[s][k][p] for s in swing], 0) for p in range(7)]
    dur = {p: float(np.mean([s['dur'][p] for s in S])) for p in PHASES}
    stats = {k: float(np.mean([s['stats'][k] for s in S])) for k in S[0]['stats']}
    return dict(actors=len(S), jumps=sum(s['n'] for s in S), leg_m=round(stats['leg_m'], 4), arm_swing_actors=sorted(swing),
                durations={k: round(v, 4) for k, v in dur.items()},
                stats={k: round(v, 4) for k, v in stats.items()},
                per_actor={k: dict(n=v['n'], **{kk: round(vv, 4) for kk, vv in v['stats'].items()}, **{'dur_' + p: round(x, 4) for p, x in v['dur'].items()}) for k, v in per_subj.items()},
                clips=rows,
                curves={k: {ph: [round(float(x), 4) for x in v[i]] for i, ph in enumerate(['weighing'] + PHASES)} for k, v in curves.items()})


if __name__ == '__main__':
    out = {}
    for style in CLIPS:
        r = summarise(style); out[style] = r; s = r['stats']
        print(f"== {style}: {r['jumps']} jumps, {r['actors']} actors.  flight {s['flight_time']*1000:.0f} ms → h = gT²/8 = {s['h_flight_time']*100:.1f} cm "
              f"(COM rise {s['h_com']*100:.1f} cm)  g COM {s['g_com']:.2f}, hip {s['g_hip']:.2f} m/s²  depth {s['depth']*100:.1f} cm  knee {s['knee_bottom']:.0f}°  "
              f"dist {s['distance']:.2f} m  " + ' '.join(f"{k} {v*1000:.0f} ms" for k, v in r['durations'].items()))
    json.dump(out, open(D / 'jump_cmu.json', 'w'))
    # what jump/index.html needs (const JUMP): timing, sizes and the curves that drive the figure
    KEEP = ('hipx', 'hipy', 'comx', 'comy', 'pitch', 'ank_dy', 'lumbar', 'thorax', 'head', 'uarm', 'farm', 'com_y')
    page = {st: dict(actors=r['actors'], jumps=r['jumps'], leg_m=r['leg_m'], arm_swing_actors=r['arm_swing_actors'], durations=r['durations'],
                     stats={k: r['stats'][k] for k in ('flight_time', 'h_flight_time', 'h_com', 'depth', 'knee_bottom', 'distance', 'distance_L', 'g_com', 'com_td_minus_to')},
                     curves={k: {ph: [round(x, 3) for x in v] for ph, v in r['curves'][k].items()} for k in KEEP})
            for st, r in out.items()}
    json.dump(page, open(D / 'jump_styles.json', 'w'), separators=(',', ':'))
