# Pitch Study

`pitch/index.html` is a baseball fastball built the same way as the walk and run pages: measured data drives the motion, and only secondary motion is simulated. It uses the walk page's palette, drawing primitives, spring and blurred cast shadow. The body is drawn from 3D joint centres instead of the 2D side-view rig, because a pitch is a rotation about the vertical axis that a side-view rig cannot express.

**Live:** https://htlin222.github.io/walk-cycle-animation/pitch/

The section below can be pasted into the root README after "## Run cycle". The last part has the lines for "Reproduce the data" and "Sources".

---

## Pitch

[![Animated fastball, 3/4 view: set position and stride at 0.5×, foot contact to the finish at 0.1×](../assets/pitch-cycle.gif)](https://htlin222.github.io/walk-cycle-animation/pitch/)

`pitch/index.html` throws a fastball from the averaged 3D motion of 67 pitchers. The phases are set position → leg lift → stride → foot plant → arm cocking → acceleration → release → follow-through → reset. The ball leaves the hand at the measured speed. The page has slow motion, a timeline, and ◀ ▶ buttons that step from one event to the next.

| Layer | Source | How it is used |
|---|---|---|
| Whole body (pelvis, legs, trunk, both arms) | Driveline OpenBiomechanics Project (OBP), fastballs on an instrumented mound: 3D joint centres at 360 Hz (`landmarks.csv`) | Each pitch is time-normalised piecewise between 8 events, averaged within each pitcher, then across pitchers. Left-handers are mirrored. Segment directions and lengths are averaged, so limbs keep their length. Knees are solved by two-bone IK between the averaged hip and ankle. |
| Shoes, head | OBP C3D files: heel, toe and four head-band markers | Sole points under the heel and toe markers. The head centre and facing direction come from the head band. |
| Event timing | OBP events: peak knee height, foot contact (10 % bodyweight), foot plant (100 %), max external rotation, release, max internal rotation. Leg-lift onset is detected here. | The page clock plays the mean event times in real time (release = 0 ms). The timeline and ◀ ▶ stop at each event. |
| Curves panel | OBP `joint_velos.csv`, `joint_angles.csv` | Pelvis and trunk rotation velocity, shoulder external rotation and elbow flexion, averaged on the same time base. |
| Ball | Radar speed per pitch (OBP metadata) | Leaves the fingers at release at the mean speed. It is aimed at the middle of the strike zone, with gravity only (see below). |
| Mound | Measured landing height | The turf is flat for 6 in in front of the rubber, then slopes down to where the lead foot lands: 10 cm lower, a 7.3 % slope. The rule-book slope is 1 in/ft (8.3 %). |
| Hair | Damped spring, 240 Hz, softly limited | The only simulated motion. |

### Measured pitch (OBP, this repo's analysis)

67 pitchers, 194 fastballs: 48 college, 9 independent, 5 MiLB, 5 high school. Height 1.85 ± 0.07 m, mass 92 ± 10 kg, 15 left-handers mirrored. Values are means ± SD across pitchers, each pitcher averaged over his own pitches.

| | |
|---|---|
| Ball speed | 84.8 ± 4.6 mph (136.6 km/h, 37.9 m/s) |
| Leg-lift onset → peak knee height | 482 ms |
| Peak knee height → foot contact | 624 ms |
| Foot contact → foot plant (10 → 100 % bodyweight) | 21 ms |
| Foot contact → release | 155 ± 18 ms |
| Max external rotation → release | 32 ± 3 ms |
| Release → max internal rotation | 34 ± 5 ms |
| Stride (OBP) | 84 ± 6 % of height |
| Peak shoulder external rotation | 168 ± 10° (averaged curve: 168°) |
| Shoulder external rotation at foot plant | 50 ± 18° |
| Elbow flexion at foot plant | 103 ± 16° |
| Peak hip–shoulder separation | 32 ± 7° |
| Peak pelvis rotation velocity | 751 ± 89 °/s, 95 ms before release |
| Peak trunk rotation velocity | 1,054 ± 87 °/s, 85 ms before release |
| Pelvis → trunk peak | +9.5 ± 16.7 ms. The trunk peaks after the pelvis in 48 of 67 pitchers. |
| Peak shoulder internal rotation velocity | 4,531 ± 290 °/s, at release |
| Peak elbow extension velocity | 2,470 ± 231 °/s |
| Trunk forward tilt at release | 34 ± 10° |
| Lead knee extension, foot plant → release | 10 ± 10° |
| Release height | 1.47 m, 1.72 m ahead of the pivot ankle |

The kinematic sequence runs proximal to distal: pelvis, then trunk, then the arm. Each segment peaks faster than the one before it. Arm acceleration takes about 30 ms. The numbers are close to those reported for college pitchers (Fleisig et al. 1999). The pelvis-to-trunk gap is small and varies between pitchers. Averaging curves that peak at slightly different times also flattens the peaks: the averaged curves reach 725 and 1,035 °/s, against per-pitcher means of 751 and 1,054 °/s.

### How the pitch differs from the walk and run

- **3D, projected.** Pelvis and trunk each turn more than 100° toward home, and the shoulder lays back to 168°, mostly behind the body. A side-view joint-angle rig cannot show either. The page projects the averaged 3D joint centres through a perspective camera instead. Three views are available: 側面 side (from the third-base side), 斜前 3/4 front and 捕手 catcher. The trunk is drawn as rings around the pelvis and thorax axes, so hip–shoulder separation shows as a twist. Body parts are depth-sorted. The cast shadow is the same figure dropped onto the mound along a light direction.
- **Averaging without shrinking.** Averaging joint positions directly makes a forearm shorter wherever pitchers' arms point different ways, as at layback. Chains are therefore rebuilt from averaged unit directions times averaged lengths. Feet and pelvis keep averaged positions, because those are what must stay planted.
- **Planted feet stay planted.** The pivot foot's ball of the foot is held still from leg-lift onset until the foot starts to drag, 196 ms before release. Before then the averaged foot creeps by at most 2 cm; afterwards the toe drags toward home, as in the data. The lead heel is held from foot plant to the end, faded in over the 21 ms from foot contact (≤ 1.7 cm correction). [`analysis/check_pitch.py`](../analysis/check_pitch.py) measures 0.000 mm movement for both held points and soles at most 0.2 mm below the mound. After release the lead foot turns about the heel: its ball moves 10 mm by release and 38 mm by the end.
- **Set position and reset are not data.** OBP recordings start at most a few hundred ms before the leg lift, so the set position is the pose at leg-lift onset, held for 1.2 s with one slow breath (the upper body rises at most 4 mm; feet and pelvis stay still, and the pose is the data pose at both ends of the hold). The data end 200 ms after release. The finish is held, then fades back to the set position. The hair spring restarts at rest when the faded-out finish is swapped for the set pose, so it does not swing across the loop seam.
- **The ball's flight is not measured.** The hand itself moves at 24 m/s at release, 17° downward. The ball leaves the fingertips at the 37.9 m/s radar speed, aimed down the line to the middle of the strike zone (launch −0.3°, 0.43 s to the plate). Gravity acts on it; the backspin lift of a four-seamer is left out.

Controls: play / pause (space), ◀ ▶ previous / next event (arrow keys), playback speed (0.25× by default; real time is 1×), timeline, camera 側面 / 斜前 / 捕手, skeleton overlay with the throwing-hand path, curves panel. The phase chips read 預備 Set → 抬腿 Leg lift → 跨步 Stride → 踏地 Foot plant → 舉臂 Arm cocking → 加速 Acceleration → 出手 Release → 跟進 Follow-through → 重置 Reset.

**Licence.** OBP data are CC BY-NC-SA 4.0 (Driveline Baseball). The curves in `analysis/data/normative_pitch_obp.json`, which are also embedded in `pitch/index.html`, are derived from them and carry the same licence. They are non-commercial and share-alike, and OBP's added restriction on use by professional sports organisations applies. The rest of this repository keeps its own terms.

**中文：** 投球（`pitch/`）用 Driveline OpenBiomechanics 的 67 位投手、194 顆直球，把 3D 關節中心依抬腿、膝蓋最高點、踏地、肩外旋最大、出手等事件對齊後平均，再投影到側面、斜前或捕手視角。球速 84.8 mph，跨步 84% 身高，肩外旋最大 168°。骨盆角速度 751 °/s 先到頂，軀幹 1,054 °/s 晚約 10 ms，肩外旋最大到出手只有 32 ms。軸心腳在出手前 196 ms 開始拖行，之前完全不動；前腳從踏地到結束不滑動。預備姿勢與重置不是資料。資料授權 CC BY-NC-SA 4.0。

### Reproduce (lines for "Reproduce the data")

```
  pitch_obp.py        OBP pitching (--download fetches and checks it, ≈ 310 MB zipped; needs `pip install c3d`) → data/normative_pitch_obp.json; --embed writes it into pitch/index.html
  check_pitch.py      held-foot / mound / event-timing / ball / loop-seam / hair checks of pitch/index.html in headless Chromium
  render_pitch.py     → assets/pitch-cycle.gif, assets/pitch-og.png
```

Pitching pipeline: `python analysis/pitch_obp.py --download --embed`, then `python analysis/check_pitch.py`. Raw files go to `analysis/obp/`, which is git-ignored.

### Sources (lines for "Sources")

- Driveline Baseball Research & Development. The OpenBiomechanics Project (OBP), baseball pitching, dataset-v1. [openbiomechanics.org](https://www.openbiomechanics.org), [github.com/drivelineresearch/openbiomechanics](https://github.com/drivelineresearch/openbiomechanics) (data CC BY-NC-SA 4.0).
- Fleisig GS, Barrentine SW, Zheng N, Escamilla RF, Andrews JR (1999). Kinematic and kinetic comparison of baseball pitching among various levels of development. *Journal of Biomechanics* 32(12):1371–1375.
- Official Baseball Rules 2023, rule 2.01 and appendix 2 (pitcher's plate and mound dimensions).
