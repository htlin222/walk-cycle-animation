"""Render the README / social images of stand/index.html: assets/stand-cycle.gif and assets/stand-og.png.

Usage: python render_stand.py      (Playwright Chromium + ffmpeg on PATH; CHROMIUM=/path/to/chrome to use a local build)
Frame-stepped and deterministic: the page's clock is driven from here, not by requestAnimationFrame.
Eyes closed on foam (the largest sway), magnified x10 so the ankle-pivot sway is visible; skeleton on, so the inverted
pendulum (ankle -> COM), the COM's floor projection and the COP marker show; the stabilogram is drawn at true scale.
"""
import pathlib, subprocess, shutil, os
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
FR = ROOT / 'build' / 'stand_frames'
FPS, SEC, SPEED = 12.5, 8, 1.5       # 8 s of GIF at 1.5x real time = 12 s of sway (the sway is slow: most power < 0.5 Hz)
shutil.rmtree(FR, ignore_errors=True); FR.mkdir(parents=True)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM')); pg = b.new_page(viewport={'width': 1200, 'height': 630})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto((ROOT / 'stand' / 'index.html').as_uri()); pg.wait_for_timeout(800)
    # social image: 12 s in, so the stabilogram holds its full 10 s window
    pg.evaluate("""(()=>{ setPlay(false); setStyle('closed_foam'); blend=1; setMag(10, true); skel.checked=true; advance(11); let n=0; while(n++<1200 && !(sway(simT).com[0]>0.15 && sway(simT).com[0]<0.25)) advance(1/240);   // a moderate forward lean (≈1.2° at x10)
      document.querySelector('.rail').style.display='none'; resize(); })()""")
    pg.evaluate("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
    pg.screenshot(path=str(ROOT / 'assets' / 'stand-og.png'))
    pg.set_viewport_size({'width': 720, 'height': 480})
    pg.evaluate("""(()=>{ document.querySelector('header').style.display='none'; resize(); })()""")
    for i in range(int(FPS * SEC)):
        pg.evaluate(f"advance({SPEED / FPS})")
        pg.evaluate("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
        pg.screenshot(path=str(FR / f'{i:04d}.png'))
    print('errors', errs); b.close()
pal = FR / 'palette.png'
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(FR / '%04d.png'),
                '-vf', 'scale=600:-1:flags=lanczos,palettegen=max_colors=48', str(pal)], check=True)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(FR / '%04d.png'), '-i', str(pal),
                '-lavfi', 'scale=600:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4', str(ROOT / 'assets' / 'stand-cycle.gif')], check=True)
print('done')
