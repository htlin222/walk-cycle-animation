"""Normative fastball pitch from the Driveline OpenBiomechanics Project (OBP).

Driveline Baseball Research & Development, Boddy K. The OpenBiomechanics Project. https://www.openbiomechanics.org,
github.com/drivelineresearch/openbiomechanics (dataset-v1). Data licence CC BY-NC-SA 4.0: the curves this script
writes are a derived work and carry the same licence (non-commercial, share-alike, attribute OBP).
Fastballs on an instrumented mound; markers 360 Hz, force plates 1080 Hz (Visual3D, 20 Hz / 40 Hz low-pass).

Usage: python pitch_obp.py --download   (release assets, ≈ 310 MB zipped, checked against OBP's SHA-256 list, into analysis/obp/;
                                        needs the pure-Python C3D reader: pip install c3d)
       python pitch_obp.py [--embed]    (--embed also writes the result into pitch/index.html; --embed-only skips the analysis)
Output: analysis/data/normative_pitch_obp.json (embedded in pitch/index.html as const PITCH)

Per pitch:
  events   leg-lift onset (ON: lead ankle 2 cm above its starting height), peak knee height (PKH), foot contact
           (FC, 10 % bodyweight), foot plant (FP, 100 % bodyweight), max shoulder external rotation (MER),
           ball release (BR), max internal rotation (MIR) and END = BR + 200 ms (the recordings stop soon after)
  time     piecewise-linear normalisation between consecutive events, fixed samples per phase
  hand     left-handers are mirrored (y → -y) so every pitch is a right-hander's; OBP angles are already symmetric
  units    positions in body heights, origin = pivot ankle at leg-lift onset, x toward home plate, y toward first base,
           z up from the turf under the rubber (lab z = 0 is the plate top, turf ≈ 13 mm)
Averaged per pitcher first, then across pitchers. Rigid chains (hips from the pelvis centre, trunk, arms, head) average
segment directions and lengths, so limbs keep their length; pelvis centre, ankles and shoe soles average positions.
Planted feet are then pinned (a few mm of averaged creep removed, see main()), and knees re-solved by two-bone IK
between hip and ankle (bend plane from the averaged knee), so a planted foot stays exactly where it is.
Head (4 head-band markers) and shoes (heel, toe markers) come from the C3D files, joint centres from landmarks.csv,
angles and angular velocities from joint_angles.csv / joint_velos.csv, ground reaction force (bodyweights) from
force_plate.csv; peak values and stride length per pitch from OBP's poi_metrics.csv.
"""
import numpy as np, pandas as pd, json, pathlib, sys, hashlib, zipfile, urllib.request, warnings
HERE = pathlib.Path(__file__).parent
O = HERE / 'obp'
REL = 'https://github.com/drivelineresearch/openbiomechanics/releases/download/dataset-v1/'
RAW = 'https://raw.githubusercontent.com/drivelineresearch/openbiomechanics/44b98dae05cceb016f080ab39d105c85b8639084/baseball_pitching/data/'
ASSETS = {  # scripts/release_checksums.sha256 in the OBP repository
    'pitching_landmarks.zip': 'efcc078d5d8e77ed1fbf0b9f6a78f750c57a624165f71f30e34142b74db7ec22',
    'pitching_joint_angles.zip': 'b4c4854ffcc52a0f757e0b3a3c86acdc4a2fc2e50516a76e62aabdb916afed46',
    'pitching_joint_velos.zip': '5752f571b40acc4f02afc42dcfdb4b9eb191fcffd5fb25bc3c585e149941fb69',
    'pitching_force_plate.zip': 'f36a1722e23101be2387acc8f91ec38d2ee5d640388f688af7fd8fa52eef29ed',
    'pitching_c3d.zip': '2f5277dc63c7f7535fa4b15310d6f38b3f3b761e572896eec529854c8c920d29',
}
EV = ['ON', 'PKH', 'FC', 'FP', 'MER', 'BR', 'MIR', 'END']
K = [48, 60, 4, 20, 10, 10, 24]          # samples per phase (≈ 3–10 ms each; the 32 ms MER→BR gets 10)
TURF = 0.013                             # m, "average turf thickness ~0.5 inch" (OBP README)
FOLLOW = 0.200                           # s of data kept after release
GRIP = 0.05                              # m, ball centre ahead of the hand centre
PLATE, ZONE, MOUND = 18.2, 0.75, 0.254   # m: rubber → middle of the plate, strike-zone middle above the plate, rubber height
G = 9.81


def download():
    O.mkdir(exist_ok=True)
    for n, sha in ASSETS.items():
        p = O / n
        if not p.exists(): urllib.request.urlretrieve(REL + n, p); print(n)
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        if h != sha: sys.exit(f'{n}: checksum mismatch')
        zipfile.ZipFile(p).extractall(O)
    for n in ('metadata.csv', 'poi/poi_metrics.csv'):
        p = O / n.split('/')[-1]
        if not p.exists(): urllib.request.urlretrieve(RAW + n, p); print(n)


def read_c3d(path):
    import c3d                                             # pip install c3d (pure Python reader)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        r = c3d.Reader(open(path, 'rb'))
        lab = [l.strip() for l in r.point_labels]
        X = np.array([p[:, :3] for _, p, _ in r.read_frames()])
    X[(X == 0).all(2)] = np.nan                            # gaps are stored as zeros
    return lab, X


def fill(x):
    """linear fill of short gaps along time; None if more than 10 % is missing"""
    x = x.copy()
    for j in range(x.shape[1]):
        bad = np.isnan(x[:, j])
        if bad.mean() > 0.1: return None
        if bad.any(): x[bad, j] = np.interp(np.where(bad)[0], np.where(~bad)[0], x[~bad, j])
    return x


def unit(v): return v / np.linalg.norm(v, axis=-1, keepdims=True)


JC = {'rear_ankle': 'rear_ankle_jc', 'lead_ankle': 'lead_ankle_jc', 'rear_knee': 'rear_knee_jc', 'lead_knee': 'lead_knee_jc',
      'rear_hip': 'rear_hip', 'lead_hip': 'lead_hip', 'shoulder': 'shoulder_jc', 'elbow': 'elbow_jc', 'wrist': 'wrist_jc',
      'hand': 'hand_jc', 'glove_shoulder': 'glove_shoulder_jc', 'glove_elbow': 'glove_elbow_jc', 'glove_wrist': 'glove_wrist_jc',
      'glove_hand': 'glove_hand_jc', 'thorax_prox': 'thorax_prox', 'thorax_dist': 'thorax_dist', 'com': 'centerofmass'}
# rigid chains: child ← parent (directions and lengths averaged); everything else is an averaged position
CHAIN = {'rear_hip': 'pelvis', 'lead_hip': 'pelvis', 'thorax_dist': 'pelvis', 'thorax_prox': 'thorax_dist',
         'shoulder': 'thorax_prox', 'elbow': 'shoulder', 'wrist': 'elbow', 'hand': 'wrist',
         'glove_shoulder': 'thorax_prox', 'glove_elbow': 'glove_shoulder', 'glove_wrist': 'glove_elbow', 'glove_hand': 'glove_wrist',
         'head': 'thorax_prox', 'rear_knee': 'rear_hip', 'lead_knee': 'lead_hip'}
ANCHOR = ['pelvis', 'rear_ankle', 'lead_ankle', 'rear_heel', 'rear_ball', 'lead_heel', 'lead_ball', 'com']
# joint angles (deg) and angular velocities (deg/s), renamed to plain anatomical terms with OBP's sign conventions
ANG = {'pelvis_rotation': ('pelvis_angle_z', 1), 'pelvis_tilt': ('pelvis_angle_x', 1), 'pelvis_lateral': ('pelvis_angle_y', 1),
       'trunk_rotation': ('torso_angle_z', 1), 'trunk_flexion': ('torso_angle_x', 1), 'trunk_lateral': ('torso_angle_y', 1),
       'hip_shoulder_separation': ('torso_pelvis_angle_z', 1),
       'shoulder_external_rotation': ('shoulder_angle_z', 1), 'shoulder_abduction': ('shoulder_angle_y', -1),
       'shoulder_horizontal_abduction': ('shoulder_angle_x', 1), 'elbow_flexion': ('elbow_angle_x', 1),
       'elbow_pronation': ('elbow_angle_z', 1), 'wrist_extension': ('wrist_angle_x', 1),
       'glove_shoulder_abduction': ('glove_shoulder_angle_y', -1), 'glove_shoulder_horizontal_abduction': ('glove_shoulder_angle_x', 1),
       'glove_shoulder_external_rotation': ('glove_shoulder_angle_z', 1), 'glove_elbow_flexion': ('glove_elbow_angle_x', 1),
       'lead_hip_flexion': ('lead_hip_angle_x', -1), 'lead_hip_abduction': ('lead_hip_angle_y', 1), 'lead_hip_external_rotation': ('lead_hip_angle_z', 1),
       'lead_knee_flexion': ('lead_knee_angle_x', 1), 'lead_ankle_dorsiflexion': ('lead_ankle_angle_x', 1),
       'rear_hip_flexion': ('rear_hip_angle_x', -1), 'rear_hip_abduction': ('rear_hip_angle_y', 1), 'rear_hip_external_rotation': ('rear_hip_angle_z', 1),
       'rear_knee_flexion': ('rear_knee_angle_x', 1), 'rear_ankle_dorsiflexion': ('rear_ankle_angle_x', 1)}
VEL = {'pelvis_rotation_velocity': ('pelvis_velo_z', 1), 'trunk_rotation_velocity': ('torso_velo_z', 1),
       'shoulder_internal_rotation_velocity': ('shoulder_velo_z', 1), 'elbow_extension_velocity': ('elbow_velo_x', 1)}   # OBP: IR +, extension +
GRF = {'rear_vertical': ('rear_force_z', 1), 'lead_vertical': ('lead_force_z', 1), 'rear_push': ('rear_force_x', 1), 'lead_brake': ('lead_force_x', 1)}
POI = {'pitch_speed_mph': 'pitch_speed_mph', 'max_shoulder_external_rotation': 'max_shoulder_external_rotation',
       'stride_length_pct_height': 'stride_length', 'max_pelvis_rotation_velocity': 'max_pelvis_rotational_velo',
       'max_trunk_rotation_velocity': 'max_torso_rotational_velo', 'max_hip_shoulder_separation': 'max_rotation_hip_shoulder_separation',
       'max_shoulder_internal_rotation_velocity': 'max_shoulder_internal_rotational_velo', 'max_elbow_extension_velocity': 'max_elbow_extension_velo',
       'elbow_flexion_fp': 'elbow_flexion_fp', 'shoulder_abduction_fp': 'shoulder_abduction_fp', 'shoulder_external_rotation_fp': 'shoulder_external_rotation_fp',
       'trunk_flexion_br': 'torso_anterior_tilt_br', 'trunk_lateral_br': 'torso_lateral_tilt_br', 'lead_knee_extension_fp_to_br': 'lead_knee_extension_from_fp_to_br',
       'arm_slot': 'arm_slot', 'stride_angle': 'stride_angle', 'max_cog_velocity_x': 'max_cog_velo_x',
       'pelvis_to_trunk_peak_ms_poi': 'timing_peak_torso_to_peak_pelvis_rot_velo', 'elbow_varus_moment': 'elbow_varus_moment', 'lead_grf_z_max': 'lead_grf_z_max', 'rear_grf_z_max': 'rear_grf_z_max'}


def grid(knots):
    u = [np.linspace(a, b, k + 1)[:-1] for a, b, k in zip(knots, knots[1:], K)]
    return np.concatenate(u + [[knots[-1]]])


def pitch(sp, d, a, v, f, m, poi, lab, X):
    """one pitch → dict of resampled curves, or a reason string"""
    t = d.time.values; e = d.iloc[0]
    lefty = poi.p_throws == 'L'; H = m.session_height_m; W = m.session_mass_kg * G
    R, L = ('L', 'R') if lefty else ('R', 'L')
    s = np.array([1, -1, 1]) if lefty else np.ones(3)                       # mirror lefties into right-handers
    P = {k: d[[c + '_x', c + '_y', c + '_z']].values * s for k, c in JC.items()}
    c = lambda n: fill(X[:, lab.index(n)] * s) if n in lab else None
    mk = {'rear_heel': c(R + 'HEE'), 'rear_toe': c(R + 'TOE'), 'lead_heel': c(L + 'HEE'), 'lead_toe': c(L + 'TOE'),
          'lfhd': c('LFHD'), 'rfhd': c('RFHD'), 'lbhd': c('LBHD'), 'rbhd': c('RBHD')}
    if any(mk[k] is None for k in ('rear_heel', 'rear_toe', 'lead_heel', 'lead_toe')): return 'foot markers missing'
    if len(X) != len(t): return 'c3d length differs'
    # leg-lift onset: lead ankle 2 cm above where it started; the foot has to start on the ground
    z = P['lead_ankle'][:, 2]; ipk = np.searchsorted(t, e.pkh_time)
    if z[0] > P['rear_ankle'][0, 2] + 0.03 or ipk < 10: return 'starts mid leg lift'
    base = np.median(z[t < 0.05]); up = np.where(z[:ipk] < base + 0.02)[0]
    if not len(up) or t[up[-1]] < 0.03: return 'starts mid leg lift'
    kn = [t[up[-1]], e.pkh_time, e.fp_10_time, e.fp_100_time, e.MER_time, e.BR_time, e.MIR_time, e.BR_time + FOLLOW]
    if np.isnan(kn).any() or not np.all(np.diff(kn) > 0): return 'events missing or out of order'
    if kn[-1] > t[-1]: return f'recording ends < {FOLLOW*1000:.0f} ms after release'
    u = grid(kn)
    o = P['rear_ankle'][up[-1]].copy(); o[2] = TURF                         # origin: pivot ankle at onset, turf level
    rs = lambda x: np.stack([np.interp(u, t, x[:, j]) for j in range(3)], 1)
    out = {k: (rs(x) - o) / H for k, x in P.items()}
    out['pelvis'] = (out['rear_hip'] + out['lead_hip']) / 2
    # head: centre of the four head-band markers, facing forehead-ward, up = normal of the band
    if all(mk[k] is not None for k in ('lfhd', 'rfhd', 'lbhd', 'rbhd')):
        fh = rs((mk['lfhd'] + mk['rfhd']) / 2); bh = rs((mk['lbhd'] + mk['rbhd']) / 2)
        out['head'] = ((fh + bh) / 2 - o) / H
        fr = unit(fh - bh); upv = unit(np.cross(rs(mk['rfhd'] - mk['lbhd']), rs(mk['lfhd'] - mk['rbhd'])))
        if np.median(upv[:, 2]) < 0: upv = -upv                             # (mirroring flips the cross product)
        out['head_front'], out['head_up'] = fr, unit(upv - (upv * fr).sum(1, keepdims=True) * fr)
    # shoes: sole points under the heel marker and under the toe marker (≈ ball of the foot). The foot frame has no roll:
    # forward = heel → toe, up = perpendicular to it in the vertical plane. Each marker's height above the sole is read
    # at onset, when both feet are flat on the turf (the ankle centre lies too close to the heel–toe line to set "up").
    i0 = up[-1]
    for side in ('rear', 'lead'):
        hz, tz = mk[side + '_heel'][i0, 2] - TURF, mk[side + '_toe'][i0, 2] - TURF
        Hh = (rs(mk[side + '_heel']) - o) / H; T = (rs(mk[side + '_toe']) - o) / H
        ef = unit(T - Hh); uf = unit(np.cross(np.cross(ef, [0, 0, 1]), ef))
        out[side + '_heel'] = Hh - uf * hz / H; out[side + '_ball'] = T - uf * tz / H
    # foot plant has to put the lead foot down well ahead (a few sessions have swapped or mislabelled foot data)
    ifp = np.searchsorted(t, e.fp_100_time)
    if z[ifp] > base + 0.03 or P['lead_ankle'][ifp, 0] - P['rear_ankle'][i0, 0] < 0.4 * H: return 'lead foot not down at foot plant'
    # ball: hand velocity at release (direction only; speed is the radar speed)
    ib = np.searchsorted(t, e.BR_time)
    vh = (P['hand'][ib + 1] - P['hand'][ib - 1]) / (t[ib + 1] - t[ib - 1])
    ang = {k: np.interp(u, t, a[col].values * sg) for k, (col, sg) in ANG.items()}
    for k in ('pelvis_rotation', 'trunk_rotation'): ang[k] = np.degrees(np.unwrap(np.radians(ang[k])))
    vf = lambda col: fill(v[[col]].values)[:, 0]                          # the last frame of a velocity table can be empty
    vel = {k: np.interp(u, v.time.values, vf(col) * sg) for k, (col, sg) in VEL.items()}
    grf = {k: np.interp(u, f.time.values, f[col].values * sg / W) for k, (col, sg) in GRF.items()}
    tv = t[(t >= kn[2] - 0.1) & (t <= kn[5] + 0.05)]                       # peak angular velocities, FC − 100 ms … BR + 50 ms
    pk = lambda col: tv[np.argmax(np.interp(tv, v.time.values, vf(col)))] - e.BR_time
    return dict(user=m.user, lefty=bool(lefty), H=H, mass=m.session_mass_kg, age=m.age_yrs, level=m.playing_level,
                knots=np.array(kn) - e.BR_time, pos=out, ang=ang, vel=vel, grf=grf, hand_v=vh, hand_speed=np.linalg.norm(vh),
                t_pelvis_peak=pk('pelvis_velo_z'), t_trunk_peak=pk('torso_velo_z'),
                poi={k: poi[c] for k, c in POI.items()})


def average(items):
    """positions: anchored points averaged, chained points rebuilt from averaged directions × averaged lengths"""
    out = {}
    for k in ANCHOR: out[k] = np.mean([it[k] for it in items], 0)
    dirs, lens = {}, {}
    for ch, pa in CHAIN.items():
        dv = [it[ch] - it[pa] for it in items if ch in it]
        if not dv: continue
        dirs[ch] = unit(np.mean([unit(x) for x in dv], 0)); lens[ch] = np.mean([np.linalg.norm(x, axis=1) for x in dv], 0)
    for ch in ['rear_hip', 'lead_hip', 'thorax_dist', 'thorax_prox', 'shoulder', 'elbow', 'wrist', 'hand',
               'glove_shoulder', 'glove_elbow', 'glove_wrist', 'glove_hand', 'head', 'rear_knee', 'lead_knee']:
        if ch in dirs: out[ch] = out[CHAIN[ch]] + dirs[ch] * lens[ch][:, None]
    if not any('head_front' in it for it in items): return out | lengths(items)
    for k in ('head_front', 'head_up'): out[k] = unit(np.mean([it[k] for it in items if k in it], 0))
    out['head_up'] = unit(out['head_up'] - (out['head_up'] * out['head_front']).sum(1, keepdims=True) * out['head_front'])
    return out | lengths(items)


def lengths(items):
    """thigh and shank lengths (constant per leg), carried up for the knee solve"""
    L = {}
    for sd in ('rear', 'lead'):
        for seg, a, b in (('_thigh', '_hip', '_knee'), ('_shank', '_knee', '_ankle')):
            L[sd + seg] = np.mean([it[sd + seg] if sd + seg in it else np.linalg.norm(it[sd + b] - it[sd + a], axis=1).mean() for it in items])
    return L


def knee_ik(hip, ankle, knee_guess, l1, l2):
    d = ankle - hip; D = np.linalg.norm(d, axis=1); e = d / D[:, None]
    Dc = np.minimum(D, (l1 + l2) * 0.9995)
    a = (l1 ** 2 - l2 ** 2 + Dc ** 2) / (2 * Dc); h = np.sqrt(np.maximum(l1 ** 2 - a ** 2, 0))
    g = knee_guess - hip; n = unit(g - (g * e).sum(1, keepdims=True) * e)
    return hip + e * a[:, None] + n * h[:, None], int((D > Dc).sum())


def main():
    meta = pd.read_csv(O / 'metadata.csv').set_index('session_pitch')
    poi = pd.read_csv(O / 'poi_metrics.csv').set_index('session_pitch')
    print('reading tables …')
    LM = pd.read_csv(O / 'landmarks.csv'); JA = pd.read_csv(O / 'joint_angles.csv')
    JV = pd.read_csv(O / 'joint_velos.csv'); FP = pd.read_csv(O / 'force_plate.csv')
    JA, JV, FP = (dict(tuple(x.groupby('session_pitch'))) for x in (JA, JV, FP))
    res, why = [], {}
    for sp, d in LM.groupby('session_pitch'):
        m = meta.loc[sp]
        if sp not in JA or sp not in JV or sp not in FP: why['table missing'] = why.get('table missing', 0) + 1; continue
        lab, X = read_c3d(O / 'c3d' / f'{m.user:06d}' / m.filename_new)
        r = pitch(sp, d.sort_values('time'), JA[sp].sort_values('time'), JV[sp].sort_values('time'), FP[sp].sort_values('time'),
                  m, poi.loc[sp], lab, X)
        if isinstance(r, str): why[r] = why.get(r, 0) + 1
        else: res.append(r)
    print('excluded:', why)
    users = sorted({r['user'] for r in res})
    per = []                                                               # per-pitcher means first
    for u_ in users:
        rr = [r for r in res if r['user'] == u_]
        pos = average([r['pos'] for r in rr])
        per.append(dict(n=len(rr), lefty=rr[0]['lefty'], H=rr[0]['H'], mass=rr[0]['mass'], age=rr[0]['age'], level=rr[0]['level'],
                        knots=np.mean([r['knots'] for r in rr], 0), pos=pos,
                        **{g: {k: np.mean([r[g][k] for r in rr], 0) for k in rr[0][g]} for g in ('ang', 'vel', 'grf')},
                        hand_v=np.mean([r['hand_v'] for r in rr], 0), hand_speed=np.mean([r['hand_speed'] for r in rr]),
                        t_pelvis_peak=np.mean([r['t_pelvis_peak'] for r in rr]), t_trunk_peak=np.mean([r['t_trunk_peak'] for r in rr]),
                        poi={k: np.nanmean([r['poi'][k] for r in rr]) for k in POI}))
    N = len(per); Hm = np.mean([p['H'] for p in per])
    pos = average([p['pos'] for p in per])
    knots = np.mean([p['knots'] for p in per], 0); knots_sd = np.std([p['knots'] for p in per], 0)
    tt = grid(knots)                                                       # sample times (s, release = 0) at the mean event times
    idx = np.concatenate([[0], np.cumsum(K)]); iFC, iFP, iEND = idx[2], idx[3], idx[7]
    # floor: turf at z = 0 under the rubber, flat for 6 in (0.15 m) in front of it, then sloping down to the landing spot
    # (mean lead-heel height after foot plant), flat beyond. pitch/index.html draws the same profile.
    x_flat = (min(pos['rear_heel'][0, 0], pos['rear_ball'][0, 0]) * Hm - 0.05 + 0.15) / Hm
    x_land, z_land = pos['lead_heel'][iFP:iEND + 1, 0].mean(), pos['lead_heel'][iFP:iEND + 1, 2].mean()
    floor = lambda x: np.interp(x, [x_flat, x_land], [0, z_land])
    # planted feet: the averaged contact point still creeps by a few mm, so each foot (shoe and ankle together) gets a
    # small translation that pins it: the pivot foot's ball from onset until the drag starts (contact point 2 cm from
    # where it began; released over 6 samples), the lead heel from foot plant to the end (faded in from foot contact).
    # Outside a hold, a foot whose sole dips under the mound surface is lifted onto it (whole foot); inside a hold only the
    # other sole point is (the held one is on the surface already). Knees are solved afterwards.
    def hold(name, i0, i1, ramp_in, ramp_out):
        p = pos[name]; ref = p[i1 if ramp_in else i0].copy(); ref[2] = floor(ref[0]); c = np.zeros_like(p); w = np.zeros(len(p))
        for i in range(len(tt)):
            w[i] = (np.clip((i - i0 + 1) / (ramp_in + 1), 0, 1) if i >= i0 else 0) * (np.clip(1 - (i - i1) / ramp_out, 0, 1) if i > i1 else 1)
            c[i] = w[i] * (ref - p[i])
        return c, w
    b = pos['rear_ball']; i_drag = int(np.argmax(np.linalg.norm(b[:, :2] - b[0, :2], axis=1) > 0.02 / Hm))
    corr = {'rear': hold('rear_ball', 0, i_drag, 0, 6), 'lead': hold('lead_heel', iFC, iEND, iFP - iFC, 1)}
    for sd, (c, w) in corr.items():
        for pt in ('ankle', 'heel', 'ball'): pos[f'{sd}_{pt}'] = pos[f'{sd}_{pt}'] + c
        lift = np.maximum(0, np.maximum(floor(pos[sd + '_heel'][:, 0]) - pos[sd + '_heel'][:, 2], floor(pos[sd + '_ball'][:, 0]) - pos[sd + '_ball'][:, 2]))
        lift[w >= 1] = 0
        for pt in ('ankle', 'heel', 'ball'): pos[f'{sd}_{pt}'][:, 2] += lift
        for pt in ('heel', 'ball'): pos[f'{sd}_{pt}'][:, 2] = np.maximum(pos[f'{sd}_{pt}'][:, 2], floor(pos[f'{sd}_{pt}'][:, 0]))
        corr[sd] = [round(float(np.linalg.norm(c[:, :2], axis=1).max() * Hm * 1000), 1), round(float(np.abs(c[:, 2]).max() * Hm * 1000), 1),
                    round(float(lift.max() * Hm * 1000), 1)]
    clamp = 0
    for sd in ('rear', 'lead'):
        pos[sd + '_knee'], c_ = knee_ik(pos[sd + '_hip'], pos[sd + '_ankle'], pos[sd + '_knee'], pos[sd + '_thigh'], pos[sd + '_shank']); clamp += c_
    print('foot hold (mm: horizontal, vertical, lift onto the mound):', corr, ' pivot drag starts at', round(tt[i_drag] * 1000), 'ms')
    # ball: the flight is not in the data. It leaves the fingers (GRIP ahead of the hand centre, along the forearm) at the
    # mean radar speed, aimed down the x axis at the middle of the strike zone, gravity only (a four-seamer's backspin
    # lift is left out). The hand's own velocity at release points 17° lower; the ball rolls off the fingertips.
    mph = np.mean([p['poi']['pitch_speed_mph'] for p in per]); v_ms = mph * 0.44704
    ib = idx[5]; hand, wr = pos['hand'][ib] * Hm, pos['wrist'][ib] * Hm
    rel = hand + unit(hand - wr) * GRIP
    rubber = min(pos['rear_heel'][0, 0], pos['rear_ball'][0, 0]) * Hm - 0.05      # rubber's front edge, behind the pivot foot
    tgt = np.array([rubber + PLATE, rel[1], ZONE - MOUND])
    dx, dz = tgt[0] - rel[0], tgt[2] - rel[2]
    lo_, hi_ = -0.3, 0.3
    for _ in range(60):                                                    # launch angle by bisection
        th = (lo_ + hi_) / 2; T_ = dx / (v_ms * np.cos(th))
        if v_ms * np.sin(th) * T_ - G * T_ ** 2 / 2 > dz: hi_ = th
        else: lo_ = th
    hd = unit(np.mean([unit(p['hand_v']) for p in per], 0))
    # summary
    S = lambda xs: dict(mean=round(float(np.mean(xs)), 2), sd=round(float(np.std(xs)), 2))
    summ = {k: S([p['poi'][k] * (1000 if k.endswith('_ms_poi') else 1) for p in per]) for k in POI}
    summ['pelvis_peak_ms_from_br'] = S([p['t_pelvis_peak'] * 1000 for p in per])
    summ['trunk_peak_ms_from_br'] = S([p['t_trunk_peak'] * 1000 for p in per])
    summ['pelvis_to_trunk_peak_ms'] = S([(p['t_trunk_peak'] - p['t_pelvis_peak']) * 1000 for p in per])
    summ['trunk_after_pelvis_pitchers'] = int(sum(p['t_trunk_peak'] > p['t_pelvis_peak'] for p in per))
    summ['hand_speed_br_ms'] = S([p['hand_speed'] for p in per])
    summ['height_m'] = S([p['H'] for p in per]); summ['mass_kg'] = S([p['mass'] for p in per]); summ['age_yrs'] = S([p['age'] for p in per])
    ang = {k: np.mean([p['ang'][k] for p in per], 0) for k in ANG}
    vel = {k: np.mean([p['vel'][k] for p in per], 0) for k in VEL}
    grf = {k: np.mean([p['grf'][k] for p in per], 0) for k in GRF}
    # measured from the averaged figure
    st = pos['lead_ankle'][idx[3], :2] - pos['rear_ankle'][0, :2]
    summ['stride_ankle_pct_height_avg_figure'] = round(float(np.linalg.norm(st) * 100), 1)
    summ['release_height_m'] = round(float(pos['hand'][idx[5], 2] * Hm), 3)
    summ['release_ahead_of_pivot_ankle_m'] = round(float(pos['hand'][idx[5], 0] * Hm), 3)
    summ['peak_shoulder_er_avg_curve'] = round(float(ang['shoulder_external_rotation'].max()), 1)
    summ['peak_pelvis_velocity_avg_curve'] = round(float(vel['pelvis_rotation_velocity'].max()), 0)
    summ['peak_trunk_velocity_avg_curve'] = round(float(vel['trunk_rotation_velocity'].max()), 0)
    summ['landing_drop_cm'] = round(float(-z_land * Hm * 100), 1)
    summ['mound_slope_pct'] = round(float(-z_land / (x_land - x_flat) * 100), 1)
    summ['pivot_drag_starts_ms'] = round(float(tt[i_drag] * 1000))
    summ['foot_hold_mm'] = corr
    r3 = lambda a, n=3: [[round(float(x), n) for x in p] for p in a]       # 0.001 height ≈ 2 mm; soles 0.2 mm
    r1 = lambda a: [round(float(x), 1) for x in a]
    out = dict(
        source='Driveline OpenBiomechanics Project (OBP), baseball_pitching dataset-v1, CC BY-NC-SA 4.0',
        licence='CC BY-NC-SA 4.0 (derived from OBP data)',
        pitchers=N, pitches=len(res), lefties_mirrored=int(sum(p['lefty'] for p in per)),
        levels={k: sum(p['level'] == k for p in per) for k in sorted({p['level'] for p in per})},
        excluded=why, height_m=round(float(Hm), 4),
        events=dict(names=EV, idx=[int(i) for i in idx], t_ms=[round(round(float(x), 5) * 1000, 2) for x in knots], sd_ms=r1(knots_sd * 1000)),
        t=[round(float(x), 5) for x in tt],
        pos={k: r3(pos[k]) for k in ['pelvis', 'rear_hip', 'lead_hip', 'rear_knee', 'lead_knee', 'rear_ankle', 'lead_ankle',
                                     'rear_heel', 'rear_ball', 'lead_heel', 'lead_ball', 'thorax_dist', 'thorax_prox',
                                     'shoulder', 'elbow', 'wrist', 'hand', 'glove_shoulder', 'glove_elbow', 'glove_wrist', 'glove_hand',
                                     'head', 'head_front', 'head_up', 'com']} | {k: r3(pos[k], 4) for k in ('rear_heel', 'rear_ball', 'lead_heel', 'lead_ball')},
        floor=dict(x_flat=round(float(x_flat), 4), x_land=round(float(x_land), 4), z_land=round(float(z_land), 4), i_drag=i_drag),
        ball=dict(speed_mph=round(float(mph), 1), speed_ms=round(float(v_ms), 2), grip_m=GRIP, release=[round(float(x / Hm), 4) for x in rel],
                  launch_deg=round(float(np.degrees(th)), 2), flight_s=round(float(T_), 3), plate_x=round(float(tgt[0] / Hm), 3),
                  hand_dir=[round(float(x), 4) for x in hd], hand_speed_ms=round(float(np.mean([p['hand_speed'] for p in per])), 2)),
        angles={k: r1(v) for k, v in ang.items()}, velocities={k: r1(v) for k, v in vel.items()},
        grf_bw={k: [round(float(x), 3) for x in v] for k, v in grf.items()},
        summary=summ)
    json.dump(out, open(HERE / 'data' / 'normative_pitch_obp.json', 'w'), separators=(',', ':'))
    print(f"{N} pitchers, {len(res)} pitches ({out['lefties_mirrored']} left-handed pitchers mirrored), levels {out['levels']}, "
          f"height {Hm:.3f} m, knee IK clamped on {clamp} samples")
    print('events (ms from release):', dict(zip(EV, out['events']['t_ms'])), ' sd', out['events']['sd_ms'])
    for k, v in summ.items(): print(f'  {k}: {v}')
    print('ball', out['ball'])


def embed():
    """write the JSON into the `const PITCH = …;` line of pitch/index.html"""
    page = HERE.parent / 'pitch' / 'index.html'
    data = (HERE / 'data' / 'normative_pitch_obp.json').read_text()
    lines = page.read_text().split('\n')
    i = next(i for i, l in enumerate(lines) if l.startswith('const PITCH = '))
    lines[i] = 'const PITCH = ' + data + ';'
    page.write_text('\n'.join(lines)); print('embedded in', page)


if __name__ == '__main__':
    if '--download' in sys.argv: download()
    if '--embed-only' not in sys.argv: main()
    if '--embed' in sys.argv or '--embed-only' in sys.argv: embed()
