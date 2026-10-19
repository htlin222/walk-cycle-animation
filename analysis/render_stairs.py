"""Render the README / social images of stairs/index.html: assets/stairs-cycle.gif and assets/stairs-og.png.

Usage: python render_stairs.py      (Playwright Chromium + ffmpeg on PATH; CHROMIUM=/path/to/chrome to use a local build)
Frame-stepped and deterministic: the page's clock is driven from here, not by requestAnimationFrame.
Both show the 地形 Course mode, 綜合 preset. The GIF walks (real time) from the level approach up the 5 stairs, over
the landing, down the other side and over the 20 % hurdle; the OG image is the walker on the way up the flight.
"""
import pathlib, subprocess, shutil, os
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
FR = ROOT / 'build' / 'stairs_frames'
FPS, T0, T1 = 20, 3.0, 14.0          # seconds along the 綜合 lap
shutil.rmtree(FR, ignore_errors=True); FR.mkdir(parents=True)
frame = lambda pg: pg.evaluate("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
START = """(t)=>{ setPlay(false); setMode('course',true); setCond('course:mixed',true); applyCond('course:mixed');
  advance(t); prints.length=0; advance(0.6); }"""          # the last 0.6 s leaves footprints and settles the springs
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM')); pg = b.new_page(viewport={'width': 1200, 'height': 630})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto((ROOT / 'stairs' / 'index.html').as_uri()); pg.wait_for_timeout(800)
    pg.evaluate("""(()=>{ document.querySelector('.rail').style.display='none'; resize(); })()""")
    pg.evaluate(START, 4.4)
    frame(pg); pg.screenshot(path=str(ROOT / 'assets' / 'stairs-og.png'))
    pg.set_viewport_size({'width': 720, 'height': 540})
    pg.evaluate("""(()=>{ document.querySelector('header').style.display='none'; resize(); })()""")
    pg.evaluate(START, T0 - 0.6)
    for i in range(round((T1 - T0) * FPS)):
        if i: pg.evaluate(f"advance({1 / FPS})")
        frame(pg); pg.screenshot(path=str(FR / f'{i:04d}.png'))
    print('errors', errs); b.close()
pal = FR / 'palette.png'
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(FR / '%04d.png'),
                '-vf', 'scale=560:-1:flags=lanczos,palettegen=max_colors=48:stats_mode=diff', str(pal)], check=True)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(FR / '%04d.png'), '-i', str(pal),
                '-lavfi', 'scale=560:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle',
                str(ROOT / 'assets' / 'stairs-cycle.gif')], check=True)
print('done')
