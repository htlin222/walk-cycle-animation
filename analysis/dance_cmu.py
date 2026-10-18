"""Dance cycles from CMU motion capture, built like the walk and run cycles: measure, cut, phase-align, average.

Input : CMU dance clips in analysis/bvh/ (cgspeed BVH conversion, see README); time windows of steady dancing in STYLES
          charleston  93_03, 93_04, 93_05                subject 93 ("charleston_01", "charleston side by side female / male")
          salsa       60_02, 60_03, 60_04, 61_01, 61_02  subjects 60 and 61 (a salsa couple; the pose uses 60 only, see POSE)
          indian      94_08                              subject 94 (Indian dance; right-foot half and left-foot half)
Output: analysis/data/dance_cmu.json  (python dance_cmu.py --embed also writes it into dance/index.html as const DANCE)

1. Body frame. Travel and turning are averaged over one cycle and removed, so the dance is seen from the dancer's own frame.
2. Cycle. The period over which the whole pose repeats: feet, hands, pelvis and head, standardised, autocorrelated (0.6-4 s).
3. Beat, from the motion alone. The beat is the vertical pelvis bounce: of the harmonics of the cycle whose period lies in
   0.3-1.2 s, the one with the largest pelvis amplitude (pooled over a style's segments) gives the beats per cycle;
   its trough marks the beat. Touchdowns (a foot within 3.5 % leg length of the floor, slower than 0.4 L/s) are counted too.
4. Every cycle is cut at a beat and time-normalised. Each segment is phase-aligned to the template by whole-beat shifts,
   optionally left/right mirrored (partners and side-by-side dancers move in mirror image), then cycles are averaged.
   The loop is closed with the recording's own continuation (cross-fade over half a cycle around the seam) and
   Fourier-smoothed (10 Hz).
5. Camera: horizontal, turned 30 deg from profile toward the dancer's front (see dance/README.md).
6. Feet: a planted shoe pivots on the heel (toes up) or the ball (heel up) about one stored floor point per contact;
   swing is corrected with cubic Hermite blends and lifted wherever the sole would dip below the floor.
   Knees are re-solved (two-bone IK in the picture plane, recorded segment lengths, bend side as recorded).
"""
import json, pathlib, sys, numpy as np
from bvh import parse, fk
HERE = pathlib.Path(__file__).parent; D = HERE / 'data'
# CMU's index lists subjects 60/61 at 60 fps; the BVH conversion stamps every file 1/120 s, which would double the tempo.
FPS = {'60': 60, '61': 60}
STYLES = {
    'charleston': [('93_03', 0.35, 3.30), ('93_04', 0.10, 3.40), ('93_05', 0.05, 3.80)],
    'salsa': [('60_02', 4, 13), ('60_03', 14, 25), ('60_04', 14, 28), ('61_01', 7, 19), ('61_02', 17, 28)],
    'indian': [('94_08', 1.2, 10.5), ('94_08', 10.8, 21.3)],
}
# Which measured stretches shape the pose (all of them set the tempo). Salsa: the two partners dance different steps
# (subject 60, the leader, a forward-back basic, ankle excursion 0.7-1.1 L fore-aft; subject 61, the follower, mostly
# side to side, 1.0-1.7 L laterally), so averaging both cancels the steps out (0.5 L each way, 4 touchdowns a cycle).
# The pose uses the leader only, and of his 10 aligned cycles the 5 closest to their average (pose r 0.85-0.89).
POSE = {'salsa': dict(clips=('60_',), top=5)}
VIEW = np.radians(30)          # camera yaw away from profile, toward the dancer's front
SPB = 40                       # samples per beat in the stored cycle
MIN_R = 0.25                   # a segment must repeat at least this well (pose autocorrelation) to be used
FC = 10.0                      # Fourier cut-off, Hz
HEEL, BALL, TOE = np.array([-0.085, -0.07]), np.array([0.17, -0.07]), np.array([0.255, -0.07])   # shoe of the page (leg lengths)
SIDES = ('Right', 'Left')      # index 0 = right = near side, as in the walk and run pages
_cache = {}


def ss(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


def rot(v, a): c, s = np.cos(a), np.sin(a); return np.array([v[0] * c - v[1] * s, v[0] * s + v[1] * c])


def shoe_pt(A, pitch, v):
    """Port of shoePt in run/ and dance/: rigid shoe, toe box bends at the ball to stay above the floor."""
    th = -pitch; q = rot(v, pitch)
    if v[0] > 0.15 and th > 0:
        b = rot(BALL, pitch); bh = A[1] + b[1]
        k = min(1, max(0, 1 - bh / 0.06)); q0 = min(1, max(-1, (bh - 0.004) / 0.085)); need = max(0, th - np.arcsin(q0))
        ang = min(th, max(th * k, need)); q = b + rot(q - b, ang * min(1, (v[0] - 0.15) / 0.03))
    return A + q


def sole_low(A, p): return min(shoe_pt(A, p, v)[1] for v in (HEEL, BALL, TOE))


def load(clip):
    if clip in _cache: return _cache[clip]
    J, Dm, ft = parse(str(HERE / 'bvh' / f'{clip}.bvh')); P = fk(J, Dm); N = [j['name'] for j in J]
    g = lambda n: P[:, N.index(n)]
    legL = np.linalg.norm(g('RightUpLeg') - g('RightLeg'), axis=1).mean() + np.linalg.norm(g('RightLeg') - g('RightFoot'), axis=1).mean()
    P = P / legL; fps = FPS.get(clip.split('_')[0], round(1 / ft))
    tpose, P = P[0], P[1:]                                    # frame 0 of the conversion is a T-pose
    _cache[clip] = (P, tpose, {n: i for i, n in enumerate(N)}, fps); return _cache[clip]


def facing(P, I):   # forward = (left hip - right hip) x up, horizontal unit vector (x, z)
    h = P[..., I['LeftUpLeg'], :] - P[..., I['RightUpLeg'], :]; f = np.stack([-h[..., 2], h[..., 0]], -1)
    return f / np.linalg.norm(f, axis=-1, keepdims=True)


def contacts(P, I, fps):
    """Planted flags and touchdown frames per foot (world frame, floor = 5th percentile of ankle height)."""
    out = []
    for s in SIDES:
        a, t = P[:, I[s + 'Foot']], P[:, I[s + 'ToeBase']]
        ha, ht = a[:, 1] - np.percentile(a[:, 1], 5), t[:, 1] - np.percentile(t[:, 1], 5)
        low = np.where(ha < ht, 0, 1); pos = np.where(low[:, None] == 0, a, t)
        v = np.linalg.norm(np.gradient(pos[:, [0, 2]], axis=0), axis=1) * fps
        c = (np.minimum(ha, ht) < 0.035) & (v < 0.4)
        c = debounce(c, int(0.06 * fps)); out.append(c)
    return out, sorted(np.concatenate([np.flatnonzero(np.diff(c.astype(int)) == 1) + 1 for c in out]))


def debounce(c, n):
    c = c.copy()
    for val in (True, False):           # fill short gaps, then drop short contacts
        i = 0
        while i < len(c):
            if c[i] != val:
                j = i
                while j < len(c) and c[j] != val: j += 1
                if 0 < i and j < len(c) and j - i < n: c[i:j] = val
                i = j
            else: i += 1
    return c


def pose_features(L, I):   # feet, hands, pelvis and head in the body frame, each coordinate standardised
    X = np.concatenate([L[:, I[s + n]] for s in SIDES for n in ('Foot', 'ToeBase', 'Hand')] + [L[:, I['Hips']], L[:, I['Head']]], 1)
    return (X - X.mean(0)) / (X.std(0) + 1e-9)


def cycle_period(L, I, fps, lo=0.6, hi=4.0):
    """Repeat period of the whole pose: first autocorrelation peak within 80 % of the highest (0.6-4 s), parabolic refinement."""
    X = pose_features(L, I); lags = np.arange(int(lo * fps), min(int(hi * fps), len(X) - int(0.8 * fps)))
    r = np.array([np.mean(np.sum(X[:-l] * X[l:], 1) / X.shape[1]) for l in lags])
    pk = [i for i in range(1, len(r) - 1) if r[i] > r[i - 1] and r[i] >= r[i + 1] and r[i] > 0]
    if not pk: return None, 0.0
    top = max(r[i] for i in pk); i = next(i for i in pk if r[i] >= 0.8 * top)
    d = 0.5 * (r[i - 1] - r[i + 1]) / (r[i - 1] - 2 * r[i] + r[i + 1])
    return (lags[i] + d) / fps, float(r[i])


def pelvis_harmonics(L, I, fps, Tc, H=12):
    """Amplitude and phase of the vertical pelvis motion at the first H harmonics of the cycle frequency."""
    y = L[:, I['Hips'], 1]; n = int(round(Tc * fps)); y = y - np.convolve(np.pad(y, n // 2, mode='edge'), np.ones(n) / n, 'valid')[:len(y)]
    m = int(len(y) // n * n); y, t = y[:m], np.arange(m) / fps          # whole cycles only
    z = np.array([2 * np.mean(y * np.exp(-2j * np.pi * h * t / Tc)) for h in range(1, H + 1)]); return z


def body_frame(P, I, fps, win):
    """Joint positions in a slowly moving body frame (fwd, up, right): travel and turning averaged over one cycle."""
    n = max(1, int(win * fps)) | 1; k = np.ones(n) / n
    sm = lambda x: np.convolve(np.pad(x, n // 2, mode='edge'), k, 'valid')
    root = P[:, I['Hips']]; f = facing(P, I); yaw = np.unwrap(np.arctan2(f[:, 1], f[:, 0]))
    rx, rz, yw = sm(root[:, 0]), sm(root[:, 2]), sm(yaw)
    F = np.stack([np.cos(yw), np.sin(yw)], 1); Rt = np.stack([-F[:, 1], F[:, 0]], 1)    # right = fwd rotated -90 deg about up
    d = P[:, :, [0, 2]] - np.stack([rx, rz], 1)[:, None, :]
    L = np.stack([(d * F[:, None]).sum(-1), P[:, :, 1], (d * Rt[:, None]).sum(-1)], -1)
    assert np.mean(L[:, I['RightUpLeg'], 2] - L[:, I['LeftUpLeg'], 2]) > 0, 'right hip must lie on +right'
    return L


def tpose_local(tp, I):   # the T-pose in the same (fwd, up, right) axes
    f = facing(tp[None], I)[0]; r = np.array([-f[1], f[0]]); d = tp[:, [0, 2]] - tp[I['Hips'], [0, 2]]
    return np.stack([d @ f, tp[:, 1], d @ r], -1)


def other_side(n):   # LeftFoot <-> RightFoot, LHipJoint <-> RHipJoint, LThumb_End <-> RThumb_End
    for a, b in (('Left', 'Right'), ('Right', 'Left')):
        if n.startswith(a): return b + n[len(a):]
    if n[:1] in 'LR' and n[1:2].isupper(): return ('R' if n[0] == 'L' else 'L') + n[1:]
    return n


def mirror(L, I):
    M = L.copy()
    for n, i in I.items(): M[:, i] = L[:, I[other_side(n)]] * [1, 1, -1]
    return M


def segment(clip, t0, t1):
    """One stretch of steady dancing: pose repeat period, pelvis harmonics, touchdowns."""
    P, tp, I, fps = load(clip); a, b = int(t0 * fps), int(t1 * fps)
    con, td = contacts(P, I, fps); td = np.array([t for t in td if a <= t < b])
    s = dict(clip=clip, t0=t0, t1=t1, P=P[a:b], I=I, fps=fps, tpose=tp, n_td=len(td), td_hz=len(td) / (t1 - t0))
    s['L'] = body_frame(s['P'], I, fps, 2.0); s['Tc'], s['rc'] = cycle_period(s['L'], I, fps)
    if s['Tc'] is None: return s
    s['L'] = body_frame(s['P'], I, fps, s['Tc'])          # travel and turning averaged over exactly one cycle
    s['Tc'], s['rc'] = cycle_period(s['L'], I, fps); s['H'] = pelvis_harmonics(s['L'], I, fps, s['Tc'])
    return s


def resample(L, fps, start, dur, N, M):
    """Samples -M..N+M of one cycle (N per cycle); NaN where the recording has ended."""
    t = start + dur * np.arange(-M, N + M + 1) / N; x = np.arange(len(L)) / fps
    out = np.array([[np.interp(t, x, L[:, j, c]) for c in range(3)] for j in range(L.shape[1])]).transpose(2, 0, 1)
    out[(t < 0) | (t > x[-1])] = np.nan; return out


def beats_per_cycle(segs):
    """The beat is the pelvis bounce: the strongest vertical-pelvis harmonic of the cycle whose period is 0.3-1.2 s
    (pooled over segments, each normalised). Its trough marks the beat (the knees give on the beat)."""
    amp = np.sum([np.abs(s['H']) / np.abs(s['H']).sum() for s in segs], 0)
    ok = [h for h in range(1, len(amp) + 1) if all(0.3 <= s['Tc'] / h <= 1.2 for s in segs)]
    k = max(ok, key=lambda h: amp[h - 1])
    for s in segs:
        s['T'] = s['Tc'] / k; ph = np.angle(s['H'][k - 1])        # y ~ |z| cos(2 pi k t / Tc + ph); trough where the angle = pi
        s['ph'] = ((np.pi - ph) / (2 * np.pi) % 1) * s['T']
    return k, amp / amp.sum()


def corr(a, b):
    a = a.reshape(len(a), -1); b = b.reshape(len(b), -1); a = a - a.mean(0); b = b - b.mean(0)
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))


def four(x, K):
    X = np.fft.rfft(x, axis=0); X[K + 1:] = 0; return np.fft.irfft(X, x.shape[0], axis=0)


def build(name, segs, k, top=None):
    T = float(np.mean([s['T'] for s in segs]))
    N = SPB * k; M = N // 4; I = segs[0]['I']; feat = [I[s + n] for s in SIDES for n in ('Foot', 'ToeBase', 'Hand', 'ForeArm', 'Leg')] + [I['Hips'], I['Head']]
    core = slice(M, M + N + 1)
    def cycles(s, shift, mir):   # every whole cycle in the segment, with a quarter cycle of what comes before and after
        L = mirror(s['L'], I) if mir else s['L']; out = []; st = s['ph'] + shift * s['T']
        while st < 0: st += k * s['T']
        while st + k * s['T'] <= (len(L) - 1) / s['fps']:
            out.append(resample(L, s['fps'], st, k * s['T'], N, M)); st += k * s['T']
        return out
    tmpl = None
    for _ in range(3):                                   # align to the running average, three passes
        allc = []; ref = (tmpl if tmpl is not None else cycles(segs[0], 0, False)[0])[core][:, feat]
        for s in segs:
            best = (-2, 0, False)
            for sh in range(k):
                for mir in (False, True):
                    cs = cycles(s, sh, mir)
                    if not cs: continue
                    r = np.mean([corr(c[core][:, feat], ref) for c in cs])
                    if r > best[0]: best = (r, sh, mir)
            s['shift'], s['mirror'], s['r'] = best[1], best[2], best[0]; s['cyc'] = cycles(s, best[1], best[2]); allc += s['cyc']
        tmpl = np.nanmean(allc, 0)
    if top and top < len(allc):                          # keep only the cycles closest to the aligned average (crisper steps)
        r = [corr(c[core][:, feat], tmpl[core][:, feat]) for c in allc]; keep = set(np.argsort(r)[::-1][:top].tolist())
        i = 0
        for s in segs: n = len(s['cyc']); s['kept'] = [j for j in range(n) if i + j in keep]; i += n
        allc = [c for j, c in enumerate(allc) if j in keep]; tmpl = np.nanmean(allc, 0)
    else:
        for s in segs: s['kept'] = list(range(len(s['cyc'])))
    # close the loop with the recording's own continuation: around the seam, cross-fade from "the end of the cycle running on"
    # to "the start of the cycle, as it was approached", both averaged over the same cycles (smoothstep over half a cycle).
    A = tmpl[M:M + N].copy()
    for j in range(-M, M):
        w = 1 - ss((j + M) / (2 * M)); x = w * tmpl[M + N + j] + (1 - w) * tmpl[M + j]   # sample N+j: running on vs approached
        A[(N + j) % N] = x
    A = four(A, int(FC * k * T)); A[:, :, [0, 2]] -= A[:, I['Hips'], [0, 2]].mean(0)
    spread = float(np.mean([np.linalg.norm(c[core][:N] - tmpl[core][:N], axis=-1)[:, feat].mean() for c in allc]))
    return dict(T=T, k=k, N=N, A=A, I=I, n_cycles=len(allc), spread=spread, tpose=segs[0]['tpose'])


def project(p):   # (fwd, up, right) -> screen (x, y): camera on the right, turned VIEW toward the front
    return np.stack([p[..., 0] * np.cos(VIEW) - p[..., 2] * np.sin(VIEW), p[..., 1]], -1)


def ang_v(d):   # angle of a 2D vector from vertical (up), forward positive: U(a)=[sin a, cos a]
    return np.arctan2(d[..., 0], d[..., 1])


def lock_feet(X, PIT, fps_c, N):
    """X: (N,2) ankle on screen, PIT: (N,) pitch. Returns the corrected ankle, contact flags and per-sample floor anchor
    (x of the flat heel point; 0 in the air)."""
    low = np.array([sole_low(X[i], PIT[i]) for i in range(N)])
    v = np.linalg.norm(np.gradient(np.concatenate([X[-2:], X, X[:2]]), axis=0)[2:-2], axis=1) * fps_c
    c = (low < 0.04) & (v < 0.6)
    c = debounce_c(c, int(0.07 * fps_c))
    if c.all() or not c.any(): raise SystemExit(f'contact detection failed: sole height {low.min():.3f}-{low.max():.3f} L, speed {v.min():.2f}-{v.max():.2f} L/s')
    Y = X.copy(); corr_ = np.zeros((N, 2)); anchor = np.zeros(N)
    # contact runs (circular)
    s0 = np.flatnonzero(c & ~np.roll(c, 1)); runs = []
    for s in s0:
        e = s
        while c[(e + 1) % N]: e += 1
        runs.append(np.arange(s, e + 1) % N)
    for r in runs:
        off = np.array([-rot(HEEL, p) if p >= 0 else (BALL - HEEL) - rot(BALL, p) for p in PIT[r]])   # ankle minus the flat heel point
        hx = round(float(np.mean(X[r, 0] - off[:, 0])), 4); anchor[r] = hx    # one floor point per contact (stored, so the page pivots exactly)
        Y[r] = np.stack([hx + off[:, 0], off[:, 1]], 1)
        corr_[r] = Y[r] - X[r]
    # swing: cubic Hermite between the corrections at the ends of the neighbouring contacts
    for a, b in zip(runs, runs[1:] + runs[:1]):
        i0, i1 = a[-1], b[0]; n = (i1 - i0) % N
        if n <= 1: continue
        d0 = (corr_[i0] - corr_[(i0 - 1) % N]) if len(a) > 1 else 0 * corr_[i0]
        d1 = (corr_[(i1 + 1) % N] - corr_[i1]) if len(b) > 1 else 0 * corr_[i1]
        for j in range(1, n):
            t = j / n; h = [(2 * t**3 - 3 * t**2 + 1), (t**3 - 2 * t**2 + t), (-2 * t**3 + 3 * t**2), (t**3 - t**2)]
            i = (i0 + j) % N; corr_[i] = h[0] * corr_[i0] + h[1] * d0 * n + h[2] * corr_[i1] + h[3] * d1 * n
            Y[i] = X[i] + corr_[i]
    # swing clearance: lift wherever the sole would go below the floor, spread smoothly, never into a contact
    for _ in range(4):
        req = np.array([0 if c[i] else max(0, 0.002 - sole_low(Y[i], PIT[i])) for i in range(N)])
        if req.max() < 1e-6: break
        w = max(2, N // 60); sm = np.array([req[(i + np.arange(-2 * w, 2 * w + 1)) % N].max() for i in range(N)])
        g = np.exp(-np.arange(-2 * w, 2 * w + 1) ** 2 / (2 * w * w)); g /= g.sum()
        lift = np.array([(sm[(i + np.arange(-2 * w, 2 * w + 1)) % N] * g).sum() for i in range(N)])
        Y[:, 1] += np.maximum(lift, req) * ~c
    return Y, c, anchor


def debounce_c(c, n):   # circular version of debounce
    if c.all() or not c.any(): return c
    sh = np.flatnonzero(c != np.roll(c, 1))[0]; r = debounce(np.roll(c, -sh), n); return np.roll(r, sh)


def ik2(H, A, a, b, Kref):
    d = A - H; L = np.linalg.norm(d); st = max(1.0, L / (a + b) * 1.0001); a2, b2 = a * st, b * st
    cosv = np.clip((a2 * a2 + L * L - b2 * b2) / (2 * a2 * L), -1, 1); al = np.arccos(cosv); u = d / L
    cand = [H + rot(u, s * al) * a2 for s in (1, -1)]
    return min(cand, key=lambda k: np.linalg.norm(k - Kref)), st


def page_data(name, B, segs):
    A, I, N, k, T = B['A'], B['I'], B['N'], B['k'], B['T']; fps_c = N / (k * T)
    S = project(A); tp = B['tpose']
    g = lambda n: S[:, I[n]]; g3 = lambda n: A[:, I[n]]
    floor_a = np.percentile(np.minimum(A[:, I['RightFoot'], 1], A[:, I['LeftFoot'], 1]), 3)   # flat ankle height
    yo = 0.07 - floor_a                                    # page: ankle 0.07 above the sole
    def pitch(s):   # true foot pitch (toes up +), zero where the foot lies flat: ankle and toe joints both at their lowest
        d = g3(s + 'ToeBase') - g3(s + 'Foot'); p = np.arctan2(d[:, 1], np.hypot(d[:, 0], d[:, 2]))
        ya, yt = g3(s + 'Foot')[:, 1], g3(s + 'ToeBase')[:, 1]
        flat = (ya - ya.min() < 0.02) & (yt - yt.min() < 0.02)
        return p - np.median(p[flat] if flat.sum() >= 3 else np.percentile(p, 90))
    out = dict(name=name, bpm=round(60 / T, 2), beat_s=round(T, 4), beats=k, cycle_s=round(k * T, 4), samples=N, view_deg=round(float(np.degrees(VIEW))),
               cycles=B['n_cycles'], spread_L=round(B['spread'], 4),
               touchdown_hz=round(float(np.sum([s['n_td'] for s in segs]) / np.sum([s['t1'] - s['t0'] for s in segs])), 2),
               clips=[dict(clip=s['clip'], t=[s['t0'], s['t1']], cycle_s=round(s['Tc'], 3), pose_r=round(s['rc'], 2), bpm=round(60 / s['T'], 1),
                           touchdown_hz=round(s['td_hz'], 2), shift=s['shift'], mirror=s['mirror'], r=round(s['r'], 3), cycles=len(s['cyc']), kept=len(s['kept'])) for s in segs])
    pel = g('Hips') + [0, yo]
    legs = []; stretch = 1
    for s in SIDES:
        hip = g(s + 'UpLeg') + [0, yo]; kn = g(s + 'Leg') + [0, yo]; an = g(s + 'Foot') + [0, yo]; pt = pitch(s)
        an2, con, anchor = lock_feet(an, pt, fps_c, N)
        knee = []
        for i in range(N):
            a = np.linalg.norm(kn[i] - hip[i]); b = np.linalg.norm(an[i] - kn[i])
            K, st = ik2(hip[i], an2[i], a, b, kn[i]); knee.append(K); stretch = max(stretch, st)
        legs.append(dict(hip=hip - pel, knee=np.array(knee), ankle=an2, pitch=pt, contact=con, anchor=anchor))
    out['knee_stretch_pct'] = round(100 * (stretch - 1), 2)
    T0 = project(tpose_local(tp, I)); t0 = lambda n: T0[I[n]]            # upright reference: the T-pose
    up0 = lambda a, b, d: ang_v(d) - ang_v(t0(b) - t0(a))
    sp = g('Spine'); nk = g('Spine1')            # lumbar: hips -> mid-back, thorax: mid-back -> neck base (Spine1 sits at the neck base)
    twist = np.degrees(np.unwrap(np.arctan2(*rel_yaw(A, I))))
    arms = []
    mid = (g('RightArm') + g('LeftArm')) / 2
    for s in SIDES:
        sh = g(s + 'Arm'); el = g(s + 'ForeArm'); wr = g(s + 'Hand')
        lu = np.linalg.norm(g3(s + 'ForeArm') - g3(s + 'Arm'), axis=1).mean(); lf = np.linalg.norm(g3(s + 'Hand') - g3(s + 'ForeArm'), axis=1).mean()
        arms.append(dict(sh=sh - mid, ua=(el - sh) * 0.37 / lu, fa=(wr - el) * 0.31 / lf))   # rig lengths, data direction and foreshortening
    r4 = lambda x: np.round(np.asarray(x, float), 4).tolist()
    out['curves'] = dict(
        # trunk as recorded (as in the run page); the rest skeleton's spine is not an upright reference. Head: relative to the T-pose.
        pel=r4(pel), lumbar=r4(ang_v(sp - g('Hips'))), thorax=r4(ang_v(nk - sp)),
        head=r4(up0('Head', 'Head_End', g('Head_End') - g('Head'))), twist=r4(np.radians(twist)),
        legs=[{k2: r4(v) if k2 != 'contact' else v.astype(int).tolist() for k2, v in L.items()} for L in legs],
        arms=[{k2: r4(v) for k2, v in a.items()} for a in arms])
    # summary numbers for the README
    con = np.array([L['contact'] for L in legs])
    out['stats'] = dict(pelvis_travel_L=round(float(np.ptp(pel[:, 1])), 3),                     # vertical, leg lengths
                        contact_pct=[round(100 * float(c.mean()), 1) for c in con], both_down_pct=round(100 * float((con[0] & con[1]).mean()), 1),
                        airborne_pct=round(100 * float((~con[0].astype(bool) & ~con[1].astype(bool)).mean()), 1),
                        touchdowns_per_cycle=int(sum(np.sum(c & ~np.roll(c, 1)) for c in con.astype(bool))))
    return out


def rel_yaw(A, I):   # shoulder line relative to hip line, about the vertical
    s = A[:, I['LeftArm']] - A[:, I['RightArm']]; h = A[:, I['LeftUpLeg']] - A[:, I['RightUpLeg']]
    a = np.arctan2(s[:, 2], s[:, 0]) - np.arctan2(h[:, 2], h[:, 0]); return np.sin(a), np.cos(a)


if __name__ == '__main__':
    res = {}
    for name, spec in STYLES.items():
        segs = [segment(*c) for c in spec]
        for s in segs:
            if s['Tc'] is None or s['rc'] < MIN_R: print(f"{name:10s} {s['clip']} {s['t0']:5.1f}-{s['t1']:5.1f}s  no repeating pattern (r={s['rc']:.2f}), skipped")
        segs = [s for s in segs if s['Tc'] is not None and s['rc'] >= MIN_R]
        k, amp = beats_per_cycle(segs)
        for s in segs:
            print(f"{name:10s} {s['clip']} {s['t0']:5.1f}-{s['t1']:5.1f}s  cycle {s['Tc']:.3f} s (pose r={s['rc']:.2f})  beat {s['T']*1000:4.0f} ms = {60/s['T']:5.1f} BPM  "
                  f"touchdowns {s['n_td']:3d} ({s['td_hz']:.2f} Hz)")
        print('  pelvis bounce by harmonic of the cycle', np.round(amp, 2), '-> beats per cycle', k)
        sel = POSE.get(name, {}); psegs = [s for s in segs if s['clip'].startswith(sel.get('clips', ('',)))]
        B = build(name, psegs, k, sel.get('top')); res[name] = page_data(name, B, psegs)
        res[name]['tempo_only'] = [dict(clip=s['clip'], t=[s['t0'], s['t1']], cycle_s=round(s['Tc'], 3), bpm=round(60 / s['T'], 1),
                                        touchdown_hz=round(s['td_hz'], 2)) for s in segs if s not in psegs]
        r = res[name]
        print(f"  => {r['bpm']} BPM, {r['beats']} beats/cycle ({r['cycle_s']} s), {r['cycles']} cycles, spread {r['spread_L']} L, knee stretch {r['knee_stretch_pct']} %, stats {r['stats']}")
        for c in r['clips']: print('    ', c)
    txt = json.dumps(res, separators=(',', ':')); (D / 'dance_cmu.json').write_text(txt)
    print('wrote', D / 'dance_cmu.json', round(len(txt) / 1024), 'KB')
    if '--embed' in sys.argv:                  # replace the const DANCE line of dance/index.html
        page = HERE.parent / 'dance' / 'index.html'; lines = page.read_text().split('\n')
        i = next(i for i, l in enumerate(lines) if l.startswith('const DANCE = ')); lines[i] = f'const DANCE = {txt};'
        page.write_text('\n'.join(lines)); print('embedded in', page)
