"""Render the README / social images of run/index.html: assets/run-cycle.gif and assets/run-og.png.

Usage: python render_run.py      (Playwright Chromium + ffmpeg on PATH; CHROMIUM=/path/to/chrome to use a local build)
Frame-stepped and deterministic: the page's clock is driven from here, not by requestAnimationFrame.
"""
import pathlib, subprocess, shutil, os
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
FR = ROOT / 'build' / 'run_frames'
FPS, SEC, SLOW = 25, 4, 0.5          # 4 s of 0.5× slow motion ≈ 2.8 strides at 3.5 m/s
shutil.rmtree(FR, ignore_errors=True); FR.mkdir(parents=True)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM')); pg = b.new_page(viewport={'width': 1200, 'height': 630})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto((ROOT / 'run' / 'index.html').as_uri()); pg.wait_for_timeout(800)
    pg.evaluate("""(()=>{ setPlay(false); setStyle('run'); blend=1; advance(3); while(Math.abs(G.mod1(phase)-0.43)>0.004) advance(1/960); prints.length=0;   // social image: mid-flight
      document.querySelector('.rail').style.display='none'; resize(); })()""")
    pg.evaluate("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
    pg.screenshot(path=str(ROOT / 'assets' / 'run-og.png'))
    pg.set_viewport_size({'width': 720, 'height': 480})
    pg.evaluate("""(()=>{ document.querySelector('header').style.display='none'; resize(); })()""")
    for i in range(FPS * SEC):
        pg.evaluate(f"advance({SLOW / FPS})")
        pg.evaluate("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
        pg.screenshot(path=str(FR / f'{i:04d}.png'))
    print('errors', errs); b.close()
pal = FR / 'palette.png'
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(FR / '%04d.png'),
                '-vf', 'scale=600:-1:flags=lanczos,palettegen=max_colors=48', str(pal)], check=True)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(FR / '%04d.png'), '-i', str(pal),
                '-lavfi', 'scale=600:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4', str(ROOT / 'assets' / 'run-cycle.gif')], check=True)
print('done')
