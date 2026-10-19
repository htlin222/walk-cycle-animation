# Walk Cycle Study

**An evidence-based procedural walk cycle in a single HTML file.** Clinical gait data drives the legs with zero foot slip, real motion capture drives the upper body, and a large anthropometric survey sets the body proportions. Switch between happy, neutral and sad walking styles measured from the same actors, start from a standstill, and watch a point-light shadow change with distance.

**Live:** [home](https://htlin222.github.io/walk-cycle-animation/) · [walk](https://htlin222.github.io/walk-cycle-animation/walk/) · [run](https://htlin222.github.io/walk-cycle-animation/run/)

![Animated walk cycle, happy style](assets/walk-cycle.gif)

[![Full page screenshot](assets/screenshot.png)](https://htlin222.github.io/walk-cycle-animation/walk/)

▶ **Video:** [`assets/walk-cycle-9-clips.mp4`](assets/walk-cycle-9-clips.mp4): 9 parameter combinations × 3 s, 1440×1080, 30 fps.

▶ **Run:** [`run/`](run/) is the running counterpart, built the same way from a running biomechanics database ([live](https://htlin222.github.io/walk-cycle-animation/run/), [details below](#run-cycle)).

▶ **Crowd:** [`crowd/`](crowd/) renders 140 different people walking together with the neutral gait. Start offsets are within ±100 ms, the camera follows the crowd, and the foreground is out of focus (1920×1080, 30 fps, 20 s).

---

## What makes it move like a person

| Layer | Source | How it is used |
|---|---|---|
| Legs (hip, knee, ankle, pelvic tilt / rotation / obliquity) | Clinical normative gait, 24 healthy adults, comfortable overground walking (Fukuchi, Fukuchi & Duarte 2018, WBDS) | Forward kinematics per leg; pelvis height and forward speed are **solved** from "the weight-bearing heel or ball does not move", so feet never slide (measured slip ≤ 0.0002 leg lengths). |
| Walking styles | CMU Graphics Lab motion capture: neutral walk (#104_02), happy vs sad performed by the **same actor** (#82_12 vs #82_10) | Stride, cadence and pelvic bounce fitted to each recording; trunk, head, shoulder girdle and arm curves played back after phase alignment to the clinical thigh curve (r ≥ 0.98). |
| Body proportions | ANSUR II, 4,082 US Army men | Neck base (C7), sternal notch, ear height, chest / waist depth, limb lengths and girths. |
| Head carriage | Craniovertebral angle, healthy young adults 50 ± 5° | Ear placed relative to C7 at 60°, the upright end of the healthy range. |
| Facial expression | FACS (Ekman) | Happy: AU6 + AU12 (cheek raiser, lip-corner puller). Sad: AU1 + AU4 + AU15 (inner brow raiser, brow lowerer, lip-corner depressor). |
| Hair, shirt hem | Damped springs, fixed 240 Hz semi-implicit Euler | Only secondary motion is simulated; the body itself is data. |

### Measured style differences (same actor, CMU subject 82)

| | Sad | Happy |
|---|---|---|
| Stride | 1.50 leg lengths | 1.78 leg lengths |
| Cadence | 101 steps/min | 117 steps/min |
| Pelvic bounce | 2.5 % leg length | 4.7 % leg length |
| Upper-arm swing | 12° | 35° |
| Head | ≈ 38° lower | level |

These match the gait-emotion literature: larger joint amplitudes and more bounce when happy, a lowered head, reduced arm swing and a contracted torso when sad (Roether et al. 2009; Michalak et al. 2009).

### Details that took evidence to get right

- **Acceleration you can see.** In a follow camera, the planted foot slides backward and the walk reads like a treadmill. The default fixed camera keeps the world still: the body speeds up and slows within every step (0.90–1.18 × mean speed), and the swing foot peaks at 3.2 × body speed.
- **Gait initiation.** Standing still → anticipatory forward lean → first step → steady state within about two steps. Forward travel is integrated from the pivot foot, so speeding up never slides a foot.
- **No limp.** Trunk, lumbar and head curves are symmetrised across the two steps. A single recorded cycle carries slow drift, and looping that drift once per stride is the visual signature of a limp.
- **Point-light shadow.** With the fixed camera a light hangs over the stage. The shadow points away from it, grows longer with distance, fades as (h / d)³ (cos θ / d² irradiance) and softens as it lengthens.

## Run cycle

[![Animated run cycle, 3.5 m/s, half speed](assets/run-cycle.gif)](https://htlin222.github.io/walk-cycle-animation/run/)

`run/index.html` uses the walk page's (`walk/index.html`) body, drawing, springs and shadows. The cycle underneath is rebuilt from running data.

| Layer | Source | How it is used |
|---|---|---|
| Legs, pelvis, ground force | Running Biomechanics Data Set (RBDS): 28 runners on an instrumented treadmill at 2.5, 3.5 and 4.5 m/s (Fukuchi, Fukuchi & Duarte 2017) | Hip, knee and ankle angles, pelvic tilt / obliquity / rotation, pelvis height, stance fraction and fore-aft ground reaction force, averaged across runners. Left and right sides are pooled. |
| Arms, trunk, head | CMU motion capture, two runners: subject 9 (7 cycles) and subject 35 (4 cycles) | Each cycle is phase-aligned to the RBDS thigh curve (r ≥ 0.99). Curves are averaged within each runner, then across the two. Arm swing is scaled with leg swing at each speed. |
| Breathing | Locomotor–respiratory coupling (Bramble & Carrier 1983) | One breath every two strides (2:2). |

### Measured cycle (RBDS, this repo's analysis)

| | Jog 2.5 m/s | Run 3.5 m/s | Fast 4.5 m/s |
|---|---|---|---|
| Cadence | 161 steps/min | 170 steps/min | 183 steps/min |
| Ground contact | 272 ms | 226 ms | 195 ms |
| Stance (% of stride) | 40.5 % | 36.0 % | 33.9 % |
| Stride | 2.16 leg lengths | 2.86 leg lengths | 3.42 leg lengths |
| Pelvis vertical travel | 9.8 cm | 9.5 cm | 8.3 cm |
| Peak knee flexion in swing | 92° | 107° | 117° |
| Foot strike (right foot) | 19 rearfoot, 4 midfoot, 5 forefoot | 19 / 5 / 4 | 17 / 6 / 5 |

As speed rises, contact time falls, the knee folds higher in swing and the pelvis bounces less. This matches the running literature (Novacheck 1998; Fukuchi et al. 2017). Two physics checks on the averaged force data: the mean vertical force over a stride is 9.54 N/kg, close to g = 9.81, and the net fore-aft impulse is +0.01 m/s, so the speed is steady.

### How running differs from the walk solver

- **Flight phase.** Walking always has a foot on the floor. In running, each foot is down for only 34–41 % of the stride, and both feet are in the air in between. Pelvis height is the measured curve, not solved from the feet.
- **Forward speed from Newton.** Integrating the fore-aft ground force (Δv = ∫F/m dt) gives the speed fluctuation. Speed dips about 4 % while braking after foot strike, recovers during push-off and stays constant in the air. Solving speed from "the planted foot does not move", as the walk does, made the body lurch by 25 % at every toe-off.
- **Planted feet stay planted.** Small per-leg corrections keep the contact point on the floor during stance: at most 3.5 % of leg length horizontally and 5.5 % vertically. The contact point drifts at about 1 % of running speed and sinks at most 0.5 % of leg length (4 mm) into the floor. In flight, both soles clear the floor. [`analysis/check_run.py`](analysis/check_run.py) measures all three.
- **Thigh reference.** Visual3D reports hip angle relative to the pelvis. The thigh-to-vertical angle is therefore hip − (pelvic tilt − standing tilt) + 6°. The 6° offset is where leg geometry and the separately measured pelvis height agree best (rms 1.3 % of leg length). Thigh-marker angles, an independent estimate, give about 4.5°.
- **Shoulders.** Seen from the side, the recorded fore-aft shoulder motion is almost all trunk twist (R² = 1.00, lever 0.215 leg lengths, about half the shoulder width). The renderer already moves the shoulders with the twist, so only the residual shoulder-girdle motion is kept. Using both would count the twist twice and push the far shoulder out behind the back. Twist is not exaggerated.
- **Toe-off.** The shoe bends at the ball of the foot just enough to keep the toe on the floor until it lifts. The bend never exceeds the foot's own pitch, so the toe box at most lies flat. Swing lift starts only after toe-off, so the toe never scrapes backward.

Controls: playback speed (slow motion helps), running speed 慢跑 2.5 / 跑步 3.5 / 快跑 4.5 m/s (cross-fades), camera 跟隨 follow (default) / 固定鏡頭 fixed, exaggeration, skeleton overlay. The phase chips show Contact → Mid-stance → Toe-off → Flight.

## Run it

Open `index.html` (home), `walk/index.html` or `run/index.html` in a browser. There is no build step and no dependencies; it is plain Canvas 2D.

Controls: speed, style (平常 neutral / 開心 happy / 低落 sad), camera (固定鏡頭 fixed / 跟隨 follow), exaggeration (secondary motion only), 重新起步 restart from standing, 顯示骨架 skeleton overlay with ankle path and pelvic-height curve.

## Reproduce the data

```
analysis/
  bvh.py              BVH parser + forward kinematics
  analyze.py          sagittal projection, heel-strike detection, cycle averaging (CMU clips → data/cmu_sagittal_curves.json)
  extract_styles.py   phase alignment + smoothing → data/styles.json (embedded in walk/index.html)
  ansur_stats.py      ANSUR II means → data/ansur2_male_means.json
  render_video.py     deterministic frame-stepped capture (Playwright) + ffmpeg → assets/walk-cycle-9-clips.mp4
  run_rbds.py         RBDS running data (--download fetches it, ≈ 400 MB) → data/normative_run_rbds.json
  extract_run.py      CMU running clips + RBDS → data/cmu_run_curves.json, data/run_styles.json (embedded in run/index.html)
  check_run.py        slip / floor / flight checks of run/index.html in headless Chromium
  render_run.py       → assets/run-cycle.gif, assets/run-og.png
  data/               intermediate results, so nothing has to be re-downloaded to inspect them
```

BVH files come from the CMU database (Motionbuilder-friendly conversion, e.g. [Shriinivas/cmubvh](https://github.com/Shriinivas/cmubvh)); put them in `analysis/bvh/`. The running clips are 09_01–09_06, 09_11, 35_18, 35_22, 35_25 and 35_26. RBDS files go to `analysis/rbds/` (`python analysis/run_rbds.py --download`).

Running pipeline: `python analysis/run_rbds.py && python analysis/extract_run.py`, then paste `data/run_styles.json` into `const RUN` in `run/index.html`.

## 中文簡介

一個只用單一 HTML 檔、以實證數據驅動的程序化走路動畫：

- **腿：** 24 位健康成人的臨床步態常模。骨盆高度與前進速度由「承重腳不動」反推，腳完全不滑步。
- **上半身與三種風格：** CMU 真人動作捕捉。開心與低落由同一位演員演出。
- **身體比例：** ANSUR II 人體測量資料庫。
- **頭部角度：** 依臨床的顱椎角。
- **表情：** 依 FACS 臉部動作編碼。

另外支援從原地起步、固定鏡頭下的點光源影子，以及可切換的骨架顯示。

**跑步（`run/`）：**

- **腿、骨盆與地面反作用力：** RBDS 跑步資料庫，28 位跑者在跑步機上以 2.5、3.5、4.5 m/s 跑步。
- **騰空期：** 觸地只佔步週期的 34–41%，其餘時間雙腳離地。
- **前進速度：** 由前後向地面反作用力積分（牛頓第二定律）。觸地煞車時約慢 4%，蹬地後回升，騰空時等速。
- **觸地腳不滑步：** 觸地點滑動約為跑速的 1%。
- **手臂與軀幹：** CMU 兩位跑者的動作捕捉，擺臂幅度隨速度放大。
- **呼吸：** 每兩個步週期一次（2:2 耦合）。

## Sources

- Fukuchi RK, Fukuchi CA, Duarte M (2017). A public data set of running biomechanics and the effects of running speed on lower extremity kinematics and kinetics. *PeerJ* 5:e3298. Data: [figshare 10.6084/m9.figshare.4543435](https://doi.org/10.6084/m9.figshare.4543435) (CC-BY-4.0).
- Novacheck TF (1998). The biomechanics of running. *Gait & Posture* 7(1):77–95.
- Hinrichs RN (1987). Upper extremity function in running. II: Angular momentum considerations. *International Journal of Sport Biomechanics* 3(3):242–263.
- Bramble DM, Carrier DR (1983). Running and breathing in mammals. *Science* 219(4582):251–256.
- Fukuchi CA, Fukuchi RK, Duarte M (2018). A public dataset of overground and treadmill walking kinematics and kinetics in healthy individuals. *PeerJ* 6:e4640. Normative curves via [PhysioGaitNorm](https://github.com/x-biosignal/PhysioGaitNorm) (CC-BY-4.0).
- [CMU Graphics Lab Motion Capture Database](http://mocap.cs.cmu.edu/); BVH conversion by B. Hahne.
- [ANSUR II anthropometric survey](https://www.openlab.psu.edu/ansur2/) (Gordon et al. 2014).
- Craniovertebral angle in young adults: [PMC11042887](https://pmc.ncbi.nlm.nih.gov/articles/PMC11042887).
- Emotion in gait review: [arXiv 2003.11461](https://arxiv.org/abs/2003.11461) (Roether 2009, Michalak 2009 and others).
- Arm swing ranges: [Applied Sciences 15(12):6593](https://www.mdpi.com/2076-3417/15/12/6593).
