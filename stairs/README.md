# Stairs and ramps

`stairs/index.html` walks up and down an endless staircase (4 step heights) or ramp (6 inclines). It uses the walk page's body, drawing, springs and shadow. The legs and pelvis come from a stair and ramp biomechanics dataset; the solver is the walk's "the loaded foot does not move", on terrain.

Data: `analysis/stairs_camargo.py` → `analysis/data/normative_stairs_camargo.json` (full curves and numbers) and `analysis/data/stairs_page.json` (embedded in the page). Checks: `analysis/check_stairs.py`. Images: `analysis/render_stairs.py` → `assets/stairs-cycle.gif`, `assets/stairs-og.png`.

The section below is ready to paste into the root README, after "## Run cycle". The link line for the top of the root README:

```
▶ **Stairs and ramps:** [`stairs/`](stairs/) climbs and descends an endless staircase (4 step heights) or ramp (6 inclines), built from 22 adults' stair and ramp biomechanics ([live](https://htlin222.github.io/walk-cycle-animation/stairs/), [details below](#stairs-and-ramps)).
```

---

## Stairs and ramps

[![Animated stair climb and descent, 6-inch steps](assets/stairs-cycle.gif)](https://htlin222.github.io/walk-cycle-animation/stairs/)

`stairs/index.html` uses the walk page's body, drawing, springs and shadows. The cycle underneath is rebuilt from stair and ramp data, and the staircase never ends.

| Layer | Source | How it is used |
|---|---|---|
| Legs, pelvis | Camargo et al. 2021: 22 adults, stairs at 4 step heights (4, 5, 6, 7 in) and ramps at 6 inclines (5.2–18°), up and down, OpenSim inverse kinematics at 200 Hz | Hip, knee and ankle angles, pelvic tilt / obliquity / rotation, stance fraction, cadence, stride and rise per stride. Steady-state cycles only (447–462 per stair condition, 790–1,096 per ramp condition), averaged within each subject, then across subjects. Left and right sides are pooled. |
| Treads | The same dataset's heel and toe markers | Tread depth and riser height, and where the ball of the foot stands on the tread going up and going down. |
| Trunk lean | Pelvic tilt in the same 22 subjects, stairs / ramps vs level walking; trunk and pelvis tilt together on slopes (Leroux et al. 2002) | The whole trunk leans by the measured change: +6.5 to +8.1° going upstairs, +2.5 to +9.9° up ramps, 0 to −1.6° going down. |
| Arms, head, trunk rhythm | The walk page's neutral CMU walk (#104_02) | Played back unchanged. No stair-specific upper-body data was used. |

### Measured cycle (Camargo et al. 2021, this repo's analysis)

Stairs (tread and riser measured from the foot markers; nominal 4–7 in = 10.2–17.8 cm):

| | 4 in | 5 in | 6 in | 7 in |
|---|---|---|---|---|
| Riser × tread | 10.9 × 29.7 cm | 13.1 × 29.0 cm | 15.9 × 27.5 cm | 18.2 × 25.9 cm |
| Cadence up / down | 100 / 107 steps/min | 102 / 109 | 99 / 108 | 98 / 106 |
| Stance up / down | 64.3 / 68.5 % | 64.4 / 67.7 % | 64.2 / 66.6 % | 63.6 / 66.1 % |
| Peak knee flexion up / down | 88 / 86° | 91 / 91° | 97 / 96° | 101 / 101° |
| Peak hip flexion up | 47° | 50° | 55° | 58° |
| Pelvic tilt vs level walking, up / down | +6.5 / −0.2° | +6.9 / −0.6° | +7.5 / −0.9° | +8.1 / −1.1° |

Going up, the heel hangs 4.4–6.4 cm over the nosing and the toe stops 12–14 cm short of the next riser. Going down, the heel stands 6.5–8.5 cm in front of the riser behind and the toe tip is within 1.6 cm of the nosing.

Ramps:

| | 5.2° | 7.8° | 9.2° | 11° | 12.4° | 18° |
|---|---|---|---|---|---|---|
| Stride up / down | 1.37 / 1.33 m | 1.36 / 1.31 | 1.36 / 1.28 | 1.35 / 1.25 | 1.34 / 1.19 | 1.20 / 1.06 |
| Cadence up / down | 98 / 100 steps/min | 101 / 104 | 100 / 106 | 100 / 107 | 100 / 108 | 92 / 103 |
| Stance up / down | 60.7 / 58.1 % | 63.1 / 58.8 % | 64.4 / 59.6 % | 65.3 / 60.6 % | 66.1 / 61.4 % | 67.4 / 63.4 % |
| Peak hip flexion up | 31° | 37° | 40° | 44° | 48° | 57° |
| Peak knee flexion down | 71° | 76° | 78° | 81° | 84° | 90° |

Steeper climbs need more hip and knee flexion and a longer stance; steeper descents shorten the stride and fold the knee further. On stairs, cadence hardly changes with step height (98–102 up, 106–109 down), and the extra height comes from knee and hip flexion. Going up, the pelvis tilts forward 6.5–8.1° compared with level walking; going down, it stays within 1.1°. This matches uphill/downhill posture (Leroux et al. 2002) and stair kinematics in the dataset paper (Camargo et al. 2021).

### How stairs differ from the walk solver

- **Contact on terrain.** The pivot is whichever of heel or ball is closer to the surface under it, not the lower of the two. Going up, the heel hangs over the nosing, so the ball carries the weight. Going down, the toes reach the nosing and the ball lands first. Body height is solved from "the pivot is on its tread or on the ramp". Stairs add one riser per step and ramps add stride × tan(incline), so the repeating part of the height stays periodic and the staircase can loop forever.
- **Stance foot exactly on the surface.** After the no-slip solve, each stance sample is shifted so that the lowest of 36 points along the sole touches the tread or ramp. The foot may rest on the nosing edge itself.
- **Treads from the data.** Tread depth = drawn stride / 2. The treads are placed so the ball of the drawn foot at mid-stance stands where the subjects' did, as a fraction of the tread (33–36 % of the way across going up, 76–82 % going down). Copying heel or toe distances in centimetres would not fit, because the drawn shoe is longer than the subjects'. Stride is fitted as on the walk page, by scaling hip excursion (×0.94 to ×1.03). Going downstairs, stride depends on the knee and ankle rather than the hip, so it is left as drawn, 4–5 % longer than measured.
- **Swing clearance against the stairs.** The swinging sole is lifted wherever it would come within 2 % of leg length of a tread, nosing or ramp, never back into stance, and fades out so the foot sets down without a jump.
- **Foot contact from markers.** The dataset's gait-event files come from heavily smoothed heel-marker speed. They mark the foot down later than the markers show it landing: by a median of 55 ms going upstairs and 130 ms going downstairs, where the toes land first. Foot off is marked 30–75 ms early. Here, contact and foot off are taken as the moments the heel or toe marker comes within 10 mm of its resting height. Stance is therefore 64–69 % on stairs, against roughly 57 % up and 50 % down with the files' events.
- **Steady state only.** A cycle counts when both feet, from the step before it to the step after it, are on the stairs or ramp (neither on the floor nor on the landing) and every label over it is the mode or its transitions. A 5-step staircase gives two such cycles per pass.
- **Pelvis frame.** OpenSim reports pelvis tilt and list about the lab axes, and the subjects walk along the lab's z axis, so its "tilt" is really obliquity there. The rotations are re-expressed in the walking direction. The thigh angle is hip flexion − anterior pelvic tilt, and this convention fits the measured pelvis height better in the 4 subjects tested (rms 4.5–5.2 mm, against 5.6–7.9 mm for the opposite sign). The ankle is zeroed so that the foot is flat in quiet standing at the start of each trial (median offset 4.3°).
- **Checks.** [`analysis/check_stairs.py`](../analysis/check_stairs.py) runs all 20 conditions in headless Chromium. While the same sole point stays in contact, it moves at most 0.0003 leg lengths (0.25 mm; under 0.0001 on stairs). The lowest sole point in stance stays within 0.0002 leg lengths of the surface. No sole point goes more than 0.0003 leg lengths (0.25 mm) into a tread, nosing, riser or ramp at any time. The swinging sole clears the stairs by at least 0.005 leg lengths (4 mm) and the ramp by at least 0.0009 (0.8 mm).

Controls: playback speed, 上樓 up stairs / 下樓 down stairs / 上坡 up ramp / 下坡 down ramp, step height 4–7″ or incline 5.2–18° (switching fades through white), exaggeration, skeleton overlay with the ankle path over the current stride. The phase chips show Contact → Mid-stance → Toe-off → Swing.

Reproduce: `pip install mat-io`, then `python analysis/stairs_camargo.py --download` (reads only the needed files out of the three 5–10 GB zips with HTTP range requests, ≈ 400 MB in total), then `python analysis/stairs_camargo.py && python analysis/stairs_camargo.py --embed`.

Caveats: the upper body is the neutral level walk. No stair-specific data was found for arm swing or gaze, so these are unchanged (people look down more on stairs, Cromwell & Wellmon 2001). The dataset locks the lumbar joint and has no trunk markers, so trunk lean is inferred from the pelvis. No handrail.

Sources (add to the root list):

- Camargo J, Ramanathan A, Flanagan W, Young A (2021). A comprehensive, open-source dataset of lower limb biomechanics in multiple conditions of stairs, ramps, and level-ground ambulation and transitions. *Journal of Biomechanics* 119:110320. [doi:10.1016/j.jbiomech.2021.110320](https://doi.org/10.1016/j.jbiomech.2021.110320). Data: Mendeley Data [fcgm3chfff](https://doi.org/10.17632/fcgm3chfff.1), [k9kvm5tn3f](https://doi.org/10.17632/k9kvm5tn3f.1), [jj3r5f9pnf](https://doi.org/10.17632/jj3r5f9pnf.1) (CC-BY-4.0).
- Leroux A, Fung J, Barbeau H (2002). Postural adaptation to walking on inclined surfaces: I. Normal strategies. *Gait & Posture* 15(1):64–74. [doi:10.1016/s0966-6362(01)00181-3](https://doi.org/10.1016/s0966-6362(01)00181-3).
- Cromwell RL, Wellmon R (2001). Sagittal plane head stabilization during level walking and ambulation on stairs. *Physiotherapy Research International* 6(3):179–192. [doi:10.1002/pri.226](https://doi.org/10.1002/pri.226).

中文簡介（可貼入根目錄 README 的中文段落）：

**上下樓梯與斜坡（`stairs/`）：**

- **腿與骨盆：** Camargo 等人 2021 年的資料庫，22 位成人上下 4 種階高的樓梯與 6 種坡度的斜坡，只取穩態步週期。
- **踩在踏面上：** 站立腳不滑動，身體高度由「承重點在踏面或坡面上」反推。上樓時腳跟懸在踏面邊緣外 4–6 cm，下樓時腳尖貼著邊緣。
- **步態事件：** 觸地與離地改由腳跟、腳尖標記點判定；資料庫原本的事件在下樓時晚了約 130 ms。
- **軀幹前傾：** 依同一批受試者相對平地行走的骨盆前傾量：上樓 +6.5 至 +8.1°，下樓幾乎不變。
- **無限樓梯：** 鏡頭跟著斜向移動，樓梯一直延伸。
