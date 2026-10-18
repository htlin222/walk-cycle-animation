"""Proportion audit of the 2D side-view rig against ANSUR II men (README "Proportions").

Usage: python proportions.py [page.html]                    table for one page (default ../index.html)
       python proportions.py --md before.html after.html   Markdown before/after table
       (git show <rev>:index.html > /tmp/before.html gives an older version)

The neutral standing pose (no sway, rest arms) is measured from the page's own pose and drawing code in headless Chromium:
landmarks from the geometry, the hair top and torso depths from the rendered pixels.
Units: the rig's leg length L = hip joint → ankle joint (thigh + shank = 1). In ANSUR II that is trochanterion (≈ the
hip-joint centre, level with the tip of the greater trochanter) − lateral malleolus = 828 mm. Heights are anchored at the
hip joint: drawn height = trochanterion height + (y − hip y) × L.
"""
import sys, json, pathlib
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
A = json.load(open(ROOT / 'analysis' / 'data' / 'ansur2_male_means.json'))
HIP = A['trochanterionheight']
LMM = HIP - A['lateralmalleolusheight']
HEADH = 232          # menton–vertex, US adult men (not measured in ANSUR II)

JS = r"""(Y)=>{
  for(const k in SPR){ const s=SPR[k]; (Array.isArray(s)?s:[s]).forEach(q=>{q.x=null;q.v=null;}); }
  setPlay(false); styleA=styleB='neutral'; blend=1; EX=0.5; simT=0; blinkAt=1e9;
  let t=0; for(let i=1;i<200000;i++){ if(Math.abs(swayAngle(i*0.001))<1e-6){ t=i*0.001; break; } }   // an instant of zero sway
  const Q=compose(kin(0,t,0,0),false), HK=(typeof BODY!=='undefined')?BODY.head:1;
  const hf=(x,y)=>(x*=HK,y*=HK,[Q.head[0]+x*Math.cos(Q.headAng)-y*Math.sin(Q.headAng), Q.head[1]+x*Math.sin(Q.headAng)+y*Math.cos(Q.headAng)]);
  const ell=(cx,cy,rx,ry,rot,keep)=>{ const o=[]; for(let i=0;i<720;i++){ const a=i/720*Math.PI*2, x=rx*Math.cos(a), y=ry*Math.sin(a);
    const p=[cx+x*Math.cos(rot)-y*Math.sin(rot), cy+x*Math.sin(rot)+y*Math.cos(rot)]; if(!keep||keep(p)) o.push(hf(p[0],p[1])); } return o; };
  const skull=ell(0,0.005,0.112,0.135,0), lo=(a,b)=>a[1]<b[1]?a:b;
  const fig=drawFigure.toString(), arm=drawArm.toString(), num=(re,d)=>{ const m=(fig+arm).match(re); return m? +m[1] : d; };
  const out={ hipY:Q.legs[0].hip[1], vertex:skull.reduce((m,p)=>p[1]>m[1]?p:m),
    menton:ell(0.035,-0.06,0.08,0.065,0.2,p=>p[0]>0).concat(ell(0,0.005,0.112,0.135,0,p=>p[0]>0.03)).reduce(lo),
    back:skull.reduce((m,p)=>p[0]<m[0]?p:m), front:skull.reduce((m,p)=>p[0]>m[0]?p:m), ear:hf(-0.035,-0.005), eye:hf(0.075,0.02), neck:Q.neck };
  const A0=Q.arms[0]; Object.assign(out,{sh:A0.sh, el:A0.el, wr:A0.wr, upperArm:Math.hypot(A0.el[0]-A0.sh[0],A0.el[1]-A0.sh[1]), forearm:Math.hypot(A0.wr[0]-A0.el[0],A0.wr[1]-A0.el[1])});
  const hc=num(/const hcx=\[A\.wr\[0\]\+fd\[0\]\*([0-9.]+)/,null);
  out.hand = hc===null ? 0.055+0.06 : hc+num(/ctx\.ellipse\(hcx\[0\],hcx\[1\],([0-9.]+)/,0.07);   // wrist → fingertip along the forearm
  { const nfu=num(/nf=P\(0\.07,([0-9.]+)\)/,0.692), tbx=num(/tb=hp\((-[0-9.]+),-0\.045\)/,-0.075);   // neck column, as drawn
    const nb=Q.T(-0.115,0.752), nf=Q.T(0.07,nfu), tb=hf(tbx,-0.045), tf=hf(0.035,-0.105);
    out.neckMid=Math.hypot((nf[0]+tf[0]-nb[0]-tb[0])/2, (nf[1]+tf[1]-nb[1]-tb[1])/2);
    out.notch=Q.T(0.075, num(/body\.push\(P\(0\.075,([0-9.]+)\)\)/,0.69)); }
  // pixels: whole figure (hair top), torso with the arms moved away (depths)
  const K=600, Wc=1400, Hc=1700, ox=700, oy=1550, cv=document.createElement('canvas'); cv.width=Wc; cv.height=Hc; const c=cv.getContext('2d');
  const draw=q=>{ c.setTransform(1,0,0,1,0,0); c.clearRect(0,0,Wc,Hc); c.setTransform(K,0,0,-K,ox,oy); drawFigure(c,q,PAL); return c.getImageData(0,0,Wc,Hc).data; };
  const d=draw(Q); out.top_hair=null;
  for(let y=0;y<Hc && out.top_hair===null;y++) for(let x=0;x<Wc;x++) if(d[(y*Wc+x)*4+3]>128){ out.top_hair=(oy-y)/K; break; }
  const tor=draw(Object.assign({},Q,{arms:Q.arms.map(a=>({...a, sh:[a.sh[0]+50,a.sh[1]], el:[a.el[0]+50,a.el[1]], wr:[a.wr[0]+50,a.wr[1]]}))}));
  const span=yw=>{ const y=Math.round(oy-yw*K); let l=1e9,r=-1e9; for(let x=0;x<Wc;x++) if(tor[(y*Wc+x)*4+3]>128){ l=Math.min(l,x); r=Math.max(r,x); } return (r-l)/K; };
  out.chest=span(Y.chest); out.waist=span(Y.waist);
  return out; }"""


def measure(page):
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 800, 'height': 600})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(pathlib.Path(page).resolve().as_uri()); pg.wait_for_timeout(300)
        hy = pg.evaluate("kin(0,0,0,0).legs[0].hip[1]")
        y = lambda h: hy + (h - HIP) / LMM
        r = pg.evaluate(JS, {'chest': y(A['chestheight']), 'waist': y(A['waistheightomphalion'])}); b.close()
        if errs: raise SystemExit(f'page errors: {errs}')
    return r


def table(r):
    H = lambda yy: HIP + (yy - r['hipY']) * LMM; Lm = lambda d: d * LMM
    hh = r['vertex'][1] - r['menton'][1]; tr = A['stature'] - A['tragiontopofhead']
    return [
        ('Stature (floor to vertex, no hair)', H(r['vertex'][1]), A['stature'], 'ANSUR II stature'),
        ('Top of hair', H(r['top_hair']), None, 'a few cm over the vertex'),
        ('Head height (menton to vertex)', Lm(hh), HEADH, 'US adult men'),
        ('Head length', Lm(r['front'][0] - r['back'][0]), A['headlength'], 'ANSUR II'),
        ('Neck: C7 to tragion (vertical)', Lm(r['ear'][1] - r['neck'][1]), tr - A['cervicaleheight'], 'ANSUR II tragion − cervicale'),
        ('Neck: chin to sternal notch (vertical)', Lm(r['menton'][1] - r['notch'][1]), A['stature'] - HEADH - A['suprasternaleheight'], 'menton − ANSUR II suprasternale'),
        ('Neck depth (mid-neck)', Lm(r['neckMid']), A['neckcircumference'] / 3.1416, 'ANSUR II neck circumference / π'),
        ('Tragion (ear) height', H(r['ear'][1]), tr, 'ANSUR II stature − tragion-to-top'),
        ('Eye height', H(r['eye'][1]), A['stature'] - 112, 'stature − 112 mm (Pheasant)'),
        ('C7 (cervicale) height', H(r['neck'][1]), A['cervicaleheight'], 'ANSUR II'),
        ('Shoulder joint height', H(r['sh'][1]), A['acromialheight'] - 40, 'ANSUR II acromion − 40 mm'),
        ('Chest depth', Lm(r['chest']), A['chestdepth'], 'ANSUR II'),
        ('Waist depth', Lm(r['waist']), A['waistdepth'], 'ANSUR II'),
        ('Trunk: C7 to hip joint', Lm(r['neck'][1] - r['hipY']), A['cervicaleheight'] - HIP, 'ANSUR II cervicale − trochanterion'),
        ('Upper arm (joint centres)', Lm(r['upperArm']), A['acromionradialelength'] - 30, 'ANSUR II acromion–radiale − 30 mm'),
        ('Forearm (joint centres)', Lm(r['forearm']), A['radialestylionlength'] - 10, 'ANSUR II radiale–stylion − 10 mm'),
        ('Elbow height, arm hanging', H(r['el'][1]), A['acromialheight'] - A['acromionradialelength'], 'ANSUR II acromion − acromion–radiale'),
        ('Wrist height, arm hanging', H(r['wr'][1]), A['wristheight'], 'ANSUR II (crotch height 846)'),
        ('Hand, wrist to fingertip', Lm(r['hand']), A['handlength'], 'ANSUR II hand length (drawn half-curled)'),
        ('Thigh (hip to knee)', Lm(0.47), 0.245 * A['stature'], 'Winter 0.245 H (legs: gait data)'),
        ('Shank (knee to ankle)', Lm(0.53), 0.246 * A['stature'], 'Winter 0.246 H (legs: gait data)'),
        ('Shoe length', Lm(0.347), 295, 'foot ≈270 mm + shoe'),
        ('Stature / head height', H(r['vertex'][1]) / Lm(hh), A['stature'] / HEADH, 'adult men 7.5–8'),
    ]


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--md':
        b, a = table(measure(sys.argv[2])), table(measure(sys.argv[3]))
        print('| Measure (mm) | Reference | Before | After | Reference source |'); print('|---|---:|---:|---:|---|')
        for (n, d0, ref, src), (_, d1, _, _) in zip(b, a):
            q = 2 if n.startswith('Stature /') else 0
            if ref is None: print(f'| {n} | | {d0:.0f} | {d1:.0f} | {src} |'); continue
            print(f'| {n} | {ref:.{q}f} | {d0:.{q}f} ({d0 - ref:+.{q}f}) | {d1:.{q}f} ({d1 - ref:+.{q}f}) | {src} |')
    else:
        for n, d, ref, s in table(measure(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'index.html')):
            print(f'{n:40s} {d:8.1f} ' + (f'{ref:8.1f} {d - ref:+7.1f}' if ref is not None else ' ' * 17) + f'  {s}')
