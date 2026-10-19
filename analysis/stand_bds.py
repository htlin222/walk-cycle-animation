"""Normative quiet standing (postural sway) from the public human balance data set (BDS).

Santos DA, Duarte M (2016). A public data set of human balance evaluations. PeerJ 4:e2648.
figshare 10.6084/m9.figshare.3394432 (BDS.zip, CC-BY-4.0). 163 adults standing still for 60 s on an AMTI force
platform, 100 Hz, already low-pass filtered (10 Hz, 4th-order zero-lag Butterworth). COPx = anterior (+) / posterior,
COPy = medio-lateral (right +), in cm. Four conditions x 3 trials: eyes open / closed, firm floor / 6 cm foam pad.

Usage: python stand_bds.py             (reads analysis/bds/BDS.zip; extracted BDS*.txt next to it also work)
       download it with:  python stand_bds.py --download      (~375 MB)
Output: analysis/data/normative_stand_bds.json

Subjects: healthy young adults = age 18-40, no disability, no fall in the last 12 months, no vestibular diagnosis.
Per trial (mean removed): COP and COM RMS, range and mean velocity (AP, ML), median / 80 % power frequency,
and the 60 s Hann-windowed periodogram. Per condition: median and IQR over subjects (each subject = mean of
its trials) and the mean periodogram over all trials, which the page synthesises sway from.

COM from COP: inverted pendulum about the ankles (Winter et al. 1998; Caron et al. 1997, Brenière 1996):
  COP - COM = -(I / (m g h)) COM''   ->   COM(f) = COP(f) * w0^2 / (w0^2 + (2 pi f)^2),  w0^2 = m g h / I
h = COM height above the ankle = 0.55 H - 0.039 H (whole-body COM, Winter 2009; lateral malleolus 0.039 H),
I = m (h^2 + rho^2), rho = 0.23 H the whole-body radius of gyration about the COM (Santschi et al. 1963,
~12 kg m^2 standing). This gives w0 ~ 3.1 rad/s (0.49 Hz) per subject: the COM is the COP low-passed at ~0.5 Hz.
The same pendulum is used for ML sway (load / unload strategy, Winter 1995).
"""
import numpy as np, json, csv, pathlib, sys, zipfile, urllib.request, io
from scipy.signal import periodogram, welch, decimate
HERE = pathlib.Path(__file__).parent
B = HERE / 'bds'
FS, N, G = 100.0, 6000, 9.81
CONDS = {'open_firm': ('Open', 'Firm'), 'closed_firm': ('Closed', 'Firm'), 'open_foam': ('Open', 'Foam'), 'closed_foam': ('Closed', 'Foam')}
FMAX = 5.0                                   # spectrum kept up to 5 Hz (the data are filtered at 10 Hz)


def download():
    B.mkdir(exist_ok=True)
    meta = json.load(urllib.request.urlopen('https://api.figshare.com/v2/articles/3394432'))
    for f in meta['files']:
        p = B / f['name']
        if not p.exists(): urllib.request.urlretrieve(f['download_url'], p); print(f['name'])


ZIP = zipfile.ZipFile(B / 'BDS.zip') if (B / 'BDS.zip').exists() else None
def read(name):
    t = ZIP.read(name).decode() if ZIP else open(B / name).read()
    return t


def subjects():
    rows = list(csv.DictReader(io.StringIO(read('BDSinfo.txt')), delimiter='\t'))
    ok = lambda r: (18 <= float(r['Age']) <= 40 and r['Disability'] == 'No' and r['Falls12m'] == '0'
                    and 'Labyrinth' not in r['Illness2'] and 'syncope' not in r['Illness2'])
    return [r for r in rows if ok(r)], len({r['Subject'] for r in rows if r['AgeGroup'] == 'Young'})


def pendulum(H):
    h = (0.55 - 0.039) * H; rho = 0.23 * H
    return h, np.sqrt(G * h / (h * h + rho * rho))


def com(x, w0):
    """COP -> COM with the inverted-pendulum low-pass, zero phase, mirror-padded against wrap-around."""
    y = np.concatenate([x, x[::-1]]); f = np.fft.rfftfreq(len(y), 1 / FS); w = 2 * np.pi * f
    return np.fft.irfft(np.fft.rfft(y) * w0 ** 2 / (w0 ** 2 + w ** 2), len(y))[:len(x)]


def fq(x, p):
    f, P = welch(x, FS, nperseg=2000); m = (f > 0) & (f <= FMAX); c = np.cumsum(P[m]); return float(np.interp(p * c[-1], c, f[m]))


def stats(x):
    return dict(rms=float(np.sqrt(np.mean(x ** 2))), range=float(np.ptp(x)), vel=float(np.mean(np.abs(np.diff(x))) * FS),
                f50=fq(x, 0.5), f80=fq(x, 0.8))


def trial(r):
    X = np.loadtxt(io.StringIO(read(r['Trial'] + '.txt')), skiprows=1)
    if len(X) < N: return None
    ap, ml = X[:N, 7] - X[:N, 7].mean(), X[:N, 8] - X[:N, 8].mean()
    H = float(r['Height']) / 100; h, w0 = pendulum(H)
    cap, cml = com(ap, w0), com(ml, w0)
    f, Pap = periodogram(ap, FS, window='hann'); _, Pml = periodogram(ml, FS, window='hann')
    out = dict(subject=r['Subject'], trial=r['Trial'], H=H, h=h, w0=w0, ap=ap, ml=ml, cap=cap, cml=cml, f=f, Pap=Pap, Pml=Pml)
    for k, x in (('cop_ap', ap), ('cop_ml', ml), ('com_ap', cap), ('com_ml', cml)): out[k] = stats(x)
    out['res_vel'] = float(np.mean(np.hypot(np.diff(ap), np.diff(ml))) * FS)
    out['angle_rms'] = float(np.degrees(np.sqrt(np.mean(cap ** 2)) / 100 / h))        # sagittal body sway angle
    return out


def summary(T, key, field):
    by = {}
    for t in T: by.setdefault(t['subject'], []).append(t[key][field] if field else t[key])
    v = np.array([np.mean(a) for a in by.values()])
    return [round(float(q), 4) for q in np.percentile(v, [25, 50, 75])]


def main():
    rows, n_young = subjects()
    H_all = np.array([float(r['Height']) / 100 for r in {r['Subject']: r for r in rows}.values()])
    L = 0.491 * H_all.mean()                                     # leg length (Winter thigh + shank), as in run_rbds.py
    hL, w0m = pendulum(H_all.mean()); hL /= L
    out = dict(source='Santos & Duarte 2016, PeerJ 4:e2648, figshare 3394432 (CC-BY-4.0)',
               selection='age 18-40, no disability, no falls in 12 months, no vestibular diagnosis',
               young_group=n_young, subjects=len(H_all), age=[round(float(np.min([float(r['Age']) for r in rows])), 1), round(float(np.max([float(r['Age']) for r in rows])), 1)],
               height_m=round(float(H_all.mean()), 3), leg_m=round(float(L), 4),
               pendulum=dict(h_m=round(float(hL * L), 3), h_L=round(float(hL), 4), w0=round(float(w0m), 3), f0=round(float(w0m / 2 / np.pi), 3),
                             method='COM(f) = COP(f) w0^2/(w0^2+w^2); w0^2 = g h/(h^2+rho^2), h = 0.511 H, rho = 0.23 H'),
               conditions={})
    for name, (vis, surf) in CONDS.items():
        T = [t for t in (trial(r) for r in rows if r['Vision'] == vis and r['Surface'] == surf) if t]
        f = T[0]['f']; m = (f > 0) & (f <= FMAX + 1e-9)
        Pap, Pml = np.mean([t['Pap'] for t in T], 0)[m], np.mean([t['Pml'] for t in T], 0)[m]
        df = f[1] - f[0]
        C = dict(trials=len(T), subjects=len({t['subject'] for t in T}))
        for k in ('cop_ap', 'cop_ml', 'com_ap', 'com_ml'):
            C[k] = {fl: summary(T, k, fl) for fl in ('rms', 'range', 'vel', 'f50', 'f80')}
        C['cop_res_vel'] = summary(T, 'res_vel', None); C['angle_rms_deg'] = summary(T, 'angle_rms', None)
        # power-averaged RMS: what a synthesis from the mean spectrum reproduces
        C['psd_rms'] = dict(cop_ap=float(np.sqrt(np.sum(Pap) * df)), cop_ml=float(np.sqrt(np.sum(Pml) * df)))
        C['psd'] = dict(df=float(df), unit='cm^2/Hz, bins k*df for k = 1..%d' % m.sum(),
                        ap=[float('%.4g' % p) for p in Pap], ml=[float('%.4g' % p) for p in Pml])
        # representative trial: COP RMS (AP, ML) closest to the condition medians, 10 Hz
        md = np.array([C['cop_ap']['rms'][1], C['cop_ml']['rms'][1]])
        rep = min(T, key=lambda t: np.sum(np.log(np.array([t['cop_ap']['rms'], t['cop_ml']['rms']]) / md) ** 2))
        C['representative'] = dict(trial=rep['trial'], fs=10, unit='cm', **{k: [round(float(v), 3) for v in decimate(rep[k], 10, ftype='fir')]
                                                                             for k in ('ap', 'ml', 'cap', 'cml')})
        out['conditions'][name] = C
        q = lambda k, fl: '%.2f [%.2f-%.2f]' % (C[k][fl][1], C[k][fl][0], C[k][fl][2])
        print(f"{name:12s} n={C['subjects']} subj / {C['trials']} trials | COP AP rms {q('cop_ap','rms')} cm range {q('cop_ap','range')} vel {q('cop_ap','vel')} cm/s "
              f"f50 {C['cop_ap']['f50'][1]:.2f} Hz | COP ML rms {q('cop_ml','rms')} vel {q('cop_ml','vel')} | COM AP rms {q('com_ap','rms')} ML {q('com_ml','rms')} cm "
              f"vel {q('com_ap','vel')} | sway angle {C['angle_rms_deg'][1]:.2f} deg | psd rms AP {C['psd_rms']['cop_ap']:.2f} ML {C['psd_rms']['cop_ml']:.2f} | rep {rep['trial']}")
    print(f"subjects {out['subjects']} (of {n_young} 'Young'), height {H_all.mean():.3f} m, leg {L:.3f} m, pendulum h {hL*L:.3f} m = {hL:.3f} L, "
          f"f0 {w0m/2/np.pi:.3f} Hz")
    json.dump(out, open(HERE / 'data' / 'normative_stand_bds.json', 'w'))
    # the part embedded in stand/index.html (const STAND): spectra, pendulum and the medians shown on the page
    med = lambda C, k: {fl: C[k][fl][1] for fl in ('rms', 'range', 'vel')}
    page = {k: out[k] for k in ('subjects', 'age', 'height_m', 'leg_m', 'pendulum')}
    page['conditions'] = {n: dict(subjects=C['subjects'], trials=C['trials'], psd={k: C['psd'][k] for k in ('df', 'ap', 'ml')},
                                  psd_rms={k: round(v, 4) for k, v in C['psd_rms'].items()}, angle_rms_deg=C['angle_rms_deg'][1],
                                  **{k: med(C, k) for k in ('cop_ap', 'cop_ml', 'com_ap', 'com_ml')})
                          for n, C in out['conditions'].items()}
    del page['pendulum']['method']
    json.dump(page, open(HERE / 'data' / 'stand_page.json', 'w'), separators=(',', ':'))


if __name__ == '__main__':
    if '--download' in sys.argv: download()
    main()
