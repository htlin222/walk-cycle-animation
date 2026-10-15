# Walk Cycle Study

**An evidence-based procedural walk cycle in a single HTML file.** Clinical gait data drives the legs with zero foot slip, real motion capture drives the upper body, and a large anthropometric survey sets the body proportions. Switch between happy, neutral and sad walking styles measured from the same actors, start from a standstill, and watch a point-light shadow change with distance.

**Live demo:** https://htlin222.github.io/walk-cycle-animation/

![Animated walk cycle, happy style](assets/walk-cycle.gif)

[![Full page screenshot](assets/screenshot.png)](https://htlin222.github.io/walk-cycle-animation/)

▶ **Video:** [`assets/walk-cycle-9-clips.mp4`](assets/walk-cycle-9-clips.mp4): 9 parameter combinations × 3 s, 1440×1080, 30 fps.

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

## Run it

Open `index.html` in a browser. There is no build step and no dependencies; it is plain Canvas 2D.

Controls: speed, style (平常 neutral / 開心 happy / 低落 sad), camera (固定鏡頭 fixed / 跟隨 follow), exaggeration (secondary motion only), 重新起步 restart from standing, 顯示骨架 skeleton overlay with ankle path and pelvic-height curve.

## Reproduce the data

```
analysis/
  bvh.py              BVH parser + forward kinematics
  analyze.py          sagittal projection, heel-strike detection, cycle averaging (CMU clips → data/cmu_sagittal_curves.json)
  extract_styles.py   phase alignment + smoothing → data/styles.json (embedded in index.html)
  ansur_stats.py      ANSUR II means → data/ansur2_male_means.json
  render_video.py     deterministic frame-stepped capture (Playwright) + ffmpeg → assets/walk-cycle-9-clips.mp4
  data/               intermediate results, so nothing has to be re-downloaded to inspect them
```

BVH files come from the CMU database (Motionbuilder-friendly conversion, e.g. [Shriinivas/cmubvh](https://github.com/Shriinivas/cmubvh)); put them in `analysis/bvh/`.

## 中文簡介

一個只用單一 HTML 檔、以實證數據驅動的程序化走路動畫：

- **腿：** 24 位健康成人的臨床步態常模。骨盆高度與前進速度由「承重腳不動」反推，腳完全不滑步。
- **上半身與三種風格：** CMU 真人動作捕捉。開心與低落由同一位演員演出。
- **身體比例：** ANSUR II 人體測量資料庫。
- **頭部角度：** 依臨床的顱椎角。
- **表情：** 依 FACS 臉部動作編碼。

另外支援從原地起步、固定鏡頭下的點光源影子，以及可切換的骨架顯示。

## Sources

- Fukuchi CA, Fukuchi RK, Duarte M (2018). A public dataset of overground and treadmill walking kinematics and kinetics in healthy individuals. *PeerJ* 6:e4640. Normative curves via [PhysioGaitNorm](https://github.com/x-biosignal/PhysioGaitNorm) (CC-BY-4.0).
- [CMU Graphics Lab Motion Capture Database](http://mocap.cs.cmu.edu/); BVH conversion by B. Hahne.
- [ANSUR II anthropometric survey](https://www.openlab.psu.edu/ansur2/) (Gordon et al. 2014).
- Craniovertebral angle in young adults: [PMC11042887](https://pmc.ncbi.nlm.nih.gov/articles/PMC11042887).
- Emotion in gait review: [arXiv 2003.11461](https://arxiv.org/abs/2003.11461) (Roether 2009, Michalak 2009 and others).
- Arm swing ranges: [Applied Sciences 15(12):6593](https://www.mdpi.com/2076-3417/15/12/6593).
