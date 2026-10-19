"""Render the README / social images of pitch/index.html: assets/pitch-cycle.gif and assets/pitch-og.png.

Usage: python render_pitch.py      (Playwright Chromium + ffmpeg on PATH; CHROMIUM=/path/to/chrome to use a local build)
Frame-stepped and deterministic: the page's clock is driven from here, not by requestAnimationFrame.
The GIF plays one pitch in the 斜前 3/4 view with a variable slow motion: the set position and the reset at real time,
the leg lift and stride at 0.5×, and foot contact → end of the data at 0.1× (the arm's 30 ms acceleration spans 8 frames).
"""
import pathlib, subprocess, shutil, os
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
FR = ROOT / 'build' / 'pitch_frames'
FPS = 25
SLOW = "(tau<SET ? 1 : tau<tauOf('FC') ? 0.5 : tau<SET+DATA ? 0.1 : 1)"   # playback rate by phase
shutil.rmtree(FR, ignore_errors=True); FR.mkdir(parents=True)
raf = "new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM')); pg = b.new_page(viewport={'width': 1200, 'height': 630})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto((ROOT / 'pitch' / 'index.html').as_uri()); pg.wait_for_timeout(800)
    # social image: 3/4 view a few ms before release, arm whipping forward, curves panel on
    pg.evaluate("""(()=>{ setPlay(false); document.querySelector('.cam[data-c="q34"]').click(); camAz=camAzT; camEl=camElT; setCam();
      seek(tauOf('BR')-0.012); advance(0); document.querySelector('.rail').style.display='none'; resize(); })()""")
    pg.evaluate(raf); pg.evaluate(raf)
    pg.screenshot(path=str(ROOT / 'assets' / 'pitch-og.png'))
    pg.set_viewport_size({'width': 720, 'height': 480})
    pg.evaluate("""(()=>{ document.querySelector('header').style.display='none'; crv.checked=false; resize(); seek(0); accum=0; })()""")
    i = 0
    while True:
        pg.evaluate(raf)
        pg.screenshot(path=str(FR / f'{i:04d}.png')); i += 1
        done = pg.evaluate(f"(()=>{{ const r={SLOW}; speed=r; const t0=tau; advance(r/{FPS}); return tau<t0; }})()")   # speed: the release label's fade clock
        if done: break
    print('frames', i, 'errors', errs); b.close()
pal = FR / 'palette.png'
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(FR / '%04d.png'),
                '-vf', 'scale=540:-1:flags=lanczos,palettegen=max_colors=48', str(pal)], check=True)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(FR / '%04d.png'), '-i', str(pal),
                '-lavfi', 'scale=540:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4', str(ROOT / 'assets' / 'pitch-cycle.gif')], check=True)
print('done', (ROOT / 'assets' / 'pitch-cycle.gif').stat().st_size // 1024, 'KB')
