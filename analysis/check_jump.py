"""Numerical checks of jump/index.html in headless Chromium, per jump style (one full jump sampled at 1200 Hz):
  slip    – while a foot carries weight (ground phases outside toe-off / toe-strike) its ball must not move: largest
            displacement of the ball sole point from its pinned spot, and fastest motion of whichever sole point touches the floor
  floor   – deepest any sole point (heel, ball, toe, toe corner) goes below the floor, ground and air
  flight  – a parabola fitted to the page's COM between take-off and touchdown must give g = 9.81 m/s²; both soles clear the floor;
            take-off / touchdown COM speed on the ground side vs the parabola's
  framing – fixed camera, three jumps of each style at 1280x800, 1024x640, 560x700 and 390x844: the whole figure (head and hair,
            hands, shoes) stays on screen, its head clear of the title / nav text, the shoes above the controls; the camera
            only moves while the jumper recovers and stands (never from the countermovement to the landing) and never cuts
Usage: python check_jump.py     (CHROMIUM=/path/to/chrome to use a local build)
"""
import os, json, pathlib, numpy as np
from playwright.sync_api import sync_playwright
url = (pathlib.Path(__file__).resolve().parent.parent / 'jump' / 'index.html').as_uri()
JS = """(st)=>{ setPlay(false); setStyle(st); if(style!==st){ advance(M.TOT-clock+1e-4); }
  advance(2*M.TOT-clock+1e-6);                               // two jumps in, springs warm, clock ≈ 0
  const SOLE=[HEEL,BALL,TOE,[0.262,-0.06]], H=1/1200, n=Math.round(M.TOT/H), rows=[];
  let pin=null;
  for(let k=0;k<n;k++){ const t=k*H; clock=t; travel=base+body(t).com[0];   // the figure is a pure function of the jump clock
    const Q=pose(t), r={t, phase:PH[phaseIdx(t)], com:[travel+Q.com[0],Q.com[1]], w:wRoll(t), feet:[]};
    for(const L of Q.legs){ const pts=SOLE.map(v=>{ const p=shoePt(L.ankle,L.pitch,v); return [travel+p[0],p[1]]; }); r.feet.push(pts); }
    rows.push(r); }
  return {rows, T:M.T, tTO:M.tTO, tTD:M.tTD, TOT:M.TOT, leg_m:M.L, FD:M.FD, h_page:FC.h, vy:FC.vy, vx:FC.vx, g_L:M.g}; }"""


FRAME_JS = """async (st)=>{ await document.fonts.ready; resize(); setPlay(false); setStyle(st); if(style!==st) advance(M.TOT-clock+1e-4); advance(M.TOT-clock+0.006);
  const hd=[...document.querySelectorAll('header h1, header p:not(.nav), header p.nav > *')].map(e=>{ const g=document.createRange(); g.selectNodeContents(e); return g.getBoundingClientRect(); }).filter(r=>r.width>0);   // the text itself
  const rail=document.querySelector('.rail').getBoundingClientRect().top;
  let L=1e9,R=-1e9,T=1e9,B=-1e9, hdr=0, still=0, jmp=0, prev=null;
  for(let k=0;k<3*M.TOT*240;k++){ advance(1/240); updateCamera(); const Q=pose(clock), X=x=>cx+S*x, Y=y=>gy-S*y;
    const pts=[[Q.head[0]-0.16,Q.head[1]-0.16],[Q.head[0]+0.17,Q.head[1]+0.3],[Q.head[0]-0.16,Q.head[1]+0.3],
      ...Q.arms.flatMap(A=>[[A.wr[0]-0.07,A.wr[1]-0.07],[A.wr[0]+0.07,A.wr[1]+0.07],A.el]),
      ...Q.legs.flatMap(Lg=>[[-0.09,-0.075],[0.27,-0.075],[0.27,0.04],[-0.09,0.04]].map(v=>G.shoePt(Lg.ankle,Lg.pitch,v))), Q.T(-0.2,0.4), Q.T(0.18,0.4)];
    const xs=pts.map(p=>X(p[0])), ys=pts.map(p=>Y(p[1]));
    L=Math.min(L,...xs); R=Math.max(R,...xs); T=Math.min(T,...ys); B=Math.max(B,...ys);
    const hb={l:X(Q.head[0]-0.16),r:X(Q.head[0]+0.17),t:Y(Q.head[1]+0.3),b:Y(Q.head[1]-0.16)};    // head incl. hair vs title / nav text
    for(const h of hd) hdr=Math.max(hdr, Math.max(0,Math.min(hb.r,h.right)-Math.max(hb.l,h.left))*Math.max(0,Math.min(hb.b,h.bottom)-Math.max(hb.t,h.top)));
    const c=camX*S; if(prev!==null){ const d=Math.abs(c-prev); jmp=Math.max(jmp,d); if(clock>WEIGH && clock<M.t0[6]) still=Math.max(still,d); } prev=c; }
  return {left:L,right:R,top:T,bottom:B,rail,hdr,still,jump_px:jmp,S}; }"""


def check(r):
    rows, L = r['rows'], r['leg_m']
    t = np.array([q['t'] for q in rows]); com = np.array([q['com'] for q in rows])
    feet = np.array([q['feet'] for q in rows])                      # (n, 2 feet, 4 points, xy)
    air = np.array([q['phase'] == 'flight' for q in rows]); w = np.array([q['w'] for q in rows])
    H = np.median(np.diff(t))
    floor = feet[..., 1].min()
    # pinned ball: weight-bearing ground samples (no toe-off / toe-strike blend)
    pinned = (~air) & (w < 1e-6)
    drift, slip = 0.0, 0.0
    for f in range(2):
        b = feet[:, f, 1]                                            # ball sole point
        for seg in np.split(np.arange(len(t)), np.where(np.diff(pinned.astype(int)) != 0)[0] + 1):
            if not pinned[seg[0]] or len(seg) < 2: continue
            drift = max(drift, np.abs(b[seg, 0] - b[seg[0], 0]).max(), np.abs(b[seg, 1]).max())
        # whichever sole point is lowest and touching the floor (within 0.1 mm), wherever on the ground: ball, heel or toe tip
        lo = feet[:, f, :, 1].argmin(1); y = feet[:, f, :, 1].min(1); x = feet[np.arange(len(t)), f, lo, 0]
        touch = (y < 0.0001 / L) & (~air)
        for i in range(1, len(t)):
            if touch[i] and touch[i - 1] and lo[i] == lo[i - 1]: slip = max(slip, abs(x[i] - x[i - 1]) / H)
    # flight parabola, in metres and seconds
    ta, ya = t[air], com[air, 1] * L
    c = np.polyfit(ta - ta[0], ya, 2); res = ya - np.polyval(c, ta - ta[0])
    clear = feet[air][..., 1].min()
    # actual airborne time: both soles above 1 mm
    up = feet[..., 1].min(axis=(1, 2)) > 0.001 / L
    vy = np.gradient(com[:, 1], t) * L
    i0, i1 = np.argmax(air), len(air) - 1 - np.argmax(air[::-1])
    return dict(g_fit=-2 * c[0], fit_rms_mm=1000 * np.sqrt(np.mean(res ** 2)), flight_ms=1000 * r['T'], airborne_ms=1000 * up.sum() * H,
                h_parabola_cm=100 * r['h_page'] * L, h_gT2_8_cm=100 * 9.81 * r['T'] ** 2 / 8,
                vy_before_takeoff=vy[i0 - 3], vy_after_takeoff=vy[i0 + 3], vy_before_touchdown=vy[i1 - 3], vy_after_touchdown=vy[i1 + 3],
                ball_drift_mm=1000 * drift * L, contact_slip_mm_s=1000 * slip * L, floor_mm=1000 * floor * L, flight_clear_mm=1000 * clear * L,
                jump_distance_m=r['FD'] * L)


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM')); pg = b.new_page(viewport={'width': 1280, 'height': 800})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(url); pg.wait_for_timeout(300)
    ok = True
    for st in ['cmj', 'broad']:
        r = check(pg.evaluate(JS, st))
        print(st, json.dumps({k: round(float(v), 3) for k, v in r.items()}))
        good = (abs(r['g_fit'] - 9.81) < 0.01 and r['ball_drift_mm'] < 0.1 and r['contact_slip_mm_s'] < 1
                and r['floor_mm'] > -0.5 and r['flight_clear_mm'] > -0.5)
        ok &= good
        print('   ', 'PASS' if good else 'FAIL', '(g within 0.01 m/s², pinned ball drift < 0.1 mm, touching contact point < 1 mm/s, nothing below the floor by > 0.5 mm, ground or air)')
    for vw, vh in [(1280, 800), (1024, 640), (560, 700), (390, 844)]:
        pg.set_viewport_size({'width': vw, 'height': vh})
        for st in ['cmj', 'broad']:
            pg.goto(url); pg.wait_for_timeout(200)
            f = pg.evaluate(FRAME_JS, st)
            good = (f['left'] >= 0 and f['right'] <= vw and f['top'] >= 0 and f['bottom'] <= f['rail'] and f['hdr'] <= 0
                    and f['still'] < 1e-6 and f['jump_px'] < 4)
            ok &= good
            print(f"{vw}x{vh} {st:5s} S={f['S']:.0f}px figure x {f['left']:.0f}..{f['right']:.0f}, y {f['top']:.0f}..{f['bottom']:.0f} (controls at {f['rail']:.0f}); "
                  f"head/title overlap {f['hdr']:.0f} px2; camera motion in action {f['still']:.1e} px, largest step {f['jump_px']:.2f} px  {'PASS' if good else 'FAIL'}")
    print('page errors', errs); b.close()
    raise SystemExit(0 if ok and not errs else 1)
