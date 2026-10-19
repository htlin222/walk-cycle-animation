# Quiet standing module (stand/)

Notes for merging this module into the root README. Every section below is ready to paste. The numbers come from `python analysis/stand_bds.py` and `python analysis/check_stand.py`.

---

## Section for the root README (after "## Run cycle")

```markdown
## Quiet standing

`stand/index.html` uses the walk page's body, drawing, springs and shadows. The person stands still, and the sway underneath comes from force-platform data.

| Layer | Source | How it is used |
|---|---|---|
| Sway | Public balance data set (BDS): 59 healthy young adults (18–38 y; no disability, no falls in the past year, no vestibular diagnosis) stood still for 60 s on a force platform, 3 trials per condition (Santos & Duarte 2016) | The centre-of-pressure (COP) power spectrum is averaged over all 177 trials per condition, AP and ML, up to 5 Hz. The page sums one sinusoid per 1/60 Hz bin, with amplitude √(2·PSD·df) and seeded random phase. The sum has the measured spectrum and RMS and repeats seamlessly every 60 s. |
| Body | Inverted pendulum about the ankles (Winter et al. 1998; Caron et al. 1997) | COP − COM = −COM''/ω0², so COM = COP · ω0²/(ω0² + ω²), a low-pass at 0.49 Hz. Here ω0² = g h / (h² + ρ²), with COM height above the ankle h = 0.511 H (0.86 m) and whole-body radius of gyration ρ = 0.23 H (Santschi et al. 1963). The whole body tips about the ankle by θ = COM / h (ankle strategy). Both feet stay planted. |
| Conditions | Same data set | 睜眼·硬地 eyes open, firm floor (default) / 閉眼·硬地 eyes closed / 睜眼·軟墊 eyes open on a 6 cm foam pad / 閉眼·軟墊 eyes closed on foam. Switching cross-fades the spectra. |
| Breathing | Resting adult rate 12–16 /min | 14 breaths/min, ±8 % slow breath-to-breath variation. Inspiration takes 40 % of the cycle (I:E ≈ 1:1.5). The chest and shoulders rise about 3 mm. |

### Measured sway (BDS, this repo's analysis)

Median over subjects, with the interquartile range in brackets. Each subject's value is the mean of its 3 trials.

| | Eyes open, firm | Eyes closed, firm | Eyes open, foam | Eyes closed, foam |
|---|---|---|---|---|
| COP AP RMS | 0.43 cm [0.34–0.51] | 0.49 cm [0.35–0.59] | 0.91 cm [0.77–1.06] | 0.96 cm [0.85–1.14] |
| COP ML RMS | 0.27 cm [0.22–0.36] | 0.27 cm [0.22–0.36] | 0.66 cm [0.61–0.74] | 0.72 cm [0.64–0.84] |
| COP AP range | 2.2 cm | 2.5 cm | 5.0 cm | 5.6 cm |
| COP mean speed, AP / resultant | 0.58 / 0.81 cm/s | 0.61 / 0.82 cm/s | 1.53 / 2.14 cm/s | 1.97 / 2.94 cm/s |
| COP AP median frequency | 0.13 Hz | 0.14 Hz | 0.15 Hz | 0.28 Hz |
| COM AP RMS (pendulum) | 0.40 cm | 0.45 cm | 0.78 cm | 0.77 cm |
| COM ML RMS (pendulum) | 0.24 cm | 0.23 cm | 0.55 cm | 0.56 cm |
| Body sway angle RMS | 0.26° | 0.31° | 0.51° | 0.51° |

Healthy young adults barely need vision on a firm floor: closing the eyes adds about 10 % to the AP sway. On foam, sway doubles and faster corrections appear. With eyes closed on foam, the median frequency doubles and the COP moves 3.4 times as fast as with eyes open on a firm floor. The true sway angle is about a quarter of a degree, a millimetre or two at the hip. The page draws it at true scale by default and has ×5 / ×10 buttons. A 10-second stabilogram shows COP (thin) and COM (thick) at true scale in centimetres: top right on a wide screen, a strip under the title on a phone.

### What is, and is not, in the model

- **Feet never move.** The body above the ankles rotates about the ankle joint, and the shoes are not touched. [`analysis/check_stand.py`](analysis/check_stand.py) measures 0 sole movement over 60 s in every condition.
- **COM from the drawn body.** The check reads the hip angle off the drawn skeleton, converts it back to COM sway and compares it with the spectrum-through-the-pendulum prediction (within 3 %) and the measured interquartile range. The synthetic COP also satisfies COP − COM = −COM''/ω0² to within 0.1 % of its RMS.
- **Arms hang.** Each arm is its own pendulum (~1 Hz), faster than the sway, so it stays vertical. Only its spring lags.
- **No hip strategy.** In quiet stance the hip mode is a small anti-phase motion above about 1 Hz (Creath et al. 2005). A force platform alone cannot size it, and at this scale it would be far below a pixel.
- **No weight shifts.** Shifting and fidgeting appear in unconstrained standing over many minutes (Duarte & Zatsiorsky 1999). The BDS trials are 60 s with the instruction "stand as still as possible", so the page leaves them out.
- **ML sway is not drawn on the body.** The view is from the side. ML sway is shown only in the stabilogram.

Controls: playback speed, condition (four buttons above), sway magnification 實際 ×1 / ×5 / ×10 (eases over about a second, so the body never tips in one frame), skeleton overlay (pendulum ankle → COM, COM floor projection and COP marker, all magnified like the body). The chips show Inhale 吸 / Exhale 吐.
```

### Line for the walk page's "Details that took evidence to get right"

```markdown
- **Standing is not still.** Before the first step, the body sways about the ankles with the measured eyes-open spectrum from `stand/` (0.26° RMS). The sway fades out as the gait amplitude rises, and the feet are untouched, so the no-slip travel is unchanged (check: [`analysis/check_stand.py`](analysis/check_stand.py)).
```

### Pointer line near the top (after "▶ **Run:**")

```markdown
▶ **Stand:** [`stand/`](stand/) is quiet standing: a public force-platform balance data set drives an inverted-pendulum sway with both feet planted ([live](https://htlin222.github.io/walk-cycle-animation/stand/), [details below](#quiet-standing)).
```

### "Run it" and "Reproduce the data" additions

```markdown
Open `index.html` (walk), `run/index.html` (run) or `stand/index.html` (stand) in a browser.

  stand_bds.py        BDS balance data (--download fetches BDS.zip, ≈ 375 MB) → data/normative_stand_bds.json, data/stand_page.json (embedded in stand/index.html)
  check_stand.py      feet / sway amplitude / pendulum checks of stand/index.html, and the walk's standing start vs git HEAD, in headless Chromium

Standing pipeline: `python analysis/stand_bds.py --download`, then paste `data/stand_page.json` into `const STAND` in `stand/index.html`. The walk page embeds the first 120 bins of `conditions.open_firm.psd.ap` as `const SWAY`.
```

### 中文簡介 addition

```markdown
**站立（`stand/`）：**

- **姿勢擺動：** BDS 平衡資料庫中 59 位健康年輕人在測力板上站 60 秒，取壓力中心（COP）的實測頻譜，以隨機相位的正弦波合成，均方根值與實測相同。
- **倒單擺：** 質心（COM）＝ COP 經 0.49 Hz 低通，整個身體以踝關節為支點前後擺動，擺角約 0.26°。雙腳完全不動。
- **四種條件：** 睜眼／閉眼 × 硬地／6 cm 軟墊。軟墊上擺動約加倍。
- **呼吸：** 每分鐘 14 次，胸口與肩膀起伏約 3 mm。
- **走路頁：** 起步前的站立也加上同樣的實測擺動。
```

### Sources to add

```markdown
- Santos DA, Duarte M (2016). A public data set of human balance evaluations. *PeerJ* 4:e2648. Data: [figshare 10.6084/m9.figshare.3394432](https://doi.org/10.6084/m9.figshare.3394432) (CC-BY-4.0).
- Winter DA, Patla AE, Prince F, Ishac M, Gielo-Perczak K (1998). Stiffness control of balance in quiet standing. *Journal of Neurophysiology* 80(3):1211–1221.
- Winter DA (1995). Human balance and posture control during standing and walking. *Gait & Posture* 3(4):193–214.
- Caron O, Faure B, Brenière Y (1997). Estimating the centre of gravity of the body on the basis of the centre of pressure in standing posture. *Journal of Biomechanics* 30(11–12):1169–1171.
- Santschi WR, DuBois J, Omoto C (1963). Moments of inertia and centers of gravity of the living human body. AMRL-TDR-63-36, Wright-Patterson AFB.
- Creath R, Kiemel T, Horak F, Peterka R, Jeka J (2005). A unified view of quiet and perturbed stance: simultaneous co-existing excitable modes. *Neuroscience Letters* 377(2):75–80.
- Duarte M, Zatsiorsky VM (1999). Patterns of center of pressure migration during prolonged unconstrained standing. *Motor Control* 3(1):12–27.
```

---

## Check output (`python analysis/check_stand.py`)

| Condition | Sole movement over 60 s | Synthetic COP AP / ML RMS | COM AP RMS from the drawn body (model) | Synthetic COP AP mean speed (measured median) |
|---|---|---|---|---|
| Eyes open, firm | 0 | 0.433 / 0.281 cm | 0.403 cm (0.403) | 0.64 cm/s (0.58) |
| Eyes closed, firm | 0 | 0.465 / 0.280 cm | 0.430 cm (0.430) | 0.70 cm/s (0.61) |
| Eyes open, foam | 0 | 0.950 / 0.683 cm | 0.841 cm (0.841) | 1.68 cm/s (1.53) |
| Eyes closed, foam | 0 | 0.943 / 0.748 cm | 0.752 cm (0.752) | 2.33 cm/s (1.97) |

Every RMS lies inside the measured interquartile range. Walk page: the body angle during the 0.8 s stand equals the sway model to within 1e-15°. The feet stay put through stand → lean → first steps. Single-support foot slip while walking is 0.00203 L/s, the same as the committed version (0.14 % of walking speed).

## Data caveats

- **"Young" in BDS means under 60.** This module keeps ages 18–40 with no disability, no falls in the past 12 months and no vestibular diagnosis: 59 of the 87 "Young" subjects (actual ages 18–38). Minor chronic conditions (asthma, rhinitis, hypothyroidism) are not excluded.
- **Synthetic sway is Gaussian with a fixed spectrum.** It matches RMS by construction. The mean speed comes out 10–20 % above the measured median, because the averaged spectrum carries the high-frequency power of the more active subjects. All but one value still lie inside the measured interquartile range; the exception is ML eyes open, firm: 0.51 vs IQR 0.34–0.50 cm/s. Real sway also shows non-stationary drifts ("rambling") that a stationary spectrum does not reproduce.
- **AP and ML phases are independent.** The real AP–ML coupling is not modelled.
- **The pendulum parameters come from anthropometry, not measurement.** h = 0.511 H and ρ = 0.23 H, giving f0 = 0.49 Hz. The COM numbers above are derived values, not measured ones.
- **The pendulum is less valid on foam.** The pad deforms, and the COP is measured under the foam rather than under the feet. On the page the feet are rigidly planted on top of the pad.
- **The figure's proportions are the walk page's.** The walk's leg length (ANSUR) is not the BDS subjects' mean leg (0.825 m, from height 1.68 m × 0.491). The sway is applied as an angle, which is independent of size.
