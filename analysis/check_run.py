"""Numerical checks of run/index.html in headless Chromium, per speed:
  slip   – fastest the contact point (heel, ball or toe, whichever is lowest) moves over the floor in stance
  floor  – deepest any sole point goes below the floor
  flight – lowest sole point while both feet should be in the air
Usage: python check_run.py     (CHROMIUM=/path/to/chrome to use a local build)
"""
import os, json, pathlib
from playwright.sync_api import sync_playwright
url = (pathlib.Path(__file__).resolve().parent.parent / 'run' / 'index.html').as_uri()
JS = """(st)=>{ setStyle(st); blend=1; setPlay(false); advance(2);
  const P=[[-0.085,-0.07],[0.17,-0.07],[0.255,-0.07]], H=1/1200;
  let slip=0, floor=0, flight=9, prev=null; const v=strideB()*cadB()/120;
  for(let k=0;k<2400;k++){ advance(H); const Q=pose(phase), st=stB();
    Q.legs.forEach((L,i)=>{ const g=G.mod1(phase+(i?0.5:0)), pts=P.map(p=>G.shoePt(L.ankle,L.pitch,p)), ys=pts.map(q=>q[1]);
      const m=Math.min(...ys), j=ys.indexOf(m); floor=Math.min(floor,m);
      if(i===0){ if(g>0.02&&g<st-0.02){ const x=travel+pts[j][0]; if(prev&&prev.j===j) slip=Math.max(slip,Math.abs(x-prev.x)/H); prev={j,x}; } else prev=null; } });
    const s=G.mod1(phase*2)/2; if(s>st+0.01&&s<0.49) for(const L of Q.legs) for(const p of P) flight=Math.min(flight,G.shoePt(L.ankle,L.pitch,p)[1]); }
  return {speed_L_per_s:v, slip_L_per_s:slip, slip_pct_of_speed:100*slip/v, floor_L:floor, flight_min_L:flight}; }"""
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM')); pg = b.new_page(viewport={'width': 1280, 'height': 800})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(url); pg.wait_for_timeout(300)
    for st in ['jog', 'run', 'fast']:
        r = pg.evaluate(JS, st)
        print(st, json.dumps({k: round(v, 4) for k, v in r.items()}))
    print('page errors', errs); b.close()
