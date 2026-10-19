# Dance cycle (`dance/`)

**Live:** https://htlin222.github.io/walk-cycle-animation/dance/

This folder holds the dance counterpart of the walk and run pages. The section between the two rules below is written to be pasted into the root README as it stands, after "## Run cycle". The rest of this file covers the data source, the camera choice and the checks.

---

## Dance cycle

[![Animated dance cycles: Charleston, salsa, Indian dance](../assets/dance-cycle.gif)](https://htlin222.github.io/walk-cycle-animation/dance/)

`dance/index.html` uses the walk page's body, drawing, springs and shadows. The figure dances in place, and every number underneath comes from motion capture.

| Layer | Source | How it is used |
|---|---|---|
| Whole body, three styles | CMU motion capture: Charleston (subject 93, 3 clips), salsa (subject 60, the leader of a couple, 3 stretches; the partner, subject 61, is measured for tempo only), Indian dance (subject 94, 2 stretches) | Travel and turning are averaged out over one cycle. Repeated cycles are phase-aligned (whole-beat shifts, left/right mirror allowed), averaged and Fourier-smoothed below 10 Hz. For salsa only the 5 of the leader's 10 cycles closest to their average are kept. |
| Tempo | Measured from the motion itself | The cycle is the period over which the whole pose repeats (autocorrelation of feet, hands, pelvis and head). The beat is the vertical pelvis bounce: the strongest harmonic of the cycle with a period of 0.3–1.2 s. Sample 0 of every loop is a bounce trough, so it falls on a beat. |
| Feet | Contacts detected from foot height and speed | A planted shoe pivots on its heel (toes up) or its ball (heel up) around one stored floor point per contact, so it cannot slide. Swing is corrected with Hermite blends. |
| Metronome | WebAudio, no audio files | Optional click on every measured beat (accent on beat 1), scheduled from the animation's own clock. Off by default. |

### Measured tempo (this repo's analysis)

| | Charleston | Salsa | Indian |
|---|---|---|---|
| Clips (CMU) | 93_03, 93_04, 93_05 | 60_02, 60_03, 60_04 (pose and tempo); 61_01, 61_02 (tempo) | 94_08 (two halves) |
| Cycles averaged | 7 | 5 (best of 10) | 23 |
| Cycle (pose repeat) | 1.30 s | 2.92 s | 0.78 s |
| Pelvis bounces per cycle | 4 | 4 | 1 |
| **Beat (pelvis bounce)** | **185 BPM (3.1 Hz)** | **82 BPM (1.4 Hz)** | **77 BPM (1.3 Hz)** |
| Per stretch | 179, 180, 197 BPM | 81–84 BPM (5 stretches, 2 dancers) | 77, 77 BPM |
| Touchdowns (raw clips) | 3.0 per s | 1.9 per s | 2.7 per s |
| Pelvis vertical travel | 5.3 % leg length | 5.4 % leg length | 5.5 % leg length |

Dancing is beat-locked. Each style keeps one period across clips and dancers. The two salsa partners repeat their basic every 2.86–2.96 s, and the pelvis bounces a fixed whole number of times per cycle.

**Why the salsa pose comes from one dancer.** The partners share the tempo but not the step. The leader (subject 60) dances a forward-and-back basic: the ankles travel 0.7–1.1 leg lengths fore-aft per cycle and 0.1–0.5 sideways. The follower (subject 61) mostly steps side to side, 1.0–1.7 leg lengths laterally and 0.2–0.4 fore-aft. Averaging all 16 cycles of both cancelled the steps: 0.5 leg lengths each way, both feet on the floor 73 % of the time and 4 touchdowns per cycle, which looked like shuffling on the spot. The pose now averages the leader only. Of the leader's 10 aligned cycles it keeps the 5 that correlate best with their mean (r = 0.85–0.89), which keeps averaging's noise reduction without blurring the timing. Ankle travel is 0.79 and 0.83 leg lengths fore-aft, close to single cycles (0.7–0.9). Both feet are down 32 % of the time and there are 5 touchdowns per cycle; the raw stretches have 5.5. The 30° camera also favours this choice, because fore-aft steps keep 87 % of their size on screen and sideways steps only 50 %. A single cycle was not used: its loop seam would need a cross-fade of its own, and one cycle carries one take's stumbles. The follower's stretches still count toward the measured beat (beats per cycle) and appear in the per-stretch tempo.

Human movement to music clusters near 2 Hz (120 per minute). Free locomotion over a whole day peaks at 2.0 Hz (MacDougall & Moore 2005), and pulse perception is modelled as a resonance near 2 Hz (van Noorden & Moelants 1999). The salsa footfalls land at 1.9 per second, right at that value. The pelvis beats spread around it: 3.1 Hz for Charleston, 1.3–1.4 Hz for salsa and Indian dance. The motion also does not fix the metrical level. If the 2.9 s salsa cycle is the 8-count basic, there are two counts per pelvis bounce (164 per minute), and the Indian stamp could be counted twice per bounce (154). This matches the finding that different body parts lock to different metrical levels at the same time (Toiviainen, Luck & Thompson 2010). In that study the period of upper-torso rotation was two beats and lateral flexion four.

### How dancing differs from the walk and run solvers

- **No travel.** Walking and running are solved forward from the feet or from ground force. Dancers here turn and drift around the capture floor, so the body frame follows a one-cycle moving average of position and heading. The figure dances on the spot and the planted feet are re-anchored in that frame.
- **The seam is the recording's own.** Each cycle is cut with a quarter cycle of what came before and after it. Around the loop point the average of "the cycle running on" cross-fades into "the next cycle, as it was approached". Without this, the drift left after averaging becomes a kink at beat 1.
- **A 30° camera.** The motion is 3D but the rig is a 2D profile drawing. The camera stays horizontal and turns 30° from profile toward the dancer's front. Lateral steps, the salsa hold and raised arms show at half their amplitude (sin 30°). Fore-aft motion keeps 87 % (cos 30°). The profile head, torso and shoes still read correctly, and because the camera does not tilt the floor stays one line, so contacts and floor depth are exact.
- **Arms and legs from projected joints.** Knees are re-solved in the picture plane with the recorded segment lengths (stretch at most 2.7 %). Arm directions and foreshortening come from the data at the rig's arm lengths.
- **The trunk starts at the hip joints.** CMU's root joint sits at the sacrum, about 0.12 leg lengths above the hip joints. The rig (as in the run and jump pages) builds the trunk up from the hip joints, so the page anchors it there. Anchored at the root, the shirt floated above the trousers and the torso was drawn 0.12 leg lengths too long.
- **The Charleston lean is real.** The trunk tilts about 35° forward through the Charleston. In the raw BVH, hips-to-neck is 24–36° from the world vertical on average per clip, ranging 4–47°, while the same subject's T-pose stands within 3° of vertical. The lean does not come from the camera or the body-frame rotation. It is the crouched, bent-forward posture of the step.
- **Lift-off and touchdown are eased.** A planted shoe pivots about its floor point, while the recorded ankle keeps drifting a little. Over the one sample next to each contact the page eases between the two, so the foot no longer jumps by up to 0.013 leg lengths when it is released or caught.
- **Checks.** [`analysis/check_dance.py`](../analysis/check_dance.py) runs the page in headless Chromium. The seam is no rougher than the rest of the cycle (≤ 0.0003 leg lengths beyond the roughest step elsewhere; measured 0). Planted feet slip 0.0 leg lengths/s over 67,000 planted samples. No sole point goes more than 0.00001 leg lengths below the floor. At lift-off and touchdown the ankle step is no larger than the largest step elsewhere. The trunk's base sits on the hip joints. There are no NaNs.

Controls: playback speed, style 查爾斯頓 Charleston / 騷莎 Salsa / 印度舞 Indian (cross-fades), exaggeration (secondary motion only), 節拍器 Click (metronome at the measured BPM), skeleton overlay with ankle paths and the pelvis-bounce curve. The beat chips count the beats of the cycle.

---

## Data source: AIST++ was intended but unreachable

The intended source was AIST++ (Li et al. 2021, "AI Choreographer"): 1,408 dance sequences (5.2 hours) in 10 genres, each with its music, so the musical beat is known exactly. It is hosted on Google Cloud Storage, which this environment could not reach. The module therefore uses the CMU Graphics Lab Motion Capture Database, which has no music. The tempo here is measured from the motion alone. If AIST++ becomes reachable, the same pipeline can take its SMPL joints, and the pelvis-bounce beat can then be checked against the music's annotated BPM.

Clips are the cgspeed BVH conversion (the same as the walk and run analysis), fetched from the per-subject zip files in [Shriinivas/cmubvh](https://github.com/Shriinivas/cmubvh). Put them in `analysis/bvh/`.

- **Charleston:** subject 93, trials 3–5 ("charleston_01", "charleston_side_by_side_female", "charleston_side_by_side_male"). Each is a 3–4 s clip of about two basics. 93_04 is the mirror image of the other two and is mirrored back. 93_08 ("xtra fancY charleston") has frozen frames and is not used.
- **Salsa:** subjects 60 and 61 ("salsa dance"), the two partners recorded together. Only stretches where the pose repeats (autocorrelation r ≥ 0.25) are used: 60_02 4–13 s, 60_03 14–25 s, 60_04 14–28 s, 61_01 7–19 s, 61_02 17–28 s. All five set the tempo; only subject 60's three shape the pose (see "Why the salsa pose comes from one dancer").
- **Indian:** subject 94, trial 8 (the CMU index leaves the description blank; the capture header reads "IndianDance"). It is a steady stamping step that travels in a circle: right foot leading for 1.2–10.5 s, left foot leading for 10.8–21.3 s. The second half is mirrored to match the first.
- **Frame rate.** The CMU index lists subjects 60 and 61 at 60 fps. The BVH conversion stamps every file 1/120 s, and the AMC files have the same frame counts, so the BVH timing would double the salsa tempo. The analysis uses 60 fps. At 120 fps the salsa basic would be 1.45 s long (331 per minute on the 8-count), which is implausible.

Other CMU dance material was looked at and not used. Trials 94_01–94_07 travel or change step too often to loop, and the Lindy hop (93_06) travels. Subject 5 (modern dance) was not analysed: its trials are sequences of different moves, not repeated steps.

## Reproduce

```
python analysis/dance_cmu.py --embed     # → analysis/data/dance_cmu.json, and rewrites const DANCE in dance/index.html
python analysis/check_dance.py           # seam / slip / floor / NaN checks in headless Chromium; exits 1 on failure
python analysis/render_dance.py          # → assets/dance-cycle.gif, assets/dance-og.png
```

Lines for the root README's "Reproduce the data" file list, and for the links at the top:

```
  dance_cmu.py        CMU dance clips → tempo from the motion, phase-aligned and averaged cycles, locked feet → data/dance_cmu.json (embedded in dance/index.html)
  check_dance.py      loop seam / foot slip / floor / NaN checks of dance/index.html in headless Chromium
  render_dance.py     → assets/dance-cycle.gif, assets/dance-og.png
```

```
▶ **Dance:** [`dance/`](dance/) loops Charleston, salsa and Indian dance from CMU motion capture, with the tempo measured from the motion itself ([live](https://htlin222.github.io/walk-cycle-animation/dance/), [details below](#dance-cycle)).
```

中文簡介 (for the root README's 中文簡介):

**跳舞（`dance/`）：**

- **三種舞：** 查爾斯頓、騷莎、印度舞，全部來自 CMU 真人動作捕捉。重複的小節對齊後平均，原地跳。
- **節拍由動作量出：** 骨盆上下彈動定出拍子。查爾斯頓 185 BPM、騷莎 82 BPM（八拍基本步每次彈動兩拍，等於 164）、印度舞 77 BPM。
- **騷莎只用帶舞者：** 兩位舞伴節奏相同、步法不同（前後步 vs 左右步），一起平均會互相抵消，所以只取帶舞者（受試者 60）10 個循環中最接近平均的 5 個。
- **約 2 Hz：** 騷莎落腳每秒 1.9 次，接近人類動作偏好的 2 Hz；其他兩種舞的拍子則分布在 2 Hz 兩側。
- **接地的腳不滑步：** 以腳跟或前掌為支點鎖在地上，滑動為 0。
- **節拍器：** 可開啟，依量到的 BPM 打拍，預設關閉。

## Sources

- CMU Graphics Lab Motion Capture Database, http://mocap.cs.cmu.edu/ (subjects 60, 61, 93, 94). BVH conversion by B. Hahne (cgspeed), mirrored in [Shriinivas/cmubvh](https://github.com/Shriinivas/cmubvh).
- MacDougall HG, Moore ST (2005). Marching to the beat of the same drummer: the spontaneous tempo of human locomotion. *Journal of Applied Physiology* 99(3):1164–1173. [doi:10.1152/japplphysiol.00138.2005](https://doi.org/10.1152/japplphysiol.00138.2005)
- van Noorden L, Moelants D (1999). Resonance in the perception of musical pulse. *Journal of New Music Research* 28(1):43–66. [doi:10.1076/jnmr.28.1.43.3122](https://doi.org/10.1076/jnmr.28.1.43.3122)
- Toiviainen P, Luck G, Thompson MR (2010). Embodied meter: hierarchical eigenmodes in music-induced movement. *Music Perception* 28(1):59–70. [doi:10.1525/mp.2010.28.1.59](https://doi.org/10.1525/mp.2010.28.1.59)
- Van Dyck E, Moelants D, Demey M, Deweppe A, Coussement P, Leman M (2013). The impact of the bass drum on human dance movement. *Music Perception* 30(4):349–359. [doi:10.1525/mp.2013.30.4.349](https://doi.org/10.1525/mp.2013.30.4.349). Dancers' tempo entrainment rose with the bass-drum level. This is why a beat is worth measuring at all.
- Li R, Yang S, Ross DA, Kanazawa A (2021). AI Choreographer: music conditioned 3D dance generation with AIST++. *ICCV 2021*. Intended data source, not reachable from the build environment.
