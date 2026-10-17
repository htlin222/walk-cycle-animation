"""Numerical checks of pitch/index.html in headless Chromium:
  nan     – every 3D point, its projection in all three views and the ball are finite over the whole loop (1 ms steps)
  pivot   – how far the pivot foot's ball of the foot moves while it is held (leg-lift onset → start of the drag)
  plant   – how far the lead heel moves from foot plant to the end of the data (and the lead ball, for information)
  floor   – deepest any sole point goes below the mound surface
  events  – the page's clock reaches each event at the measured time (ms from release), the phase chip and readout agree
  ball    – in the hand until release, then leaves at the measured speed without jumping
Usage: python check_pitch.py     (CHROMIUM=/path/to/chrome to use a local build)
"""
import os, json, pathlib, sys
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
url = (ROOT / 'pitch' / 'index.html').as_uri()
DATA = json.load(open(ROOT / 'analysis' / 'data' / 'normative_pitch_obp.json'))
JS = """()=>{ setPlay(false);
  const mm=HM*1000, iDrag=D.floor.i_drag, tDrag=TS[iDrag], res={nan:0, pivot_mm:0, plant_heel_mm:0, plant_ball_mm:0, floor_mm:0};
  const p0=poseAt(0), pFP=poseAt(tauOf('FP')), views=Object.values(VIEWS);
  for(let tau=0; tau<CYCLE; tau+=0.001){ const Q=poseAt(tau), t=Q.t;
    for(const k in D.pos){ if(!Q[k].every(Number.isFinite)) res.nan++;
      for(const v of views){ camAz=v[0]*D2R; camEl=v[1]*D2R; setCam(); if(!proj(Q[k]).every(Number.isFinite)) res.nan++; } }
    const b=ballAt(tau); if(b && !b.pos.every(Number.isFinite)) res.nan++;
    if(t<=tDrag) res.pivot_mm=Math.max(res.pivot_mm, Math.hypot(Q.rear_ball[0]-p0.rear_ball[0], Q.rear_ball[1]-p0.rear_ball[1], Q.rear_ball[2]-p0.rear_ball[2])*mm);
    if(t>=EV.FP){ res.plant_heel_mm=Math.max(res.plant_heel_mm, Math.hypot(Q.lead_heel[0]-pFP.lead_heel[0], Q.lead_heel[1]-pFP.lead_heel[1], Q.lead_heel[2]-pFP.lead_heel[2])*mm);
      const bm=Math.hypot(Q.lead_ball[0]-pFP.lead_ball[0], Q.lead_ball[1]-pFP.lead_ball[1])*mm;
      res.plant_ball_mm=Math.max(res.plant_ball_mm, bm); if(t<=EV.BR) res.plant_ball_br_mm=Math.max(res.plant_ball_br_mm||0, bm); }
    for(const k of ['rear_heel','rear_ball','lead_heel','lead_ball']) res.floor_mm=Math.min(res.floor_mm,(Q[k][2]-floorZ(Q[k][0]))*mm); }
  camAz=0; camEl=VIEWS.side[1]*D2R; setCam();
  res.drag_starts_ms=tDrag*1000;
  // events: page clock vs data, chip just after each event
  res.events={}; const chip={ON:'lift',PKH:'stride',FC:'plant',FP:'cock',MER:'accel',BR:'release',MIR:'follow',END:'follow'};
  for(const n of D.events.names){ seek(tauOf(n)); res.events[n]={ms:dataT(tau)*1000, chip:phaseAt(tauOf(n)+1e-4), want:chip[n]}; }
  // ball: continuity across release and speed just after it
  const tb=tauOf('BR'), a=ballAt(tb-1e-6), c=ballAt(tb+1e-6), d=ballAt(tb+0.005), e=ballAt(tb+0.006);
  res.ball={held_before:!a.free, free_after:c.free, jump_mm:Math.hypot(...sub3(c.pos,a.pos))*mm,
    speed_ms:Math.hypot(...sub3(e.pos,d.pos))/0.001*HM, gone_after_flight:ballAt(tb+D.ball.flight_s+0.01)===null};
  // the clock: one loop of advance() returns to the same instant
  seek(0.5); accum=0; const t0=tau; advance(CYCLE);
  res.loop_err_ms=Math.abs(((tau+accum-t0+CYCLE/2)%CYCLE+CYCLE)%CYCLE-CYCLE/2)*1000;   // accum: time not stepped yet
  return res; }"""
fails = []
def ok(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond: fails.append(msg)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM')); pg = b.new_page(viewport={'width': 1280, 'height': 800})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(url); pg.wait_for_timeout(300)
    r = pg.evaluate(JS)
    for v in ('side', 'q34', 'catcher'):                     # every view draws a few frames without errors
        pg.click(f'.cam[data-c="{v}"]'); pg.evaluate("setPlay(true)"); pg.wait_for_timeout(400)
    pg.evaluate("setPlay(false); seek(tauOf('MER')+1e-4)"); pg.wait_for_timeout(100)
    shown = pg.evaluate("[document.querySelector('.chip.on').dataset.k, document.getElementById('fr').textContent]")
    b.close()
print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k not in ('events', 'ball')}))
ok(r['nan'] == 0, f"no NaN / infinite points ({r['nan']})")
ok(r['pivot_mm'] < 0.5, f"pivot foot held until the drag ({r['drag_starts_ms']:.0f} ms): moves {r['pivot_mm']:.3f} mm")
ok(r['plant_heel_mm'] < 0.5, f"lead heel planted from foot plant to the end: moves {r['plant_heel_mm']:.3f} mm "
   f"(ball of the foot: {r['plant_ball_br_mm']:.1f} mm by release, {r['plant_ball_mm']:.1f} mm by the end as the foot turns about the heel)")
ok(r['floor_mm'] > -0.5, f"soles stay on or above the mound: deepest {r['floor_mm']:.2f} mm")
for n, e in r['events'].items():
    want = DATA['events']['t_ms'][DATA['events']['names'].index(n)]
    ok(abs(e['ms'] - want) < 0.05 and e['chip'] == e['want'], f"{n}: page {e['ms']:.1f} ms, data {want:.1f} ms, phase '{e['chip']}'")
ok(shown == ['accel', str(round(DATA['events']['t_ms'][4]))], f"UI after seeking to MER: chip '{shown[0]}', readout {shown[1]} ms")
bl = r['ball']
ok(bl['held_before'] and bl['free_after'] and bl['jump_mm'] < 1, f"ball held until release, leaves without a jump ({bl['jump_mm']:.2f} mm)")
ok(abs(bl['speed_ms'] / DATA['ball']['speed_ms'] - 1) < 0.005, f"ball speed after release {bl['speed_ms']:.2f} m/s (measured {DATA['ball']['speed_ms']} m/s)")
ok(bl['gone_after_flight'], 'ball removed after reaching the plate')
ok(r['loop_err_ms'] < 1, f"one loop of the clock returns to the same instant (error {r['loop_err_ms']:.3f} ms)")
ok(not errs, f'page errors {errs}')
sys.exit(1 if fails else 0)
