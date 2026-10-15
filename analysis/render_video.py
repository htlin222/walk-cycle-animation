from playwright.sync_api import sync_playwright
import json
import os, pathlib, subprocess
ROOT=pathlib.Path(__file__).resolve().parent.parent
OUT=ROOT/'build'/'frames'; OUT.mkdir(parents=True, exist_ok=True)
page_url=(ROOT/'index.html').as_uri()
SEG=[  # style, camera, speed, exaggeration, start-from-standing, skeleton, label
 ("neutral","fixed",1.0,0.5,False,False,"平常 · 固定鏡頭 · 1×"),
 ("happy",  "fixed",1.0,0.5,False,False,"開心 · 固定鏡頭 · 1×"),
 ("sad",    "fixed",1.0,0.5,False,False,"低落 · 固定鏡頭 · 1×"),
 ("neutral","follow",1.0,0.0,False,False,"平常 · 跟隨 · 誇張 0"),
 ("happy",  "follow",0.5,1.0,False,False,"開心 · 跟隨 · 0.5× 慢動作 · 誇張 1"),
 ("sad",    "follow",1.0,1.0,False,False,"低落 · 跟隨 · 誇張 1"),
 ("neutral","fixed",1.0,0.5,True, False,"平常 · 從原地起步"),
 ("happy",  "fixed",1.0,0.5,True, True, "開心 · 起步 · 顯示骨架"),
 ("sad",    "follow",0.5,0.5,False,True, "低落 · 跟隨 · 0.5× · 顯示骨架"),
]
FPS=30; N=3*FPS
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1440,'height':1080},device_scale_factor=1)
    errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto(page_url); pg.wait_for_timeout(800)
    pg.evaluate("""(()=>{ window.realAdvance=advance; advance=()=>{};      // take over the clock
      const d=document.createElement('div'); d.id='seglbl';
      d.style.cssText='position:absolute;top:22px;right:max(24px,env(safe-area-inset-right,0px));font:600 15px/1.3 Archivo,"PingFang TC",system-ui,sans-serif;color:#1f2233;background:#f3f3f6;padding:8px 12px;border-radius:10px';
      document.getElementById('wrap').appendChild(d); })()""")
    k=0
    for i,(st,cam,spdv,ex,start,skel,lbl) in enumerate(SEG):
        pg.evaluate(f"""(()=>{{
          setStyle('{st}'); blend=1; startGait();
          camMode='{cam}'; camBtns.forEach(x=>x.setAttribute('aria-pressed', x.dataset.c==='{cam}'));
          speed={spdv}; spd.value={spdv}; spdo.textContent=({spdv}).toFixed(2)+'×';
          EX={ex}; sty.value={ex}; skel.checked={str(skel).lower()};
          setPlay(true);
          {'' if start else 'realAdvance(4); prints.length=0;'}
          camX=null;
          document.getElementById('seglbl').textContent='{i+1} / 9 · {lbl}';
        }})()""")
        for f in range(N):
            pg.evaluate(f"realAdvance({1/FPS}*speed)")
            if not __import__('os').path.exists(str(OUT/f'{k:04d}.png')): pg.evaluate("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
            fn=str(OUT/f'{k:04d}.png')
            if not __import__('os').path.exists(fn): pg.screenshot(path=fn)
            k+=1
    print('frames',k,'errors',errs); b.close()
# encode: 30 fps H.264, 1440x1080
subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','30','-i',str(OUT/'%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p',
                '-crf','20','-movflags','+faststart',str(ROOT/'assets'/'walk-cycle-9-clips.mp4')],check=True)
