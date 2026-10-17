# Jump Study (`jump/`)

`jump/index.html` loops a **countermovement jump** (CMJ, straight up) and a **standing broad jump**. It uses the walk page's body, drawing, springs and point-light shadow, like `run/`. The jump underneath is averaged from motion capture and cut into the force-plate phases of the CMJ. Flight follows Newton: the centre of mass (COM) is on a parabola with g = 9.81 m/s².

> **Data source note.** The intended source was the AddBiomechanics dataset (marker-based kinematics *and* ground forces for many jumpers). It could not be reached from the environment this module was built in. The module therefore uses **CMU Graphics Lab motion capture** for the kinematics, and **physics plus the published CMJ literature** for everything a force plate would have given (phase definitions, flight-time height, landing height, the role of the arm swing). If AddBiomechanics becomes reachable, it is the better source, because its jumps have measured forces.

Below is a section ready to paste into the root `README.md` (same structure as "## Run cycle"), followed by details that do not need to go there.

---

## Ready to paste into the root README

The link line, after the `▶ **Run:**` line near the top:

```markdown
▶ **Jump:** [`jump/`](jump/) loops a countermovement jump and a standing broad jump, averaged from motion capture and cut into force-plate phases ([live](https://htlin222.github.io/walk-cycle-animation/jump/), [details below](#jump)).
```

The section, after "## Run cycle":

```markdown
## Jump

[![Animated countermovement jump, 0.75× speed](assets/jump-cycle.gif)](https://htlin222.github.io/walk-cycle-animation/jump/)

`jump/index.html` uses the walk page's body, drawing, springs and shadows. It loops a countermovement jump (CMJ) and a standing broad jump. The intended source, AddBiomechanics, was not reachable when this was built. Kinematics come from CMU motion capture; the dynamics come from physics and the CMJ literature.

| Layer | Source | How it is used |
|---|---|---|
| Legs, pelvis, trunk, head | CMU motion capture. CMJ: 7 jumps by 3 actors (subjects 13, 16, 49). Broad jump: 13 jumps by 3 actors (subjects 13, 16, 118). | Foot pitch, hip relative to ankle, trunk and head angles. Each jump is cut into phases, time-normalised phase by phase, averaged within each actor, then across actors. |
| Phases | Force-plate CMJ phases (McMahon et al. 2018) | Weighing → unweighting (to peak downward COM velocity) → braking (to the bottom, COM velocity zero) → propulsion → flight → landing (to COM velocity zero again) → recovery. CMU has no force plate, so the events are found on the COM. |
| Centre of mass | Dempster segment parameters (Winter 2009) | Whole-body COM from 14 segments of each recording. It finds the phases and carries the flight. |
| Flight | Projectile motion; jump height h = g T² / 8 from flight time T (Linthorne 2001) | Ballistic: the COM leaves the take-off pose and lands in the touchdown pose after the measured flight time, under gravity alone. |
| Arm swing | Lees et al. 2004: arm swing raises a vertical jump by 8.6 cm | Only some CMU actors swing their arms. The arm curves come from the jumps that do (shoulder range > 60°). |

### Measured jumps (CMU, this repo's analysis)

| | Countermovement jump | Standing broad jump |
|---|---|---|
| Flight time | 473 ms | 433 ms |
| Height from flight time, g T² / 8 | 27.8 cm | 23.4 cm |
| COM rise above take-off | 25.1 cm | 20.2 cm |
| Distance (toes, start → landing) | 5 cm (on the spot) | 1.27 m |
| Countermovement depth (COM) | 21.4 cm | 19.5 cm |
| Knee flexion at the bottom | 93° | 83° |
| Unweighting / braking / propulsion | 421 / 154 / 239 ms | 419 / 167 / 266 ms |
| Landing (touchdown → deepest point) | 156 ms, COM 14.8 cm below standing | 150 ms, 11.7 cm below |

Flight-time height is 2.7 cm (CMJ) and 3.2 cm (broad jump) above the COM's actual rise. The COM lands 6–7 cm lower than it took off: knees and hips are already bending, and the arms come down from the swing. Linthorne (2001) describes exactly this bias of the flight-time method: the COM lands lower than it took off, so the method overestimates height, and more so with an arm swing.

### Physics checks

- **g from the recordings.** A free parabola fitted to each recorded COM in the air gives 9.69–10.10 m/s² (CMJ) and 9.73–10.35 m/s² (broad jump), mean 9.85 and 9.94. The fit residual is 0.6–4.0 mm. The pelvis alone is not ballistic (9.71–10.76 m/s²), because the legs and arms move about the COM. Five broad jumps were dropped because their COM did not fall at g (11.1–11.9 m/s²) or the fit residual was above 4 mm.
- **g on the page.** The page does not replay the recorded COM in the air. It uses the exact parabola between the take-off and touchdown poses in the measured flight time. Fitting the page's COM gives 9.81 m/s² with zero residual.
- **No slip.** While a foot carries weight, the ball of the foot is pinned to the floor; ankle, hip and COM hang off it through the recorded chain. In toe-off and toe-strike the foot rolls over its toes and the toe tip is pinned. Pinned points move 0.0 mm, and nothing goes below the floor by more than 0.1 mm. [`analysis/check_jump.py`](analysis/check_jump.py) measures all of these in headless Chromium.
- **Take-off speed.** The COM leaves the floor at 2.38 m/s (CMJ) and continues at 2.17 m/s on the parabola. It lands at 2.42 m/s and continues into the landing at 2.65 m/s. The broad jump's speeds match within 5 %.

### How jumping differs from the run

- **Phases, not a cycle.** Walking and running repeat one stride. A jump is a sequence with its own measured duration per phase, so it plays on a clock, not on a phase angle. After the recovery, the figure settles back into quiet stance for 1 s, the weighing time McMahon et al. recommend.
- **Toe-off.** Pivoting on the ball of the foot cannot lift the ankle as fast as the recordings show in the last 0.1 s before take-off. With the ball pinned, the COM would leave the floor at a third of its recorded speed and then jump onto the parabola. In that window the ankle follows its recorded height, the ball lifts on an arc about the toe tip, and the toe tip stays on the floor.
- **Shadow under a body in the air.** With the fixed camera, the light hangs LH = 4.2 leg lengths above the floor. Lifting the body by h makes its shadow LH / (LH − h) larger, softer and fainter, and it shrinks and sharpens again on landing. The ambient shadow under the body spreads and fades with height.

Controls: playback speed, 原地跳 CMJ / 立定跳遠 broad jump (the switch waits for the current jump to finish), camera 固定鏡頭 fixed (default) / 跟隨 follow, exaggeration, skeleton overlay with the COM path and a COM-height trace. The phase chips show Stand → Unweight → Brake → Propel → Flight → Land → Recover.
```

Lines for "## Reproduce the data" (add to the `analysis/` tree, and a pipeline sentence below the running one):

```markdown
  jump_cmu.py         CMU jump clips → data/jump_cmu.json (per-clip stats, phase curves), data/jump_styles.json (embedded in jump/index.html)
  check_jump.py       slip / floor / flight-parabola checks of jump/index.html in headless Chromium
  render_jump.py      → assets/jump-cycle.gif, assets/jump-og.png
```

```markdown
Jump pipeline: `python analysis/jump_cmu.py`, then paste `data/jump_styles.json` into `const JUMP` in `jump/index.html`. The jump clips are 13_39–13_42, 16_01, 16_02, 49_02, 49_03 (CMJ) and 13_11, 13_13, 13_19, 13_32, 16_05–16_07, 16_09, 16_10, 118_18–118_29 (broad jump); clips without a quiet start or with a non-ballistic flight are skipped automatically.
```

Bullets for "## 中文簡介":

```markdown
**跳躍（`jump/`）：**

- **動作：** CMU 動作捕捉。原地反向跳 7 次、3 位演員；立定跳遠 13 次、3 位演員。依測力板文獻的階段（站立、卸重、制動、推蹬、騰空、落地）切分後平均。原本預定使用 AddBiomechanics 資料庫，因當時無法連線，改用 CMU 加物理與文獻。
- **騰空：** 重心只受重力，走 g = 9.81 m/s² 的拋物線。騰空 473 ms，依 h = gT²/8 跳高 27.8 cm。
- **觸地腳不滑步：** 承重時前腳掌釘在地上；蹬地與著地瞬間改以腳尖為支點。
- **影子：** 身體離地越高，點光源下的影子越大、越淡、越模糊，落地後縮回。
```

Sources to add under "## Sources":

```markdown
- McMahon JJ, Suchomel TJ, Lake JP, Comfort P (2018). Understanding the key phases of the countermovement jump force-time curve. *Strength and Conditioning Journal* 40(4):96–106. [doi:10.1519/SSC.0000000000000375](https://doi.org/10.1519/SSC.0000000000000375)
- Linthorne NP (2001). Analysis of standing vertical jumps using a force platform. *American Journal of Physics* 69(11):1198–1204. [doi:10.1119/1.1397460](https://doi.org/10.1119/1.1397460)
- Lees A, Vanrenterghem J, De Clercq D (2004). Understanding how an arm swing enhances performance in the vertical jump. *Journal of Biomechanics* 37(12):1929–1940. [doi:10.1016/j.jbiomech.2004.02.021](https://doi.org/10.1016/j.jbiomech.2004.02.021)
- Winter DA (2009). *Biomechanics and Motor Control of Human Movement*, 4th ed., Wiley. Dempster segment parameters, as tabulated in [BMClab's BSP_DempsterWinter.txt](https://github.com/demotu/BMC/blob/master/data/BSP_DempsterWinter.txt).
```

---

## Details

### What each cited source is used for

Each claim was checked against the source itself.

- **McMahon et al. (2018)**, author-accepted manuscript. Six phases: weighing ("stand as still as possible… usually for at least 1 second"); unweighting, from movement onset until force returns to body weight, which "coincides with the instant at which peak negative COM velocity is achieved"; braking, from peak negative velocity "through to when COM velocity increases to zero", the bottom of the countermovement; propulsion, to take-off; flight; and landing, which ends "when COM velocity reaches zero again", the deepest landing point. The paper also notes that the flight-time method assumes the same COM height at take-off and touchdown.
- **Linthorne (2001).** v_to = g t_flight / 2 and y_flight = v_to² / 2g, so h = g T² / 8. Worked example: t_flight = 0.553 s, v_to = 2.71 m/s, 37.5 cm. With hands on the hips, the COM at landing is usually 1–4 cm lower than at take-off, so the flight-time method overestimates the height by 0.5–2 cm. With an arm swing the difference is greater. The recorded jumps agree: the flight-time height is 2.7–3.2 cm above the COM rise.
- **Lees et al. (2004)**, 20 adult men. Jumps with an arm swing were 0.086 m higher than without. The gain came from greater COM height (28 %) and velocity (72 %) at take-off. Used only to justify taking the arm curves from the jumps that have a swing.
- **Winter (2009)** / Dempster. Segment mass fractions and COM positions: hand 0.006 @ 0.506, forearm 0.016 @ 0.430, upper arm 0.028 @ 0.436, thigh 0.100 @ 0.433, leg 0.0465 @ 0.433, foot 0.0145 @ 0.5, trunk 0.497 @ 0.5 (greater trochanter ↔ shoulder), head and neck 0.081 at the ear. The fractions sum to 1.000.

### Per-actor results

| Style | Actor (CMU subject) | Jumps | Flight | g T² / 8 | COM depth | Knee at bottom | Distance |
|---|---|---|---|---|---|---|---|
| CMJ | 13 | 3 | 547 ms | 36.9 cm | 31.3 cm | 110° | 0.16 m |
| CMJ | 16 | 2 | 446 ms | 24.5 cm | 17.1 cm | 87° | 0 |
| CMJ | 49 | 2 | 425 ms | 22.2 cm | 15.8 cm | 83° | 0 |
| Broad | 13 | 4 | 456 ms | 25.9 cm | 22.0 cm | 94° | 1.37 m |
| Broad | 16 | 3 | 425 ms | 22.6 cm | 13.5 cm | 72° | 1.19 m |
| Broad | 118 | 6 | 418 ms | 21.7 cm | 23.0 cm | 84° | 1.25 m |

Only subject 13 swings the arms in the CMJ (backward to −65…−91°, forward to +39…+49° at take-off). Subjects 13 and 118 swing them in the broad jump. Per-clip numbers are in `analysis/data/jump_cmu.json` (`clips`).

### Discrepancies found and how they were handled

- **CMU scale and frame rate.** CMU lengths are in units of 0.45 inch. With that scale and 120 fps, the recorded COM falls at 9.7–10.4 m/s² in every kept jump. This independently confirms both numbers.
- **Subjects 141 and 143** ("Jump Distances", "Jumping Heights") were not used. At their stated 120 fps their COM falls at about 38 m/s², roughly 4 g, so time runs at half speed (probably 60 fps). Even at 60 fps the fit gives 8.2–9.6 m/s², which suggests the length scale is also off.
- **Non-ballistic flights.** 16_09, 16_10, 118_26 and 118_28 fall at 11.1–11.9 m/s² (118_28 also has a 625 ms braking phase), and 118_20 has a 4.1 mm residual. These were dropped (|g − 9.81| < 1 m/s², residual < 4 mm). 13_39, the repeated hops in 49_02 / 49_03 and a few 118 clips have no quiet stance before the jump, so they were skipped.
- **Take-off and touchdown timing.** "Both feet 3 cm up" finds the flights, but starts them late and ends them early. The edges are moved to where the recorded COM joins and leaves free fall, within 3 mm of the parabola. This is the force-plate definition (force falls below threshold) expressed in kinematics.
- **Recorded COM vs physics.** The averaged recorded flight is close to ballistic but not exact (mean g 9.85 / 9.94, rms 1.6–2.0 mm). The page therefore does not replay it. It replaces it with the exact g = 9.81 parabola between the recorded take-off and touchdown poses, in the measured flight time. The limbs still move about the COM as recorded.
- **Toe-off.** The page's foot has no toe joint. With the ball pinned to the floor, the ground side of the take-off moved the COM at 0.78 m/s against 2.6 m/s on the parabola. The toe-roll window described above fixes this: the remaining mismatch is 9 % (CMJ) and under 5 % (broad jump).

### Caveats

- 3 actors per style and 7 / 13 jumps. These are motion-capture performers, not a normative sample. Jump heights are typical of recreational jumpers, not athletes.
- Phase events are kinematic (COM velocity from marker-based segment COM), not force-plate events. Any error in COM placement shifts them slightly.
- The CMJ arm swing comes from one actor (subject 13). The broad-jump arm swing comes from two (13 and 118).
- Both legs are averaged and drawn identically; the far foot sits 5 % of a leg length behind the near one, so both legs read in profile.
