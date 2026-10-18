# Stairs and ramps

`stairs/index.html` walks up and down an endless staircase (4 step heights) or ramp (6 inclines). It uses the walk page's body, drawing, springs and shadow. The legs and pelvis come from a stair and ramp biomechanics dataset; the solver is the walk's "the loaded foot does not move", on terrain.

Data: `analysis/stairs_camargo.py` → `analysis/data/normative_stairs_camargo.json` (full curves and numbers) and `analysis/data/stairs_page.json` (embedded in the page). Course mode: `analysis/course_camargo.py` → `analysis/data/course_camargo.json` (all transition categories) and `analysis/data/course_page.json` (embedded as `COURSE`; `python analysis/course_camargo.py --embed`). Checks: `analysis/check_stairs.py`, `analysis/check_course.py`. Images: `analysis/render_stairs.py` → `assets/stairs-cycle.gif`, `assets/stairs-og.png`.

The section below is ready to paste into the root README, after "## Run cycle". The link line for the top of the root README:

```
▶ **Stairs and ramps:** [`stairs/`](stairs/) climbs and descends an endless staircase (4 step heights) or ramp (6 inclines), built from 22 adults' stair and ramp biomechanics ([live](https://htlin222.github.io/walk-cycle-animation/stairs/), [details below](#stairs-and-ramps)).
```

---

## Stairs and ramps

[![Animated terrain course: up a flight of stairs, over the landing, down again and over a hurdle](assets/stairs-cycle.gif)](https://htlin222.github.io/walk-cycle-animation/stairs/)

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
- **Swing clearance against the stairs.** The swinging sole is lifted wherever it would come within 2 % of leg length of a tread, nosing or ramp, never back into stance. The lift fades in after foot off and out before contact, so the foot leaves and sets down without a jump. The toe box bends at the ball to keep its tip off the surface while the ball is low; on a ramp that height is measured from the slope, not the level.
- **Foot contact from markers.** The dataset's gait-event files come from heavily smoothed heel-marker speed. They mark the foot down later than the markers show it landing: by a median of 55 ms going upstairs and 130 ms going downstairs, where the toes land first. Foot off is marked 30–75 ms early. Here, contact and foot off are taken as the moments the heel or toe marker comes within 10 mm of its resting height. Stance is therefore 64–69 % on stairs, against roughly 57 % up and 50 % down with the files' events.
- **Steady state only.** A cycle counts when both feet, from the step before it to the step after it, are on the stairs or ramp (neither on the floor nor on the landing) and every label over it is the mode or its transitions. A 5-step staircase gives two such cycles per pass.
- **Pelvis frame.** OpenSim reports pelvis tilt and list about the lab axes, and the subjects walk along the lab's z axis, so its "tilt" is really obliquity there. The rotations are re-expressed in the walking direction. The thigh angle is hip flexion − anterior pelvic tilt, and this convention fits the measured pelvis height better in the 4 subjects tested (rms 4.5–5.2 mm, against 5.6–7.9 mm for the opposite sign). The ankle is zeroed so that the foot is flat in quiet standing at the start of each trial (median offset 4.3°).
- **Checks.** [`analysis/check_stairs.py`](../analysis/check_stairs.py) runs all 20 conditions in headless Chromium. While the same sole point stays in contact, it moves at most 0.0003 leg lengths (0.25 mm; under 0.0001 on stairs). The lowest sole point in stance stays within 0.0002 leg lengths of the surface. No sole point goes more than 0.0003 leg lengths (0.25 mm) into a tread, nosing, riser or ramp at any time. The swinging sole clears the stairs by at least 0.0024 leg lengths (2 mm) and the ramp by at least 0.0018 (1.5 mm). Neither ankle's velocity changes by more than 0.012 leg lengths from one 240 Hz frame to the next (the toe-off lift on steep ramps used to jump 4–6 cm in a few milliseconds; fixed), and no knee bends backwards.

Controls: playback speed, 上樓 up stairs / 下樓 down stairs / 上坡 up ramp / 下坡 down ramp / 地形 Course, step height 4–7″, incline 5.2–18° or course preset (樓梯 / 坡道 / 障礙 / 綜合 / 隨機; switching fades through white), exaggeration, skeleton overlay with the ankle path over the current stride. The phase chips show Contact → Mid-stance → Toe-off → Swing.

Reproduce: `pip install mat-io`, then `python analysis/stairs_camargo.py --download` (reads only the needed files out of the three 5–10 GB zips with HTTP range requests, ≈ 400 MB in total), then `python analysis/stairs_camargo.py && python analysis/stairs_camargo.py --embed`.

### 地形 Course: one walk over level ground, stairs, ramps, curbs and hurdles

The 地形 Course mode walks without stopping through a course that loops seamlessly. The presets are 樓梯 (level → 5 steps up → landing → 5 steps down), 坡道 (level → ramp up → top → ramp down), 障礙 (hurdles at three heights and a curb up and down), 綜合 (all of them). 隨機 builds a course from a seed. The lap ends at the height and phase where it starts, so the course repeats exactly.

| Part | Source | How it is used |
|---|---|---|
| Level walking | Camargo et al. 2021 level-ground trials, comfortable speed, straight walking only (22 subjects, 1,183 cycles) | Stance 58.8 %, stride 1.12 s, stride 1.56 leg lengths. |
| Stair and ramp strides, including the transitions | The same stair (6 in) and ramp (9.2°) trials, every foot contact typed by what it lands on (floor, step / ramp, landing) | Each leg cycle is named by the four footholds around it. The cycles that step onto the landing (up: second-to-last step → landing, 22 subjects, 230 cycles; last step → landing, 190 cycles) and the first and last full cycles of a descent (112 and 228 cycles) are averaged and used whole. The stance and the timing of every cycle come from the measured cycle for its footholds. |
| Stepping onto and off the stairs / ramp from the floor | The measured swings only (e.g. floor → first step, 22 subjects, 114 swings, 0.45 s; landing → first step down, 88 swings, 0.56 s), joined to a level-walking stance | In this dataset every stair and ramp trial starts from standing one step before the first riser and ends by stopping just after the last one. The floor-side transition strides are gait initiation and termination, not walking, so a whole measured cycle cannot be used there. The page uses the measured swing onto the step instead, and the stance it leaves from is level walking. |
| Curb (one 6-inch step) | The swings onto the first step and off the last step | Step-up: floor → first step, then first step → landing. Step-down: landing → first step down, then last step → floor. |
| Hurdles (10, 20, 30 % of leg length; 2 cm thick) | No open dataset with obstacle geometry was found (one candidate on Zenodo could not be used). Modelled from the literature: Chardon et al. 2024 (28 young adults, 15 cm obstacle) for clearance and foot placement, Lu et al. 2022 (12 healthy older adults, 10–30 % of leg length) for how clearance and joint angles change with height | Leading toe clearance 10.1 cm (0.117 leg lengths) at every height, as Lu et al. found no height effect. Trailing clearance = leading × Lu's trailing / leading ratio at that height: 0.113, 0.120 and 0.126 leg lengths. While crossing, hip and knee flexion are raised to Lu's values when the toe is over the obstacle (leading hip 58 / 67 / 75°, knee 90 / 107 / 118°; trailing hip 27 / 32 / 35°, knee 99 / 115 / 129°). Foot placement: trailing ball 42.4 cm before the bar, leading heel 25.1 cm after it, trailing heel 90 cm after it (Chardon et al.). |

How the course is built:

- **Footholds first.** The course is a list of alternating footholds, each tagged with the terrain it lands on. For each feature, the number of level steps before it is chosen from the designed gap (in metres) and corrected by a trial solve. The total is kept even, so the same foot starts every lap.
- **Which foot leads.** Feet strictly alternate, so which foot meets the first riser follows from the step count. The approach is planned in steps, not distance: the step count and three per-step stride adjustments before each feature (hip excursion scaled ×0.70–1.45, up to ×1.7 for the step over a hurdle, set at each contact and blended across the cycle) put the foot whose measured swing is "floor → first step" exactly on the first riser. That swing is what the data was recorded for. The stairs are then placed by least squares so that every foot on the flight stands where the subjects' did on the tread, as a fraction of it.
- **Then the solver of the stairs page, along a whole lap.** Speed comes from "the loaded foot does not move", body height from the loaded heel or ball on the surface, and each stance sample is placed so the sole touches the ground. Within a stance, the sole point in contact is held still. When contact passes to another point (heel → ball → bent toe), that point is held from where it is, so the foot rolls without sliding. The swing carries the corrections from foot-off to the next contact. It is lifted wherever the sole would come within 2 % of leg length of a step, curb, nosing or ramp, including ahead of a riser and at the half-way points the page draws between samples.
- **No jolt at a curb.** Stepping onto or off a curb or the first stair, the weight passes between feet a riser apart in a short double support, and the body would jump a riser in about 50 ms. The body height is kept at or below what the legs give and changes no faster than 0.6 leg lengths/s (≈ 0.5 m/s, a brisk stair climb): the rise is spread over the next single support and a drop starts earlier on the trailing leg. Level walking and steady flights are slower than that and are unchanged.
- **Hurdle clearance exactly as modelled.** For each crossing, the swing is adjusted vertically, up or down, with a narrow smooth correction at the closest pass, until the sole's lowest point over the bar equals the modelled clearance. The crossing step is split around the bar in Chardon's proportions.
- **Seamless loop.** The lap is solved as one periodic problem: timeline, body path and both legs repeat with an offset of one lap length (and the lap's height change, which the presets keep at zero). Nothing is blended across the seam.

Checks: [`analysis/check_course.py`](../analysis/check_course.py) plays the four presets and three random seeds for a full lap at 240 Hz. Results:

- While the same sole point stays in contact, it moves at most 0.0003 leg lengths (0.25 mm).
- The lowest sole point in stance stays within 0.0006 leg lengths of the ground.
- No sole point goes more than 0.0001 leg lengths into the ground, a step, a curb or a hurdle.
- The swinging sole clears the terrain by at least 0.0013 leg lengths (1 mm, just after foot off).
- Played back at 1/1920 s with sole points every millimetre, every hurdle crossing's clearance is within 0.0008 leg lengths (0.7 mm) of the model. The crossing step (trailing ball → bar → leading heel) is at least 87 % of the measured one.
- Across the lap seam, the frame-to-frame change of every table is at most 1.3 × the largest anywhere else in the lap.
- Neither ankle's velocity changes by more than 0.0093 leg lengths between 240 Hz frames (before the fixes: up to 0.048, a 3–4 cm jump of the foot at every foot off and a 13 cm jump of the body onto a curb), and no knee bends backwards.
- No page errors, and no horizontal scroll at 390 px.

Course caveats:

- The floor-side transitions use measured swings with a level-walking stance, because the dataset has no walking-through transitions there.
- The step off the last stair onto the floor has 29 cycles from 6 subjects (3 subjects on the ramp).
- The hurdle model mixes young-adult clearance and placement with older-adult trends for height and joint angles.
- The crossing step is about 87 % of the measured one: the trailing ball lands about 0.43 leg lengths before the bar (measured 0.49) and the leading heel about 0.25 after it (0.29). The step after it runs 2–12 % long (trailing heel 1.06–1.16 leg lengths past the bar, measured 1.04): a longer crossing step drags the next one with it, and more hip excursion than ×1.7 starts to look forced.
- Designed gaps before hurdles and curbs come out within about ±0.7 leg lengths (±0.6 m). On stairs and ramps they are exact.
- Building a course takes 0.3–1 s in the browser.

Caveats: the upper body is the neutral level walk. No stair-specific data was found for arm swing or gaze, so these are unchanged (people look down more on stairs, Cromwell & Wellmon 2001). The dataset locks the lumbar joint and has no trunk markers, so trunk lean is inferred from the pelvis. No handrail.

Sources (add to the root list):

- Camargo J, Ramanathan A, Flanagan W, Young A (2021). A comprehensive, open-source dataset of lower limb biomechanics in multiple conditions of stairs, ramps, and level-ground ambulation and transitions. *Journal of Biomechanics* 119:110320. [doi:10.1016/j.jbiomech.2021.110320](https://doi.org/10.1016/j.jbiomech.2021.110320). Data: Mendeley Data [fcgm3chfff](https://doi.org/10.17632/fcgm3chfff.1), [k9kvm5tn3f](https://doi.org/10.17632/k9kvm5tn3f.1), [jj3r5f9pnf](https://doi.org/10.17632/jj3r5f9pnf.1) (CC-BY-4.0).
- Leroux A, Fung J, Barbeau H (2002). Postural adaptation to walking on inclined surfaces: I. Normal strategies. *Gait & Posture* 15(1):64–74. [doi:10.1016/s0966-6362(01)00181-3](https://doi.org/10.1016/s0966-6362(01)00181-3).
- Cromwell RL, Wellmon R (2001). Sagittal plane head stabilization during level walking and ambulation on stairs. *Physiotherapy Research International* 6(3):179–192. [doi:10.1002/pri.226](https://doi.org/10.1002/pri.226).
- Chardon M, Barbieri FA, Hansen C, Petit P, Vuillerme N (2024). Impact of overweight on spatial-temporal gait parameters during obstacle crossing in young adults: a cross-sectional study. *Sensors* 24(23):7867. [doi:10.3390/s24237867](https://doi.org/10.3390/s24237867).
- Lu S-H, Kuan Y-C, Wu K-W, Lu H-Y, Tsai Y-L, Chen H-H, Lu T-W (2022). Kinematic strategies for obstacle-crossing in older adults with mild cognitive impairment. *Frontiers in Aging Neuroscience* 14:950411. [doi:10.3389/fnagi.2022.950411](https://doi.org/10.3389/fnagi.2022.950411).

中文簡介（可貼入根目錄 README 的中文段落）：

**上下樓梯與斜坡（`stairs/`）：**

- **腿與骨盆：** Camargo 等人 2021 年的資料庫，22 位成人上下 4 種階高的樓梯與 6 種坡度的斜坡，只取穩態步週期。
- **踩在踏面上：** 站立腳不滑動，身體高度由「承重點在踏面或坡面上」反推。上樓時腳跟懸在踏面邊緣外 4–6 cm，下樓時腳尖貼著邊緣。
- **步態事件：** 觸地與離地改由腳跟、腳尖標記點判定；資料庫原本的事件在下樓時晚了約 130 ms。
- **軀幹前傾：** 依同一批受試者相對平地行走的骨盆前傾量：上樓 +6.5 至 +8.1°，下樓幾乎不變。
- **無限樓梯：** 鏡頭跟著斜向移動，樓梯一直延伸。
- **地形 Course：** 平地、樓梯、坡道、路緣與跨欄串成一圈無縫循環（4 種預設與隨機）。樓梯與坡道的上下轉換步取自同一資料庫的實測轉換步週期與擺動期；跨欄的腳尖離障高度、跨越時的髖膝屈曲與落腳位置依 Chardon 2024、Lu 2022 建模，擺動腳離欄高度正好等於模型值。
