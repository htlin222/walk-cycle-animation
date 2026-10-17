"""Render the README / social images of dance/index.html: assets/dance-cycle.gif and assets/dance-og.png.

Usage: python render_dance.py      (Playwright Chromium + ffmpeg on PATH; CHROMIUM=/path/to/chrome to use a local build)
Frame-stepped and deterministic: the page's clock is driven from here, not by requestAnimationFrame.
The GIF shows each style for whole cycles of its own, about 2.5-3 s each, at full speed (Charleston, salsa, Indian).
"""
import pathlib, subprocess, shutil, os, math
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
FR = ROOT / 'build' / 'dance_frames'
FPS = 25
shutil.rmtree(FR, ignore_errors=True); FR.mkdir(parents=True)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM')); pg = b.new_page(viewport={'width': 1200, 'height': 630})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto((ROOT / 'dance' / 'index.html').as_uri()); pg.wait_for_timeout(800)
    pg.evaluate("""(()=>{ setPlay(false); setStyle('charleston'); blend=1; advance(3); while(Math.abs(G.mod1(phase)-0.62)>0.004) advance(1/960); prints.length=0;   // social image: the kick
      document.querySelector('.rail').style.display='none'; resize(); })()""")
    pg.evaluate("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
    pg.screenshot(path=str(ROOT / 'assets' / 'dance-og.png'))
    pg.set_viewport_size({'width': 720, 'height': 480})
    pg.evaluate("""(()=>{ document.querySelector('header').style.display='none'; resize(); })()""")
    i = 0
    for st in ['charleston', 'salsa', 'indian']:
        cyc = pg.evaluate(f"(()=>{{ setStyle('{st}'); blend=1; phase=0; advance(2*DANCE['{st}'].cycle_s); prints.length=0; return DANCE['{st}'].cycle_s; }})()")
        n = int(round(math.ceil(2.4 / cyc) * cyc * FPS))             # whole cycles, about 2.5-3 s per style
        for _ in range(n):
            pg.evaluate(f"advance({1 / FPS})")
            pg.evaluate("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
            pg.screenshot(path=str(FR / f'{i:04d}.png')); i += 1
    print('errors', errs); b.close()
pal = FR / 'palette.png'
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(FR / '%04d.png'),
                '-vf', 'scale=600:-1:flags=lanczos,palettegen=max_colors=48', str(pal)], check=True)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(FR / '%04d.png'), '-i', str(pal),
                '-lavfi', 'scale=600:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4', str(ROOT / 'assets' / 'dance-cycle.gif')], check=True)
print('done')
