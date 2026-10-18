"""Render the README / social images of index.html (walk): assets/walk-cycle.gif, assets/og-image.png, assets/screenshot.png.

Usage: python render_walk.py      (Playwright Chromium + ffmpeg on PATH; CHROMIUM=/path/to/chrome to use a local build)
Frame-stepped and deterministic: the page's clock is driven from here, not by requestAnimationFrame.
  og-image.png   1200x630, happy style, fixed camera, at heel strike
  screenshot.png 1440x900 at 2x, neutral style, fixed camera, at heel strike
  walk-cycle.gif 720x480, happy style, following camera, title only (no nav / controls), two strides at 20 fps (loops seamlessly)
"""
import pathlib, subprocess, shutil, os
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
FR = ROOT / 'build' / 'walk_frames'
FPS = 20
shutil.rmtree(FR, ignore_errors=True); FR.mkdir(parents=True)
RAF = "new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))"
SETUP = """(st)=>{ setPlay(false); setStyle(st); blend=1; advance(4); while(G.mod1(phase)>0.003) advance(1/960); prints.length=0; blinkAt=simT+9; }"""
CAM = """(c)=>{ camMode=c; camBtns.forEach(x=>x.setAttribute('aria-pressed', x.dataset.c===c)); camX=null; }"""
CENTRE = """(f)=>{ camX=travel-W*f/S; updateCamera(); }"""   # put the walker at this fraction of the width
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM'))
    errs = []
    for (w, h, dpr, st, out) in [(1200, 630, 1, 'happy', 'og-image.png'), (1440, 900, 2, 'neutral', 'screenshot.png')]:
        pg = b.new_page(viewport={'width': w, 'height': h}, device_scale_factor=dpr); pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto((ROOT / 'index.html').as_uri()); pg.wait_for_timeout(800)
        pg.evaluate(CAM, 'fixed'); pg.evaluate(SETUP, st); pg.evaluate(CENTRE, 0.5); pg.evaluate(RAF)
        pg.screenshot(path=str(ROOT / 'assets' / out)); pg.close()
    pg = b.new_page(viewport={'width': 720, 'height': 480}); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto((ROOT / 'index.html').as_uri()); pg.wait_for_timeout(800)
    # small frame: the title and the walker only (the nav and controls would cover the legs at 720x480)
    pg.evaluate("(()=>{ document.querySelector('header p.nav').style.display='none'; document.querySelector('.rail').style.display='none'; resize(); })()")
    pg.evaluate(CAM, 'follow'); pg.evaluate(SETUP, 'happy')
    period = pg.evaluate("120/cadB()")          # one stride, seconds
    n = round(2 * period * FPS)
    for i in range(n):
        if i: pg.evaluate(f"advance({2 * period / n})")
        pg.evaluate(RAF); pg.screenshot(path=str(FR / f'{i:04d}.png'))
    print('frames', n, 'errors', errs); b.close()
pal = FR / 'palette.png'
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(FR / '%04d.png'),
                '-vf', 'palettegen=max_colors=64', str(pal)], check=True)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(FR / '%04d.png'), '-i', str(pal),
                '-lavfi', 'paletteuse=dither=bayer:bayer_scale=4', str(ROOT / 'assets' / 'walk-cycle.gif')], check=True)
print('done')
