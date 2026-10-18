"""Numerical checks of stand/index.html (and the walk page's standing start) in headless Chromium.

stand/, per condition, 60 s (one full period of the synthesis) sampled at 120 Hz, sway at true scale (x1):
  feet      – largest movement of any sole point (heel, ball, toe; both feet) and depth below the support surface
  COP       – RMS / range / mean velocity of the synthesised COP (AP, ML) vs the data: the spectrum's own RMS
              (must match within 3 %) and the measured median and IQR over subjects
  COM       – AP sway recovered from the drawn body (hip angle about the ankle x pendulum height), RMS within 3 % of
              the spectrum through the pendulum filter, and inside the measured IQR
  pendulum  – COP - COM = -COM''/w0^2 holds on the synthesised signals (rms residual / rms COP)
index.html (walk): standing sway is present and the feet stay put during stand -> lean -> first steps; walking slip
  (single-support pivot speed) is compared with the committed version (git HEAD) to catch regressions.
stand/ layout, closed eyes on foam at x10 (largest sway), at 1280x800, 700x800, 600x700 and 390x844: the figure stays on screen
  and above the controls, its head clear of the title / nav text and of the stabilogram, and the stabilogram clear of
  the text; switching x1 -> x10 eases the body over (largest change of the body angle per 1/240 s step)
Usage: python check_stand.py     (CHROMIUM=/path/to/chrome to use a local build); exits 1 on failure
"""
import os, sys, json, pathlib, subprocess, tempfile, numpy as np
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
D = json.load(open(ROOT / 'analysis' / 'data' / 'normative_stand_bds.json'))

STAND_JS = """(c)=>{ setStyle(c); blend=1; setMag(1, true); setPlay(false);
  const P=[[-0.085,-0.07],[0.17,-0.07],[0.255,-0.07]], out={cop_ap:[],cop_ml:[],com_ap:[],com_ml:[],body_ap:[]};
  let ref=null, move=0, depth=0;
  const th0=Math.atan2(-STAND_X, STAND_H-STAND_AY);                         // hip about the ankle at zero sway
  const t=[], t0=simT;                                                        // 1/120 s = two 240 Hz sim steps
  for(let n=0;n<7200;n++){ advance(1/120); t.push(simT-t0); const Q=pose();
    Q.legs.forEach((L,i)=>P.forEach((p,j)=>{ const q=G.shoePt(L.ankle,L.pitch,p), k=i*3+j;
      ref=ref||[]; if(!ref[k]) ref[k]=q; move=Math.max(move,Math.hypot(q[0]-ref[k][0],q[1]-ref[k][1])); depth=Math.min(depth,q[1]-Q.pad); }));
    const L=Q.legs[0], th=Math.atan2(L.hip[0]-L.ankle[0], L.hip[1]-L.ankle[1])-th0;
    out.body_ap.push(HP*Math.sin(th)*LEG*100);                                // COM from the drawn body, cm
    out.cop_ap.push(Q.sw.cop[0]); out.cop_ml.push(Q.sw.cop[1]); out.com_ap.push(Q.sw.com[0]); out.com_ml.push(Q.sw.com[1]); }
  return {move, depth, w0:W0, t, ...out}; }"""

# walk: sole points relative to the travel point; world x = travel + x. Stand phase first, then 8 s of walking.
WALK_JS = """()=>{ startGait(); setPlay(false); blend=1;
  const P=[[-0.085,-0.07],[0.17,-0.07]], H=1/240, has=typeof swayAngle!=="undefined";
  let ref=null, standMove=0, th=[], err=0, slip=0, prev=null, n=0; const th0=Math.atan2(-STAND_X, STAND_H-STAND_AY);
  while(gaitState!=="walk" && n<4000){ advance(H); n++; const Q=pose(phase);
    if(gaitState==="stand"||gaitState==="apa"){ const pts=Q.legs.flatMap(L=>P.map(p=>G.shoePt(L.ankle,L.pitch,p))).map(q=>[travel+q[0],q[1]]);
      ref=ref||pts; pts.forEach((q,k)=>standMove=Math.max(standMove,Math.hypot(q[0]-ref[k][0],q[1]-ref[k][1]))); }
    if(gaitState==="stand"){   // body angle about the ankle vs the sway model
      const a=Math.atan2(Q.legs[0].hip[0]-Q.legs[0].ankle[0], Q.legs[0].hip[1]-Q.legs[0].ankle[1])-th0;
      th.push(a); if(has) err=Math.max(err,Math.abs(a-swayAngle(simT))); } }
  for(let k=0;k<8*240;k++){ advance(H); const Q=pose(phase), L=Q.legs[0], g=G.mod1(phase);
    if(G.wStance(phase)>=0.999){ const pts=P.map(p=>G.shoePt(L.ankle,L.pitch,p)), j=pts[0][1]<pts[1][1]?0:1, x=travel+pts[j][0];
      if(prev&&prev.j===j) slip=Math.max(slip,Math.abs(x-prev.x)/H); prev={j,x}; } else prev=null; }
  const m=th.reduce((a,b)=>a+b,0)/th.length, rms=Math.sqrt(th.reduce((a,b)=>a+(b-m)**2,0)/th.length);
  return {has_sway:has, stand_samples:th.length, stand_feet_move_L:standMove, stand_angle_rms_deg:rms*180/Math.PI,
          stand_angle_range_deg:(Math.max(...th)-Math.min(...th))*180/Math.PI, stand_model_err_deg:err*180/Math.PI, walk_slip_L_per_s:slip, speed_L_per_s:strideB()*cadB()/120}; }"""


# head box incl. hair (leg lengths about the head centre; the quiff tops out ≈0.21 above it), sole box, fingertips; every overlap in px²
LAYOUT_JS = """async ()=>{ await document.fonts.ready; resize(); setPlay(false); setStyle('closed_foam'); blend=1; setMag(10, true); const ov=(a,b)=>Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left))*Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top));
  const txt=[...document.querySelectorAll('header h1, header p:not(.nav), header p.nav > *')].map(e=>{ const g=document.createRange(); g.selectNodeContents(e); return g.getBoundingClientRect(); }).filter(r=>r.width>0);
  const tb=document.getElementById('trace'), trace=getComputedStyle(tb).display!=='none', tr=tb.getBoundingClientRect();
  let l=1e9,r=-1e9,t=1e9,b=-1e9, ht=0, hs=0;
  for(let k=0;k<60*30;k++){ advance(1/30); const Q=pose(), X=x=>cx+S*x, Y=y=>gy-S*y;
    const hb={left:X(Q.head[0]-0.16),right:X(Q.head[0]+0.17),top:Y(Q.head[1]+0.22),bottom:Y(Q.head[1]-0.16)};
    const pts=[[hb.left,hb.top],[hb.right,hb.bottom],...Q.legs.flatMap(L=>[[-0.09,-0.075],[0.27,-0.075]].map(v=>{ const p=G.shoePt(L.ankle,L.pitch,v); return [X(p[0]),Y(p[1])]; })),
      ...Q.arms.map(A=>[X(A.wr[0]+Math.sin(A.fa)*0.14),Y(A.wr[1]-Math.cos(A.fa)*0.14)])]   // fingertips;
    for(const [x,y] of pts){ l=Math.min(l,x); r=Math.max(r,x); t=Math.min(t,y); b=Math.max(b,y); }
    for(const q of txt) ht=Math.max(ht,ov(hb,q)); if(trace) hs=Math.max(hs,ov(hb,tr)); }
  return {l,r,t,b,rail:document.querySelector('.rail').getBoundingClientRect().top, head_text:ht, head_trace:hs, trace, trace_text:trace? Math.max(0,...txt.map(q=>ov(tr,q))) : 0, S}; }"""
MAG_JS = """()=>{ setPlay(false); setStyle('closed_foam'); blend=1; setMag(1, true); advance(7.3);
  const ang=()=>{ const Q=pose(), L=Q.legs[0]; return Math.atan2(L.hip[0]-L.ankle[0], L.hip[1]-L.ankle[1])*180/Math.PI; };
  setMag(10); let a=ang(), m=0; for(let k=0;k<480;k++){ advance(1/240); const b=ang(); m=Math.max(m,Math.abs(b-a)); a=b; } return m; }"""


def stats(x, t):
    x = np.asarray(x) - np.mean(x)
    return dict(rms=float(np.sqrt(np.mean(x ** 2))), range=float(np.ptp(x)), vel=float(np.sum(np.abs(np.diff(x))) / (t[-1] - t[0])))


fails = []
def check(name, ok, msg):
    print(('PASS ' if ok else 'FAIL ') + name.ljust(36) + msg)
    if not ok: fails.append(name)


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM')); pg = b.new_page(viewport={'width': 1280, 'height': 800})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto((ROOT / 'stand' / 'index.html').as_uri()); pg.wait_for_timeout(300)
    for c, C in D['conditions'].items():
        r = pg.evaluate(STAND_JS, c)
        print(f'--- stand/{c}  ({C["subjects"]} subjects, {C["trials"]} trials)')
        check('feet still', r['move'] < 1e-9, f"max sole movement {r['move']:.1e} L")
        check('feet on the surface', r['depth'] > -1e-6, f"deepest {r['depth']:.1e} L")
        P = C['psd']; f = np.arange(1, len(P['ap']) + 1) * P['df']; w = 2 * np.pi * f; lp = r['w0'] ** 2 / (r['w0'] ** 2 + w ** 2)
        for ax in ('ap', 'ml'):
            s = stats(r['cop_' + ax], r['t']); target = np.sqrt(np.sum(P[ax]) * P['df']); q = C['cop_' + ax]
            check(f'COP {ax} rms = spectrum', abs(s['rms'] / target - 1) < 0.03, f"{s['rms']:.3f} cm vs {target:.3f} cm")
            check(f'COP {ax} rms in measured IQR', q['rms'][0] <= s['rms'] <= q['rms'][2], f"{s['rms']:.3f} in [{q['rms'][0]:.3f}, {q['rms'][2]:.3f}] (median {q['rms'][1]:.3f})")
            print(f"     COP {ax} range {s['range']:.2f} cm (measured median {q['range'][1]:.2f}, IQR {q['range'][0]:.2f}-{q['range'][2]:.2f}); "
                  f"mean velocity {s['vel']:.2f} cm/s (measured {q['vel'][1]:.2f}, IQR {q['vel'][0]:.2f}-{q['vel'][2]:.2f})")
        s = stats(r['body_ap'], r['t']); target = np.sqrt(np.sum(np.array(P['ap']) * lp ** 2) * P['df']); q = C['com_ap']
        check('COM ap from drawn body = model', abs(s['rms'] / target - 1) < 0.03, f"{s['rms']:.3f} cm vs {target:.3f} cm")
        check('COM ap rms in measured IQR', q['rms'][0] <= s['rms'] <= q['rms'][2], f"{s['rms']:.3f} in [{q['rms'][0]:.3f}, {q['rms'][2]:.3f}] (median {q['rms'][1]:.3f})")
        ang = np.degrees(s['rms'] / 100 / D['pendulum']['h_m'])
        print(f"     body sway angle rms {ang:.3f} deg (measured median {C['angle_rms_deg'][1]:.3f}); COM velocity {s['vel']:.2f} cm/s (measured {q['vel'][1]:.2f})")
        cop, com = np.array(r['cop_ap']), np.array(r['com_ap']); acc = np.gradient(np.gradient(com, r['t']), r['t'])
        res = np.sqrt(np.mean((cop - (com - acc / r['w0'] ** 2))[5:-5] ** 2)) / np.sqrt(np.mean(cop ** 2))
        check('COP - COM = -COM\'\'/w0^2', res < 0.02, f"residual {res*100:.2f} % of COP rms")
    for vw, vh in [(1280, 800), (700, 800), (600, 700), (390, 844)]:
        pg.set_viewport_size({'width': vw, 'height': vh}); pg.goto((ROOT / 'stand' / 'index.html').as_uri()); pg.wait_for_timeout(200)
        f = pg.evaluate(LAYOUT_JS)
        check(f'layout {vw}x{vh}', f['l'] >= 0 and f['r'] <= vw and f['t'] >= 0 and f['b'] <= f['rail'] and f['head_text'] == 0 and f['head_trace'] == 0 and f['trace_text'] == 0,
              f"S {f['S']:.0f} px, figure x {f['l']:.0f}..{f['r']:.0f} y {f['t']:.0f}..{f['b']:.0f} (controls {f['rail']:.0f}); stabilogram {'shown' if f['trace'] else 'hidden'}; "
              f"overlap px2 head/text {f['head_text']:.0f}, head/stabilogram {f['head_trace']:.0f}, stabilogram/text {f['trace_text']:.0f}")
    pg.set_viewport_size({'width': 1280, 'height': 800}); pg.goto((ROOT / 'stand' / 'index.html').as_uri()); pg.wait_for_timeout(200)
    m = pg.evaluate(MAG_JS)
    check('x1 -> x10 eases', m < 0.1, f"largest body-angle step {m:.3f} deg per 1/240 s (sway at x10 itself: < 0.03)")
    stand_errs = list(errs)
    # walk page, current file and the committed version
    walk = {}
    head = subprocess.run(['git', '-C', str(ROOT), 'show', 'HEAD:index.html'], capture_output=True, text=True)
    with tempfile.TemporaryDirectory() as td:
        srcs = {'current': ROOT / 'index.html'}
        if head.returncode == 0: (pathlib.Path(td) / 'index.html').write_text(head.stdout); srcs['HEAD'] = pathlib.Path(td) / 'index.html'
        for k, path in srcs.items():
            errs.clear(); pg.goto(path.as_uri()); pg.wait_for_timeout(300)
            walk[k] = pg.evaluate(WALK_JS); walk[k]['errors'] = list(errs)
            print(f'--- walk ({k})', json.dumps({a: (round(v, 5) if isinstance(v, float) else v) for a, v in walk[k].items()}))
    W = walk['current']
    check('walk: standing sway = stand/ model', W['has_sway'] and W['stand_angle_range_deg'] > 0 and W['stand_model_err_deg'] < 1e-6,
          f"body angle = model within {W['stand_model_err_deg']:.0e} deg; {W['stand_angle_range_deg']:.3f} deg range in the {W['stand_samples']/240:.2f} s stand")
    check('walk: feet still while standing', W['stand_feet_move_L'] < 1e-6, f"{W['stand_feet_move_L']:.1e} L")
    if 'HEAD' in walk:
        h = walk['HEAD']
        check('walk: slip not worse than HEAD', W['walk_slip_L_per_s'] <= h['walk_slip_L_per_s'] * 1.01 + 1e-6,
              f"{W['walk_slip_L_per_s']:.5f} vs {h['walk_slip_L_per_s']:.5f} L/s ({100*W['walk_slip_L_per_s']/W['speed_L_per_s']:.3f} % of speed)")
    check('no page errors', not stand_errs and not W['errors'], str(stand_errs + W['errors']))
    b.close()
print('ALL PASS' if not fails else f'{len(fails)} FAILED: {fails}')
sys.exit(1 if fails else 0)
