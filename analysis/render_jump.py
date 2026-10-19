"""Render the README / social images of jump/index.html: assets/jump-cycle.gif and assets/jump-og.png.

Usage: python render_jump.py      (Playwright Chromium + ffmpeg on PATH; CHROMIUM=/path/to/chrome to use a local build)
Frame-stepped and deterministic: the page's clock is driven from here, not by requestAnimationFrame.
"""
import pathlib, subprocess, shutil, os
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
FR = ROOT / 'build' / 'jump_frames'
FPS, SLOW = 25, 0.75                  # one countermovement jump (2.75 s) at 0.75× ≈ 3.7 s
shutil.rmtree(FR, ignore_errors=True); FR.mkdir(parents=True)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM')); pg = b.new_page(viewport={'width': 1200, 'height': 630})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto((ROOT / 'jump' / 'index.html').as_uri()); pg.wait_for_timeout(800)
    pg.evaluate("""(()=>{ setPlay(false); setStyle('cmj'); advance(2*M.TOT-clock+0.01); advance((M.t0[4]+M.t0[5])/2-clock); prints.length=0;   // social image: top of the flight
      document.querySelector('.rail').style.display='none'; resize(); camX=null; })()""")
    pg.evaluate("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
    pg.screenshot(path=str(ROOT / 'assets' / 'jump-og.png'))
    pg.set_viewport_size({'width': 720, 'height': 480})
    pg.evaluate("""(()=>{ document.querySelector('header').style.display='none'; resize(); advance(M.TOT-clock+0.4); camX=null; })()""")
    n = int(round(pg.evaluate("M.TOT") / SLOW * FPS))
    for i in range(n):
        pg.evaluate(f"advance({SLOW / FPS})")
        pg.evaluate("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
        pg.screenshot(path=str(FR / f'{i:04d}.png'))
    print('errors', errs); b.close()
pal = FR / 'palette.png'
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(FR / '%04d.png'),
                '-vf', 'scale=600:-1:flags=lanczos,palettegen=max_colors=48', str(pal)], check=True)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(FR / '%04d.png'), '-i', str(pal),
                '-lavfi', 'scale=600:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4', str(ROOT / 'assets' / 'jump-cycle.gif')], check=True)
print('done')
