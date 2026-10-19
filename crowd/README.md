# Crowd walk

A packed crowd of 140 people walking together, rendered to a clean 16:9 video (1920×1080, 30 fps, 20 s, no UI).

Every walker uses the page's neutral gait (`walk/index.html`, GAIT-BEGIN…GAIT-END) and the same no-slip simulation, running on its own spring state and its own clock.

## What differs between walkers

- **Timing.** Each walker's clock is shifted by a start offset τ drawn uniformly from ±100 ms. Walker *i* at time *T* is exactly the reference walker at *T + τᵢ*.
- **Height.** Height varies by ±10 % (five bins: 0.90–1.10). Everyone shares one cadence, so the ±τ timing stays exact. Stride in leg lengths scales as 1/h (each bin is a separate `fitStyle` gait), so shorter people take relatively longer steps and the whole crowd keeps one walking speed.
- **Look.** Seeded random choices for:
  - skin tone and build;
  - 14 hair styles, including dyed colours;
  - shirt prints, open jackets, skirts and dresses;
  - beards, glasses, earrings, necklaces, backpacks and headphones.

## Camera and depth of field

- **Camera.** A high follow camera tracks the crowd's mean travel. The horizon sits above the frame, so rows further back stack up to the top edge.
- **Depth of field.** The blur radius is proportional to |k(z) − k(focus)|, where k is the perspective scale; behind the focus plane the blur is softer. Radii snap to six levels, and walkers sharing a level are blurred as one layer. Heavy levels are blurred at half resolution.

## Files

| File | Role |
|---|---|
| `gait.js` | Copy of the gait block from `../index.html`. `video.py` refreshes it on every run. |
| `crowd.js` | Per-walker simulation, looks, crowd layout, perspective renderer with depth of field. |
| `render.html` | Headless harness: `setup(w, h, seed, offset, mode, n)`, `advance(dt)`, `drawNow()`. |
| `video.py` | Deterministic frame-stepped capture in parallel Chromium workers, then ffmpeg encoding to `walk-crowd-dof-1080p.mp4`. |

## Render

```
pip install playwright && playwright install chromium   # plus ffmpeg on PATH
python3 crowd/video.py        # optional argument: number of parallel workers (default 2)
```

Size, frame rate, length, head count, seed and offset are set on the first lines of `video.py`. `setup(..., 'stand', n)` starts everyone from standing instead of mid-stride.
