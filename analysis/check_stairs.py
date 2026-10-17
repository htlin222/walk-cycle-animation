"""Numerical checks of stairs/index.html in headless Chromium, per condition (all step heights and inclines):
  slip     – fastest the sole point in contact (the lowest of 36 points along the sole) moves over the surface in stance
  drift    – farthest that point moves while it stays the contact point (rolling hands over to the next point)
  gap      – largest distance between the lowest sole point and the tread / ramp surface in stance
  floor    – deepest any point of either sole goes into a tread, nosing, riser or the ramp (any phase)
  swing    – smallest clearance of the swinging sole over the stairs / ramp
Every value is in leg lengths (L ≈ 0.84 m); slip also as % of walking speed. Fails (exit 1) if drift > 0.001 L
(≈ 1 mm), gap > 0.002 L or floor < -0.002 L (≈ 2 mm).
Usage: python check_stairs.py     (CHROMIUM=/path/to/chrome to use a local build)
"""
import os, sys, json, pathlib
from playwright.sync_api import sync_playwright
url = (pathlib.Path(__file__).resolve().parent.parent / 'stairs' / 'index.html').as_uri()
JS = """(k)=>{ setPlay(false); setMode(k.replace(/_[0-9.]+$/,''),true); setCond(k,true); advance(2);
  const SOLE=[]; for(let j=0;j<=34;j++) SOLE.push([-0.085+0.34*j/34,-0.07]); SOLE.push([0.262,-0.06]);
  const H=1/240; let slip=0, drift=0, gap=0, floor=0, swing=9, prev=null; const v=G.STRIDE*D.cad/120;
  for(let n=0;n<2400;n++){ advance(H);
    for(const i of [0,1]){ const L=legAt(i,phase), g=G.mod1(phase+(i?0.5:0)), t=travel(), l=lift();
      const P=SOLE.map(s=>{ const p=G.shoePt(L.A,L.pitch,s,L.fy,G.K); return [p[0]+t,p[1]+l]; }), cl=P.map(p=>p[1]-G.terr(p[0]));
      const lo=Math.min(...cl), j=cl.indexOf(lo);
      floor=Math.min(floor,lo);
      if(g>0.02 && g<G.ST-0.02){ gap=Math.max(gap,Math.abs(lo));
        // slip: the sole point in contact, followed while the same point stays in contact (rolling hands over to the next)
        if(i===0){ if(prev&&prev.j===j){ slip=Math.max(slip,Math.abs(P[j][0]-prev.x)/H); drift=Math.max(drift,Math.abs(P[j][0]-prev.x0)); prev.x=P[j][0]; }
          else prev={j,x:P[j][0],x0:P[j][0]}; } }
      else { if(i===0) prev=null; if(g>G.ST+0.02 && g<0.98) swing=Math.min(swing,lo); } } }
  return {speed_L_per_s:v, slip_L_per_s:slip, slip_pct_of_speed:100*slip/v, drift_L:drift, gap_L:gap, floor_L:floor, swing_min_L:swing}; }"""
bad = []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM')); pg = b.new_page(viewport={'width': 1280, 'height': 800})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(url); pg.wait_for_timeout(300)
    for k in pg.evaluate('CONDS'):
        r = pg.evaluate(JS, k)
        print(f'{k:20s}', json.dumps({q: round(v, 4) for q, v in r.items()}))
        if r['drift_L'] > 0.001 or r['gap_L'] > 0.002 or r['floor_L'] < -0.002: bad.append(k)
    print('page errors', errs); b.close()
print('FAIL: ' + ', '.join(bad) if bad or errs else 'all conditions pass')
sys.exit(1 if bad or errs else 0)
