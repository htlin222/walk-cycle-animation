"""Render the README / social images of stairs/index.html: assets/stairs-cycle.gif and assets/stairs-og.png.

Usage: python render_stairs.py      (Playwright Chromium + ffmpeg on PATH; CHROMIUM=/path/to/chrome to use a local build)
Frame-stepped and deterministic: the page's clock is driven from here, not by requestAnimationFrame.
The GIF climbs 6-inch stairs for one stride, then goes down them for one stride (real time).
"""
import pathlib, subprocess, shutil, os
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
FR = ROOT / 'build' / 'stairs_frames'
FPS = 25
shutil.rmtree(FR, ignore_errors=True); FR.mkdir(parents=True)
frame = lambda pg: pg.evaluate("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM')); pg = b.new_page(viewport={'width': 1200, 'height': 630})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto((ROOT / 'stairs' / 'index.html').as_uri()); pg.wait_for_timeout(800)
    pg.evaluate("""(()=>{ setPlay(false); setMode('stair_ascent',true); setCond('stair_ascent_6',true); advance(3);
      while(Math.abs(G.mod1(phase)-0.05)>0.004) advance(1/960); prints.length=0;
      document.querySelector('.rail').style.display='none'; resize(); applyCond(cond); })()""")
    frame(pg); pg.screenshot(path=str(ROOT / 'assets' / 'stairs-og.png'))
    pg.set_viewport_size({'width': 720, 'height': 540})
    pg.evaluate("""(()=>{ document.querySelector('header').style.display='none'; resize(); applyCond(cond); })()""")
    i = 0
    for mode in ('stair_ascent', 'stair_descent'):
        pg.evaluate(f"(()=>{{ setMode('{mode}',true); setCond('{mode}_6',true); advance(2); while(G.mod1(phase)>0.01) advance(1/960); prints.length=0; }})()")
        n = round(FPS * 120 / pg.evaluate('D.cad'))          # one stride in real time
        for _ in range(n):
            pg.evaluate(f"advance({1 / FPS})"); frame(pg)
            pg.screenshot(path=str(FR / f'{i:04d}.png')); i += 1
    print('errors', errs); b.close()
pal = FR / 'palette.png'
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(FR / '%04d.png'),
                '-vf', 'scale=600:-1:flags=lanczos,palettegen=max_colors=48', str(pal)], check=True)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(FR / '%04d.png'), '-i', str(pal),
                '-lavfi', 'scale=600:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4', str(ROOT / 'assets' / 'stairs-cycle.gif')], check=True)
print('done')
