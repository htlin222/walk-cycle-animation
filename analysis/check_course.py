"""Numerical checks of the 地形 Course mode of stairs/index.html in headless Chromium: the four presets and a few
random seeds, each played for one full lap from 0.5 s in (so the lap seam is crossed) at 240 Hz; a hurdle crossing
that the lap boundary cuts in two is put back together (the lap repeats exactly).
  slip      – fastest the sole point in contact (lowest of 36 points along the sole) moves over the ground in stance
  drift     – farthest that point moves while it stays the contact point
  gap       – largest distance between the lowest sole point and the ground in stance
  floor     – deepest any sole point goes into the ground, a step, a curb or a hurdle (any phase)
  swing     – smallest clearance of a swinging sole over the ground (not counting hurdles)
  hurdle    – for every crossing, the lead and trail sole's smallest clearance over the bar, played back, against the
              modelled clearance (COURSE.obstacle); worst |played − model|
  gaps      – worst difference between a designed level gap and the built one (informative, not a pass criterion)
  seam      – the largest frame-to-frame change of the ankles, pelvis and camera across the lap seam, over the largest
              anywhere else in the lap (≤ 1.5 means the loop has no visible jump)
Then: no page errors, and at 390 px wide the page has no horizontal scroll in course mode.
Values in leg lengths (L ≈ 0.84 m). Fails (exit 1) if drift > 0.001 L, gap > 0.002 L, floor < -0.002 L,
swing < 0, |hurdle| > 0.002 L or seam > 1.5.
Usage: python check_course.py     (CHROMIUM=/path/to/chrome to use a local build)
"""
import os, sys, json, pathlib
from playwright.sync_api import sync_playwright
url = (pathlib.Path(__file__).resolve().parent.parent / 'stairs' / 'index.html').as_uri()
KEYS = ['course:stairs', 'course:ramps', 'course:hurdles', 'course:mixed', 'course:r1', 'course:r7', 'course:r42']
JS = """(key)=>{ setPlay(false); setMode('course',true); setCond(key,true); advance(0.5);
  const C=CRS, T=C.T, SOLE=[]; for(let j=0;j<=34;j++) SOLE.push([-0.085+0.34*j/34,-0.07]); SOLE.push([0.262,-0.06]);
  const H=1/240, n=Math.ceil((C.TL+0.05)/H), stOf=(i,τ)=>cN(T.leg[i].st,τ);
  let slip=0, drift=0, gap=0, floor=0, swing=9; const prev=[null,null], hur={};
  for(let s=0;s<n;s++){ advance(H); const τ=phase, t=travel(), l=lift();
    for(const i of [0,1]){ const L=legAt(i,τ);
      const P=SOLE.map(v=>{ const p=G.shoePt(L.A,L.pitch,v,L.fy,L.k); return [p[0]+t,p[1]+l]; });
      const cg=P.map(p=>p[1]-C.terrNoH(p[0])), ch=P.map(p=>p[1]-C.terr(p[0]));
      const lo=Math.min(...cg), j=cg.indexOf(lo); floor=Math.min(floor,Math.min(...ch));
      const stance=stOf(i,τ-0.02)&&stOf(i,τ)&&stOf(i,τ+0.02);
      if(stance){ gap=Math.max(gap,Math.abs(lo));
        const pv=prev[i]; if(pv&&pv.j===j){ slip=Math.max(slip,Math.abs(P[j][0]-pv.x)/H); drift=Math.max(drift,Math.abs(P[j][0]-pv.x0)); pv.x=P[j][0]; }
        else prev[i]={j,x:P[j][0],x0:P[j][0]}; }
      else { prev[i]=null;
        if(!stOf(i,τ-0.03)&&!stOf(i,τ)&&!stOf(i,τ+0.03)) swing=Math.min(swing,lo); } } }
  // clearance over each hurdle bar, per crossing (own cycle k of the leg): the lap again at 1/1920 s with sole points
  // every 1 mm, so the closest pass is not missed between frames
  const SD=[]; for(let j=0;j<=340;j++) SD.push([-0.085+0.34*j/340,-0.07]); SD.push([0.262,-0.06]);
  for(let τ=0;τ<C.TL;τ+=1/1920){ phase=τ; const t=travel(), l=lift();
    for(const i of [0,1]){ if(stOf(i,τ)) continue; const L=legAt(i,τ);
      for(const h of C.HUR()){ const q=Math.floor((t-h.x0)/C.XL+0.5), xm=(h.x0+h.x1)/2+q*C.XL;
        if(Math.abs(L.A[0]+t-xm)>0.6) continue; let m=9;
        for(const v of SD){ const p=G.shoePt(L.A,L.pitch,v,L.fy,L.k), x=p[0]+t-q*C.XL; if(x>=h.x0&&x<=h.x1) m=Math.min(m,p[1]+l-(h.y+h.h+q*C.HL)); }
        if(m<9){ const k=cN(T.leg[i].k,τ), id=h.id+":"+k; hur[id]=Math.min(hur[id]??9,m); } } } }
  // played clearance vs the model, per crossing
  let herr=0; const hl=[];
  for(const id in hur){ const [hid,k]=id.split(":").map(Number), c=C.cycles[k];
    if(!c.obst){ herr=Math.max(herr,Math.abs(hur[id]-0)); continue; }
    const e=hur[id]-c.target; herr=Math.max(herr,Math.abs(e)); hl.push([C.feats[hid].h, c.obst, +hur[id].toFixed(4), +c.target.toFixed(4)]); }
  // seam: frame-to-frame change of tables across the lap seam vs elsewhere
  const tabs=[[T.X,C.XL],[T.Y,C.HL],[T.Xs,C.XL],[T.Ys,C.HL],[T.leg[0].ax,C.XL],[T.leg[0].ay,C.HL],[T.leg[1].ax,C.XL],[T.leg[1].ay,C.HL],[T.leg[0].pt,0],[T.leg[1].pt,0],[T.tilt,0],[T.lean,0]];
  let seam=0;
  for(const [a,off] of tabs){ const NS=T.NS, v=j=>j<a.length?a[j]:a[j-NS]+off; let mx=0, d2=[];
    for(let j=1;j<NS-1;j++){ mx=Math.max(mx,Math.abs(v(j+1)-2*v(j)+v(j-1))); }
    const sj=Math.max(...[NS-2,NS-1,NS].map(j=>Math.abs(v(j+1)-2*v(j)+v(j-1))));
    seam=Math.max(seam, mx>1e-9? sj/mx : 0); }
  return {lap_m:C.XL*STAIRS["stair_ascent_6"].leg_m, steps:C.N, lap_s:C.TL, slip_L_per_s:slip, drift_L:drift, gap_L:gap, floor_L:floor, swing_min_L:swing,
    hurdle_err_L:herr, crossings:hl, gaps_worst_L:Math.max(0,...C.fit.gapErr.map(Math.abs)), seam_ratio:seam}; }"""
bad = []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM')); pg = b.new_page(viewport={'width': 1280, 'height': 800})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(url); pg.wait_for_timeout(300)
    for k in KEYS:
        r = pg.evaluate(JS, k)
        cr = r.pop('crossings')
        print(f'{k:16s}', json.dumps({q: (round(v, 4) if isinstance(v, float) else v) for q, v in r.items()}))
        for c in cr: print(f'{"":16s}   hurdle {c[0]:.1f} L  {c[1]:5s} clearance {c[2]:.4f} L  (model {c[3]:.4f})')
        if r['drift_L'] > 0.001 or r['gap_L'] > 0.002 or r['floor_L'] < -0.002 or r['swing_min_L'] < 0 or r['hurdle_err_L'] > 0.002 or r['seam_ratio'] > 1.5:
            bad.append(k)
    # phone width: course mode, nothing wider than the screen
    m = b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
    m.on('pageerror', lambda e: errs.append(str(e)))
    m.goto(url); m.wait_for_timeout(300); m.click('button[data-m="course"]'); m.wait_for_timeout(1500)
    sw = m.evaluate('Math.max(document.documentElement.scrollWidth, document.body.scrollWidth)')
    rail = m.evaluate('(()=>{ const r=document.querySelector(".rail").getBoundingClientRect(); return [r.left, r.right]; })()')
    print('390 px: scrollWidth', sw, 'rail', [round(v, 1) for v in rail])
    if sw > 390 or rail[0] < 0 or rail[1] > 390: bad.append('390px')
    print('page errors', errs); b.close()
print('FAIL: ' + ', '.join(bad) if bad or errs else 'all courses pass')
sys.exit(1 if bad or errs else 0)
