"""Numerical checks of dance/index.html in headless Chromium, per style:
  seam   – the loop point is no rougher than the rest of the cycle: the wrap step and the bends beside it, for every stored
           series, may exceed the largest step / bend elsewhere by at most 3e-4 (rounding of the stored 4-decimal data)
  slip   – fastest the contact point (heel, ball or toe, whichever is lowest) moves over the floor while a foot is planted
  floor  – deepest any sole point goes below the floor, all phases, both feet
  nan    – non-finite numbers in the posed figure (springs running) over 4 s of dancing
Usage: python check_dance.py     (CHROMIUM=/path/to/chrome to use a local build); exits 1 if any check fails
"""
import os, sys, json, pathlib
from playwright.sync_api import sync_playwright
url = (pathlib.Path(__file__).resolve().parent.parent / 'dance' / 'index.html').as_uri()
LIMITS = dict(seam_excess=3e-4, slip_L_per_s=1e-3, floor_L=-1e-3)
JS = """(st)=>{ setPlay(false); setStyle(st); blend=1;
  const c=DANCE[st].curves, series=[];
  const walk=(v,name)=>{ if(Array.isArray(v)&&typeof v[0]==="number"&&!name.endsWith("contact")&&!name.endsWith("anchor")) series.push([name,v]);   // contact flags and floor anchors step by design
    else if(Array.isArray(v)&&Array.isArray(v[0])&&typeof v[0][0]==="number"){ series.push([name+".x",v.map(p=>p[0])]); series.push([name+".y",v.map(p=>p[1])]); }
    else if(Array.isArray(v)) v.forEach((x,i)=>walk(x,name+"["+i+"]")); else if(v&&typeof v==="object") for(const k in v) walk(v[k],name+"."+k); };
  walk(c,"");
  // seam: the wrap step (last sample -> first) and the bends next to it, against the largest step / bend anywhere else.
  // Excess beyond that, in leg lengths (or radians); 3e-4 allows for the 4-decimal rounding of the stored data.
  let seam=0, seamName="";
  for(const [name,a] of series){ const n=a.length, d1=i=>a[(i+1)%n]-a[i], d2=i=>a[(i+2)%n]-2*a[(i+1)%n]+a[i];
    let m1=0,m2=0; for(let i=0;i<n-3;i++){ m1=Math.max(m1,Math.abs(d1(i))); m2=Math.max(m2,Math.abs(d2(i))); }
    const r=Math.max(Math.abs(d1(n-1))-m1, Math.abs(d2(n-2))-m2, Math.abs(d2(n-1))-m2);
    if(r>seam){ seam=r; seamName=name; } }
  // slip and floor on the page's own sampler and shoe
  const P=[[-0.085,-0.07],[0.17,-0.07],[0.255,-0.07]], M=20000, dt=DANCE[st].cycle_s/M;
  let slip=0, floor=0, planted=0;
  for(const i of [0,1]){ let prev=null;
    for(let k=0;k<=M;k++){ const f=k/M, L=legAt(i,f), pts=P.map(p=>G.shoePt(L.ankle,L.pitch,p)), ys=pts.map(q=>q[1]);
      const m=Math.min(...ys), j=ys.indexOf(m); floor=Math.min(floor,m);
      const n=c.legs[i].contact.length, s=Math.floor(f*n)%n, inC=c.legs[i].contact[s]&&c.legs[i].contact[(s+n-1)%n]&&c.legs[i].contact[(s+1)%n];
      if(inC){ planted++; if(prev&&prev.j===j) slip=Math.max(slip,Math.hypot(pts[j][0]-prev.x,pts[j][1]-prev.y)/dt); prev={j,x:pts[j][0],y:pts[j][1]}; } else prev=null; } }
  // NaN: dance 4 s with springs and check every number of the posed figure
  let bad=0; const chk=v=>{ if(typeof v==="number"){ if(!Number.isFinite(v)) bad++; } else if(Array.isArray(v)) v.forEach(chk); else if(v&&typeof v==="object") for(const k in v) if(typeof v[k]!=="function") chk(v[k]); };
  for(let k=0;k<240;k++){ advance(1/60); const Q=pose(phase); chk(Q.legs); chk(Q.arms); chk([Q.head,Q.neck,Q.headAng,Q.hair,Q.hem,Q.pelvis,Q.lean]); for(const u of [0,0.3,0.61,0.76]) chk(Q.T(0,u)); }
  return {bpm:DANCE[st].bpm, beats:DANCE[st].beats, series:series.length, seam_excess:seam, seam_worst:seamName, slip_L_per_s:slip, planted_samples:planted, floor_L:floor, nan:bad}; }"""
fail = False
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM')); pg = b.new_page(viewport={'width': 1280, 'height': 800})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(url); pg.wait_for_timeout(300)
    for st in pg.evaluate('Object.keys(DANCE)'):
        r = pg.evaluate(JS, st)
        ok = dict(seam=r["seam_excess"] <= LIMITS["seam_excess"], slip=r['slip_L_per_s'] <= LIMITS['slip_L_per_s'], floor=r['floor_L'] >= LIMITS['floor_L'], nan=r['nan'] == 0)
        fail |= not all(ok.values())
        print(st, json.dumps({k: round(v, 5) if isinstance(v, float) else v for k, v in r.items()}), ' '.join(f"{k}:{'ok' if v else 'FAIL'}" for k, v in ok.items()))
    print('page errors', errs); fail |= bool(errs); b.close()
print('FAIL' if fail else 'PASS'); sys.exit(1 if fail else 0)
