// ===== CROWD-BEGIN =====
// 50 walkers, one gait (neutral: CMU #104_02 upper body + 24-adult clinical norms for the legs).
// Each walker runs the original no-slip simulation on its own clock, shifted by a start offset of ±OFF seconds,
// so walker i at shared time T is exactly the reference walker at time T + τᵢ.

// ---------- performance layer: damped springs (semi-implicit Euler, 240 Hz), one set per walker ----------
class Spring{ constructor(hz,zeta){ this.w=TAU*hz; this.z=zeta; this.x=null; this.v=null; }
  step(t,h){ if(!this.x){ this.x=t.slice(); this.v=t.map(()=>0); return this.x; }
    for(let i=0;i<t.length;i++){ const a=this.w*this.w*(t[i]-this.x[i])-2*this.z*this.w*this.v[i]; this.v[i]+=a*h; this.x[i]+=this.v[i]*h; }
    return this.x; }
  get(t){ return this.x||t; } }
const makeSprings=()=>({ chest:new Spring(4.2,0.42), head:new Spring(2.9,0.38), hair:new Spring(2.1,0.14), hem:new Spring(3.4,0.22),
  ua:[new Spring(3.0,0.5),new Spring(3.0,0.5)], fl:[new Spring(2.3,0.42),new Spring(2.3,0.42)],
  sh:[new Spring(3.6,0.4),new Spring(3.6,0.4)] });
const U=a=>[Math.sin(a),Math.cos(a)], FW=a=>[Math.cos(a),-Math.sin(a)];
const add=(p,v,k=1)=>[p[0]+v[0]*k,p[1]+v[1]*k], sub=(p,q)=>[p[0]-q[0],p[1]-q[1]];
const ss=x=>x<=0?0:x>=1?1:x*x*(3-2*x);

const STAND_X=0.04, STAND_AY=0.07, STAND_H=1.07, PRE_MAX=0.04;
const meanOf=a=>a.reduce((s,v)=>s+v,0)/a.length;
for(const k in STYLES){ const c=STYLES[k].curves;
  for(const n of ["thorax","lumbar","head"]) c[n]=c[n].map((v,i)=>(v+c[n][(i+50)%100])/2);
  c.throt=c.throt.map((v,i)=>(v-c.throt[(i+50)%100])/2); }
for(const k in STYLES){ const c=STYLES[k].curves; STYLES[k].mean={}; for(const n in c) STYLES[k].mean[n]=meanOf(c[n]); }
const meanB=n=>lerpN(STYLES[styleA].mean[n], STYLES[styleB].mean[n], bw());
const amp=(n,f,a,rest)=>{ const m=rest??meanB(n); return m+a*(cur(n,f)-m); };
function relX(i,f,a,p){ const L=legB(f+(i?0.5:0)); return a*Xb(f) + a*L.ankle[0] + (1-a)*STAND_X - p; }
function solePts(i,f,a,p){
  const L=legB(f+(i?0.5:0)), an=[relX(i,f,a,p), a*(hipYb(f)+L.ankle[1])+(1-a)*STAND_AY], pt=a*L.pitch;
  return [G.shoePt(an,pt,[-0.085,-0.07]), G.shoePt(an,pt,[0.17,-0.07])]; }
function kin(f,t,a,p){
  const hy=lerpN(STAND_H, hipYb(f), a), px=a*Xb(f);
  const legs=[0,0.5].map((off,i)=>{ const L=legB(f+off), g=G.mod1(f+off);
    const hip=[px+a*L.hip[0], hy+a*L.hip[1]];
    const ankle=[relX(i,f,a,p), a*(hipYb(f)+L.ankle[1]) + (1-a)*STAND_AY];
    const imp = g<0.2 ? a*(g/0.018)*Math.exp(1-g/0.018) : 0;
    return {hip, ankle, pitch:a*L.pitch, knee:ik(hip, ankle, G.LT, G.LS), imp}; });
  const tiltD=a*(G.C.pelvic_tilt(f)-10.5)*D2R;
  const a2r=(amp("thorax",f,a)+1.5 + 4*p/PRE_MAX)*D2R;
  const a1=a2r*0.6 + a*cur("lumbar",f)*D2R + tiltD;
  const breath=Math.sin(TAU*t/3.8);
  const P0=[px, hy+0.03], P1=add(P0,U(a1),0.28), C=add(add(P1,U(a2r),0.30),U(a2r),0.004*breath);
  const arms=[0,0.5].map(off=>{ const g=f+off, ua=amp("uarm",g,a,-3), fa=amp("farm",g,a,8);
    return { ua:ua*D2R, fl:Math.max(6,fa-ua)*D2R, shx:a*cur("shx",g), shy:a*cur("shy",g) }; });
  return {f, legs, tiltD, lean:a2r, a1, P0, P1, C, thr:a*cur("throt",f)*D2R, head:amp("head",f,a)*D2R, arms, breath};
}
// rigid targets + this walker's spring state; step=true advances the springs by h seconds
// Body proportions (ANSUR II men; README "Proportions"). Leg length L = hip joint → ankle joint (thigh + shank = 1, ≈0.83 m).
// trunk: scales the torso landmarks along the spine (C7 at 0.744 L above the hip joint); neck: C7 → tragion rise (0.13 L = 108 mm);
// head: scales the drawn head (vertex–menton 0.28 L = 232 mm, head length 0.24 L).
const BODY={trunk:0.94, neck:0.13, head:1.05};
function compose(R, step, h, W){
  const SPR=W.spr;
  const mix=(kx,ky)=>(s,t)=>[t[0]+(s[0]-t[0])*kx, t[1]+(s[1]-t[1])*(ky??kx)];
  const cs = step? SPR.chest.step(R.C,h) : SPR.chest.get(R.C);
  let C = mix(0.2+0.2*EX, 1+0.6*EX)(cs,R.C);
  { const dd=sub(C,R.P1), aa=Math.atan2(dd[0],dd[1]), lim=1.8*D2R, ac=Math.max(R.lean-lim,Math.min(R.lean+lim,aa)), l=Math.hypot(dd[0],dd[1]);
    C=add(R.P1,U(ac),l); }
  const d=sub(C,R.P1), a2=Math.atan2(d[0],d[1]);
  const k=Math.hypot(C[0]-R.P0[0],C[1]-R.P0[1])/Math.hypot(R.C[0]-R.P0[0],R.C[1]-R.P0[1]), wsc=1/Math.sqrt(k);
  const tw=Math.sin(R.thr*(1+EX));
  const B0=R.P0, B1=add(R.P0,U(R.a1),0.24), B3=add(C,U(a2),0.08), B2=add(C,U(a2),-0.18);
  const bz=s=>{ const m=1-s; return [m*m*m*B0[0]+3*m*m*s*B1[0]+3*m*s*s*B2[0]+s*s*s*B3[0], m*m*m*B0[1]+3*m*m*s*B1[1]+3*m*s*s*B2[1]+s*s*s*B3[1]]; };
  const bt=s=>{ const m=1-s; const x=3*m*m*(B1[0]-B0[0])+6*m*s*(B2[0]-B1[0])+3*s*s*(B3[0]-B2[0]), y=3*m*m*(B1[1]-B0[1])+6*m*s*(B2[1]-B1[1])+3*s*s*(B3[1]-B2[1]), l=Math.hypot(x,y)||1; return [x/l,y/l]; };
  const T=(r,u)=>{ u*=BODY.trunk; const s=Math.min(1,Math.max(0,u/0.66)), tg=bt(s); let p=bz(s); if(u>0.66) p=add(p,tg,u-0.66);
    const n=[tg[1],-tg[0]], th=(1+(wsc-1)*ss(s*1.6))*(1+(r>0?0.12:0.05)*Math.abs(tw));
    return add(p,n,r*th); };
  let shD=[0,0];
  const arms=R.arms.map((A,i)=>{ const side=i?-1:1;
    const ua0=step? SPR.ua[i].step([A.ua],h)[0] : SPR.ua[i].get([A.ua])[0];
    const fl0=step? SPR.fl[i].step([A.fl],h)[0] : SPR.fl[i].get([A.fl])[0];
    const ua=A.ua+(ua0-A.ua)*0.6*EX, fl=A.fl+(fl0-A.fl)*0.8*EX, fa=ua+fl;
    const base=add(T(-0.04 + side*0.14*tw, 0.62),[0,0.004*R.breath]);
    const pro=A.shx*(1+EX), ele=A.shy*(1+EX);
    const tgt=add(add(base,FW(a2),pro),U(a2),ele);
    const sp=step? SPR.sh[i].step(tgt,h) : SPR.sh[i].get(tgt);
    const sh=[sp[0],sp[1]]; if(!i) shD=sub(sh,base);
    const el=[sh[0]+Math.sin(ua)*0.37, sh[1]-Math.cos(ua)*0.37], wr=[el[0]+Math.sin(fa)*0.31, el[1]-Math.cos(fa)*0.31];
    return {sh,el,wr,ua,fa}; });
  const thA=R.legs.map(L=>Math.atan2(L.knee[0]-L.hip[0], L.hip[1]-L.knee[1]));
  const pushF=0.07*Math.max(0,Math.sin(Math.max(...thA)))*(0.5+EX), pushB=0.045*Math.max(0,-Math.sin(Math.min(...thA)))*(0.5+EX);
  const neck=T(-0.11,0.76);
  const CVA=60*D2R, earR=[neck[0]+BODY.neck/Math.tan(CVA), neck[1]+BODY.neck];
  const headR=[earR[0]+0.035*BODY.head, earR[1]+0.005*BODY.head];
  const hs = step? SPR.head.step(headR,h) : SPR.head.get(headR);
  let head = mix(0.05*EX, 0.15*EX)(hs,headR);
  const nod = Math.max(-0.02,Math.min(0.02,-(head[1]-headR[1])*3));
  const headAng=-R.head + nod*EX;
  { const down=Math.max(0,-headAng), hk=BODY.head, piv=[head[0]-0.01*hk+0.11*Math.sin(down*0.55), head[1]-0.09*hk-0.03*(1-Math.cos(down*0.55))];
    head=[piv[0]+(0.01*Math.cos(headAng)-0.09*Math.sin(headAng))*hk, piv[1]+(0.01*Math.sin(headAng)+0.09*Math.cos(headAng))*hk]; }
  const piv=add(head,[ -0.125*BODY.head*Math.sin(headAng), 0.125*BODY.head*Math.cos(headAng)]);   // quiff root
  const tipR=add(piv, [(0.1*Math.cos(headAng)-0.04*Math.sin(headAng))*BODY.head, (0.1*Math.sin(headAng)+0.04*Math.cos(headAng))*BODY.head]);
  const tp = step? SPR.hair.step(tipR,h) : SPR.hair.get(tipR);
  const v1=sub(tipR,piv), v2=sub(tp,piv);
  const hair=Math.max(-0.3,Math.min(0.3,(Math.atan2(v2[1],v2[0])-Math.atan2(v1[1],v1[0]))*(0.7+0.7*EX)));
  const hemR=T(0,0);
  const hm = step? SPR.hem.step([hemR[1]],h)[0] : SPR.hem.get([hemR[1]])[0];
  const hem=Math.max(-0.03,Math.min(0.03,(hm-hemR[1])*(1+3*EX)));
  let eye=1; const blk=W.t-W.blinkAt; if(blk>0&&blk<0.13) eye=Math.abs(blk-0.065)/0.065;
  const shade=-0.085+0.16*tw;
  return {legs:R.legs, lean:a2, tiltD:R.tiltD, T, arms, neck, head, headAng, hair, hem, eye, shade, tw, pelvis:R.P0, shD, pushF, pushB};
}


// ---------- drawing (world units, y up); C = this walker's look ----------
function smooth(ctx, pts){
  const n=pts.length, m=i=>{const a=pts[i%n],b=pts[(i+1)%n];return[(a[0]+b[0])/2,(a[1]+b[1])/2];};
  ctx.beginPath(); const s=m(n-1); ctx.moveTo(s[0],s[1]);
  for(let i=0;i<n;i++){ const p=pts[i], q=m(i); ctx.quadraticCurveTo(p[0],p[1],q[0],q[1]); }
  ctx.closePath();
}
function seg(ctx, pts, w, col, cap){ ctx.beginPath(); ctx.moveTo(pts[0][0],pts[0][1]);
  for(let i=1;i<pts.length;i++) ctx.lineTo(pts[i][0],pts[i][1]);
  ctx.lineWidth=w; ctx.strokeStyle=col; ctx.lineCap=cap||"round"; ctx.lineJoin="round"; ctx.stroke(); }
function disc(ctx,p,r,col){ ctx.beginPath(); ctx.arc(p[0],p[1],r,0,Math.PI*2); ctx.fillStyle=col; ctx.fill(); }
function taper(ctx,p0,p1,w0,w1,col){ const dx=p1[0]-p0[0], dy=p1[1]-p0[1], l=Math.hypot(dx,dy)||1, nx=-dy/l, ny=dx/l;
  ctx.beginPath(); ctx.moveTo(p0[0]+nx*w0/2,p0[1]+ny*w0/2); ctx.lineTo(p1[0]+nx*w1/2,p1[1]+ny*w1/2); ctx.lineTo(p1[0]-nx*w1/2,p1[1]-ny*w1/2); ctx.lineTo(p0[0]-nx*w0/2,p0[1]-ny*w0/2); ctx.closePath(); ctx.fillStyle=col; ctx.fill(); }
const lerp=(a,b,t)=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t];

function drawLeg(ctx, L, C, far){
  const pant = far?C.pantD:C.pant, skin = far?C.skinD:C.skin, shoe=far?C.shoeD:C.shoe, b=C.b;
  const bare = C.skirt ? (C.tights ? (far?C.tightsD:C.tights) : skin) : skin;
  const cuff = lerp(L.knee, L.ankle, 0.9);
  seg(ctx,[cuff,[L.ankle[0],L.ankle[1]+0.005]],0.058,bare,"round");
  const sq=1-0.16*EX*L.imp, F=v=>G.shoePt(L.ankle,L.pitch,[v[0]*(1+0.04*EX*L.imp), -0.07+(v[1]+0.07)*sq]);
  smooth(ctx,[[-0.08,-0.068],[0.21,-0.07],[0.262,-0.06],[0.25,-0.032],[0.19,-0.018],[0.09,0.008],[0.035,0.04],[-0.055,0.035],[-0.085,0.0]].map(F));
  ctx.fillStyle=shoe; ctx.fill();
  smooth(ctx,[[-0.085,-0.07],[0.24,-0.07],[0.262,-0.06],[0.255,-0.053],[-0.085,-0.054]].map(F));
  ctx.fillStyle=C.sole; ctx.fill();
  if(C.skirt){
    taper(ctx,L.hip,L.knee,0.2*b,0.12,bare); disc(ctx,L.knee,0.062,bare); taper(ctx,L.knee,cuff,0.12,0.095,bare);
  } else if(C.shorts){
    taper(ctx,L.hip,L.knee,0.2*b,0.13,skin); disc(ctx,L.knee,0.066,skin); taper(ctx,L.knee,cuff,0.13,0.1,skin);
    disc(ctx,L.hip,0.12*b,pant); taper(ctx,L.hip,lerp(L.hip,L.knee,0.72),0.25*b,0.2*b,pant);
  } else {
    disc(ctx,L.hip,0.12*b,pant);
    taper(ctx,L.hip,L.knee,0.24*b,0.16*Math.sqrt(b),pant);
    disc(ctx,L.knee,0.08*Math.sqrt(b),pant);
    taper(ctx,L.knee,cuff,0.16*Math.sqrt(b),0.145,pant);
  }
}
function drawArm(ctx, A, P, C, far){
  const skin=far?C.skinD:C.skin, top=C.jacket?(far?C.jkD:C.jk):(far?C.shirtD:C.shirt), limb=(C.ls||C.jacket)?top:skin;
  disc(ctx,A.sh,0.07,limb); taper(ctx,A.sh,A.el,0.14,0.1,limb); disc(ctx,A.el,0.049,limb); taper(ctx,A.el,A.wr,0.1,0.072,limb);
  const fd=[Math.sin(A.fa),-Math.cos(A.fa)];
  { const hcx=[A.wr[0]+fd[0]*0.068,A.wr[1]+fd[1]*0.068];   // relaxed hand along the forearm: wrist → fingertip 0.138 L (ANSUR hand length 0.23 L, fingers half-curled)
    ctx.beginPath(); ctx.ellipse(hcx[0],hcx[1],0.07,0.054,A.fa-Math.PI/2,0,Math.PI*2); ctx.fillStyle=skin; ctx.fill(); }
  if(!far){ const k=[A.wr[0]+fd[0]*0.035-Math.cos(A.fa)*0.025, A.wr[1]+fd[1]*0.035-Math.sin(A.fa)*0.025];
    seg(ctx,[k,[k[0]+fd[0]*0.04,k[1]+fd[1]*0.04]],0.008,C.skinDD,"round"); }
  const ax=[Math.sin(A.ua),-Math.cos(A.ua)], n=[Math.cos(A.ua),Math.sin(A.ua)];
  const S=A.sh, p=(u,v)=>[S[0]+ax[0]*u+n[0]*v, S[1]+ax[1]*u+n[1]*v];
  smooth(ctx,[p(-0.07,0.035),p(-0.02,0.09),p(0.18,0.085),p(0.185,-0.078),p(0.02,-0.095),p(-0.08,-0.055)]);
  ctx.fillStyle=top; ctx.fill();
  if(!far && !C.ls && !C.jacket){ seg(ctx,[p(0.178,0.065),p(0.182,-0.06)],0.012,C.shirtDD,"round"); }
  if(C.bangle && !far){ const q=lerp(A.el,A.wr,0.85); seg(ctx,[[q[0]-0.03*Math.cos(A.fa),q[1]-0.03*Math.sin(A.fa)],[q[0]+0.03*Math.cos(A.fa),q[1]+0.03*Math.sin(A.fa)]],0.014,C.gold,"round"); }
}
// shirt prints, drawn in body coordinates so they follow the spine
function drawPattern(ctx,P,C){
  const c=C.patc, k=C.pat;
  if(k===1){ for(let u=-0.1;u<0.75;u+=0.075) seg(ctx,[P(-0.3,u),P(0.3,u)],0.026,c,"butt"); }
  else if(k===2){ for(let u=-0.05;u<0.72;u+=0.07) for(let r=-0.2;r<0.2;r+=0.07) disc(ctx,P(r+((u*100|0)%2?0.035:0),u),0.014,c); }
  else if(k===3){ for(let u=0.02;u<0.72;u+=0.12) for(let r=-0.18;r<0.2;r+=0.11){ const a=P(r,u), b=P(r+0.04,u+0.035), d=P(r+0.07,u-0.01);
      ctx.beginPath(); ctx.moveTo(a[0],a[1]); ctx.quadraticCurveTo(b[0],b[1],d[0],d[1]); ctx.lineWidth=0.012; ctx.strokeStyle=c; ctx.lineCap="round"; ctx.stroke(); } }
  else if(k===4){ for(let u=0.0;u<0.72;u+=0.13) for(let r=-0.2;r<0.2;r+=0.12){ const q=P(r+((u*10|0)%2?0.05:0),u);
      ctx.beginPath(); ctx.ellipse(q[0],q[1],0.035,0.014,(r*31+u*17)%3,0,Math.PI*2); ctx.fillStyle=c; ctx.fill(); } }
  else if(k===5){ for(let u=-0.1;u<0.75;u+=0.15) seg(ctx,[P(-0.3,u),P(0.3,u)],0.06,c,"butt"); }
}
function drawFigure(ctx, Q, C){
  const b=C.b;
  drawArm(ctx, Q.arms[1], Q, C, true);
  drawLeg(ctx, Q.legs[1], C, true);
  drawLeg(ctx, Q.legs[0], C, false);
  const T=Q.T;
  if(!C.skirt){ const pts=[[-0.162,0.05],[0.148,0.05],[0.15,-0.03],[0.115,-0.095],[0.03,-0.125],[-0.08,-0.115],[-0.158,-0.07],[-0.172,0.0]].map(v=>T(v[0]*b,v[1]));
    smooth(ctx,pts); ctx.fillStyle=C.pant; ctx.fill(); }
  else { // skirt / dress: waist to just above the knees, flaring with the stride
    const k0=Q.legs[0].knee, k1=Q.legs[1].knee, hy=(k0[1]+k1[1])/2+0.07*C.skLen;
    const fx=Math.max(k0[0],k1[0])+0.1, bx=Math.min(k0[0],k1[0])-0.09;
    smooth(ctx,[T(-0.17*b,0.04),T(-0.2*b,-0.15),[bx,hy],[(bx+fx)/2,hy-0.02],[fx,hy],T(0.2*b,-0.15),T(0.16*b,0.04)]); ctx.fillStyle=C.skc; ctx.fill(); }
  const hm=Q.hem, sd=Q.shD, w=u=>ss((u-0.4)/0.2)*(1-ss((u-0.64)/0.08));
  const P=(r,u)=>{ const p=T(r,u), k=w(u), kb=k*Math.max(0,Math.min(1,-r/0.12))*0.6; return [p[0]+sd[0]*kb, p[1]+sd[1]*kb*0.5]; };
  const bu=u=>u<0.62?b:lerpN(b,1,Math.min(1,(u-0.62)/0.1));
  const front=[[0.0,0.145+Q.pushF],[0.1,0.142+Q.pushF*0.35],[0.25,0.14],[0.42,0.146],[0.53,0.144],[0.6,0.124],[0.645,0.095]];
  const back=[[0.756,-0.118],[0.72,-0.142],[0.66,-0.158],[0.56,-0.165],[0.42,-0.16],[0.3,-0.148],[0.18,-0.142],[0.06,-0.155],[0.0,-0.165-Q.pushB]];
  const body=[];
  body.push(P((-0.165-0.4*Math.abs(hm)-Q.pushB)*b, hm*1.5));
  for(const [u,rr] of front) body.push(P(rr*bu(u), u + (u<0.05? hm*0.7+Q.pushF*0.5 : 0)));
  body.push(P(0.075,0.66)); body.push(P(-0.02,0.718));
  for(const [u,rr] of back) body.push(P(rr*bu(u), u + (u<0.05? hm*1.2 : 0)));
  smooth(ctx,body); ctx.fillStyle=C.shirt; ctx.fill();
  ctx.save(); smooth(ctx,body); ctx.clip();
  if(C.pat) drawPattern(ctx,P,C);
  const shadeP=[P(-0.45,-0.12),P(Q.shade+0.01,-0.12),P(Q.shade-0.01,0.25),P(Q.shade-0.03,0.5),P(Q.shade-0.05,0.85),P(-0.45,0.85)];
  const fillPoly=(pts,col,a=1)=>{ ctx.beginPath(); pts.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1])); ctx.closePath(); ctx.globalAlpha=a; ctx.fillStyle=col; ctx.fill(); ctx.globalAlpha=1; };
  fillPoly(shadeP, "#1f2233", C.pat?0.13:0); if(!C.pat) fillPoly(shadeP, C.shirtD);
  if(C.jacket){   // open jacket: covers the back and sides, a strip of the shirt shows down the front
    fillPoly([P(-0.5,-0.2),P(0.075*b,-0.2),P(0.06*b,0.3),P(0.045,0.52),P(0.085,0.7),P(-0.5,0.95)], C.jk);
    fillPoly(shadeP, C.jkD);
    seg(ctx,[P(0.075*b,-0.15),P(0.06*b,0.3),P(0.045,0.52),P(0.085,0.68)],0.01,C.jkD,"round"); }
  if(Q.pushF>0.01){ const a=P(0.12,0.02), bb=P(0.06,0.14); seg(ctx,[a,bb],0.012,C.jacket?C.jkD:C.shirtD,"round"); }
  ctx.restore();
  if(C.bag){ smooth(ctx,[P(-0.13*b,0.24),P(-0.31*b,0.25),P(-0.33*b,0.42),P(-0.31*b,0.6),P(-0.13*b,0.63)]); ctx.fillStyle=C.bagc; ctx.fill();
    seg(ctx,[P(-0.3*b,0.4),P(-0.15*b,0.4)],0.012,C.bagD,"round");
    seg(ctx,[P(-0.1,0.7),P(0.05,0.62),P(0.1*b,0.38)],0.022,C.bagD,"round"); }
  { const ha=Q.headAng, Hd=Q.head, hk=BODY.head, hp=(x,y)=>[Hd[0]+(x*Math.cos(ha)-y*Math.sin(ha))*hk, Hd[1]+(x*Math.sin(ha)+y*Math.cos(ha))*hk];
    smooth(ctx,[P(-0.125,0.76),P(-0.07,0.775),P(0.02,0.712),P(-0.03,0.705)]); ctx.fillStyle=C.shirtDD; ctx.fill();
    const nb=P(-0.115,0.752), nf=P(0.07,0.662), tb=hp(-0.062,-0.045), tf=hp(0.035,-0.105);
    smooth(ctx,[nb,lerp(nb,tb,0.5),tb,hp(-0.005,-0.1),tf,lerp(tf,nf,0.5),nf,P(-0.01,0.7)]); ctx.fillStyle=C.skin; ctx.fill();
    smooth(ctx,[hp(-0.015,-0.098),hp(0.035,-0.108),hp(0.02,-0.122),hp(-0.01,-0.118)]); ctx.fillStyle=C.skinD; ctx.fill();
    const c0=P(-0.125,0.76), cm=P(-0.02,0.722), c1=P(0.078,0.66);
    ctx.beginPath(); ctx.moveTo(c0[0],c0[1]); ctx.quadraticCurveTo(cm[0],cm[1],c1[0],c1[1]);
    ctx.lineWidth=0.026; ctx.strokeStyle=C.jacket?C.jk:C.shirt; ctx.lineCap="round"; ctx.stroke();
    ctx.lineWidth=0.007; ctx.strokeStyle=C.jacket?C.jkD:C.shirtDD; ctx.stroke();
    if(C.necklace){ ctx.beginPath(); const a=P(-0.06,0.72), m=P(0.03,0.615), e=P(0.085,0.66); ctx.moveTo(a[0],a[1]); ctx.quadraticCurveTo(m[0],m[1],e[0],e[1]);
      ctx.lineWidth=0.008; ctx.strokeStyle=C.gold; ctx.stroke(); }
  }
  drawHead(ctx,Q,C);
  drawArm(ctx, Q.arms[0], Q, C, false);
}
// hair styles:
// 0 quiff · 1 crop · 2 long · 3 ponytail · 4 bun · 5 cap · 6 shaved · 7 afro · 8 locs · 9 bob · 10 headscarf · 11 curly long · 12 spikes · 13 braid
const CAP=[[0.11,0.06],[0.09,0.135],[0,0.168],[-0.1,0.135],[-0.128,0.05],[-0.105,0],[-0.07,0.02],[-0.05,0.055],[0.04,0.07]];   // ≈2 cm of volume over the crown
function drawHead(ctx,Q,C){
  ctx.save(); ctx.translate(Q.head[0],Q.head[1]); ctx.rotate(Q.headAng); ctx.scale(BODY.head,BODY.head);
  const hs=C.hs, sw=Q.hair;
  ctx.fillStyle=C.hair;
  // hair that sits behind the head
  if(hs===7){ for(const [x,y,r] of [[-0.03,0.07,0.17],[-0.12,0.0,0.1],[0.05,0.13,0.11],[-0.14,0.11,0.1]]) disc(ctx,[x,y],r,C.hair); }
  if(hs===8){ ctx.save(); ctx.translate(-0.05,0.1); ctx.rotate(sw*0.5);
    for(let i=0;i<6;i++) seg(ctx,[[-0.01-i*0.02,0.02],[-0.04-i*0.026,-0.16],[-0.03-i*0.028,-0.3+0.01*(i%2)]],0.026,i%2?C.hair:C.hairD,"round");
    ctx.restore(); }
  if(hs===11){ ctx.save(); ctx.translate(-0.05,0.1); ctx.rotate(sw*0.4);
    for(const [x,y,r] of [[0.0,0.06,0.07],[-0.07,0.04,0.07],[-0.1,-0.04,0.065],[-0.09,-0.12,0.065],[-0.04,-0.17,0.06],[-0.12,-0.2,0.055],[-0.06,-0.26,0.05],[-0.13,-0.12,0.06]]) disc(ctx,[x,y],r,C.hair);
    ctx.restore(); }
  // face
  ctx.beginPath(); ctx.ellipse(0,0.005,0.112,0.135,0,0,Math.PI*2); ctx.fillStyle=C.skin; ctx.fill();
  ctx.beginPath(); ctx.ellipse(0.035,-0.06,0.08,0.065,0.2,0,Math.PI*2); ctx.fill();
  ctx.beginPath(); ctx.ellipse(-0.035,-0.005,0.025,0.033,0,0,Math.PI*2); ctx.fillStyle=C.skinD; ctx.fill();
  ctx.beginPath(); ctx.moveTo(0.108,0.015); ctx.quadraticCurveTo(0.14,-0.02,0.112,-0.03); ctx.fillStyle=C.skin; ctx.fill();
  if(C.beard){ smooth(ctx,[[-0.045,0.0],[-0.03,-0.08],[0.03,-0.13],[0.1,-0.13],[0.125,-0.095],[0.1,-0.082],[0.06,-0.088],[0.035,-0.05],[-0.015,0.0]]); ctx.fillStyle=C.hair; ctx.fill();
    seg(ctx,[[0.072,-0.055],[0.112,-0.048]],0.012,C.hair,"round"); }
  if(hs===10){ // headscarf: wraps head and neck, leaves the face open
    smooth(ctx,[[0.095,0.075],[0.07,0.16],[-0.03,0.185],[-0.14,0.13],[-0.165,0.0],[-0.155,-0.15],[-0.05,-0.23],[0.07,-0.2],[0.085,-0.13],[0.045,-0.08],[0.035,0.0],[0.055,0.06]]);
    ctx.fillStyle=C.scarf; ctx.fill();
    seg(ctx,[[0.06,0.07],[0.04,0.0],[0.05,-0.08],[0.085,-0.13]],0.012,C.scarfD,"round"); }
  const ry=0.011*Math.max(0.12,Q.eye);
  ctx.beginPath(); ctx.ellipse(0.075,0.02,0.011,ry,0,0,Math.PI*2); ctx.fillStyle=C.face; ctx.fill();
  seg(ctx,[[0.05,0.052],[0.098,0.046]],0.009,C.brow,"round");
  if(!C.beard){ const c0=[0.066,-0.067], c1=[0.1,-0.066];
    ctx.beginPath(); ctx.moveTo(c0[0],c0[1]); ctx.quadraticCurveTo(0.083,-0.069,c1[0],c1[1]); ctx.lineWidth=0.007; ctx.strokeStyle=C.lip; ctx.lineCap="round"; ctx.stroke(); }
  if(C.glasses){ ctx.beginPath(); ctx.ellipse(0.082,0.018,0.026,0.022,0,0,Math.PI*2); ctx.lineWidth=0.007; ctx.strokeStyle=C.frame; ctx.stroke();
    seg(ctx,[[0.056,0.025],[-0.03,0.035]],0.006,C.frame,"round"); }
  if(C.earring && hs!==10 && hs!==9){ if(C.earring===1) disc(ctx,[-0.03,-0.045],0.012,C.gold);
    else { ctx.beginPath(); ctx.arc(-0.03,-0.07,0.028,0,Math.PI*2); ctx.lineWidth=0.007; ctx.strokeStyle=C.gold; ctx.stroke(); } }
  ctx.fillStyle=C.hair;
  if(hs===10){ ctx.restore(); return; }
  if(hs===6){ smooth(ctx,[[-0.05,0.04],[-0.11,0.07],[-0.125,0.0],[-0.09,-0.025],[-0.07,0.02]]); ctx.globalAlpha=0.55; ctx.fill(); ctx.globalAlpha=1; }
  else if(hs===5){ smooth(ctx,[[0.11,0.055],[0.09,0.135],[0.0,0.165],[-0.1,0.135],[-0.13,0.05],[-0.06,0.045],[0.04,0.06]]); ctx.fillStyle=C.hat; ctx.fill();
    smooth(ctx,[[0.06,0.07],[0.215,0.058],[0.21,0.04],[0.06,0.045]]); ctx.fill();
    ctx.fillStyle=C.hair; smooth(ctx,[[-0.128,0.05],[-0.105,0.0],[-0.08,0.02],[-0.07,0.05]]); ctx.fill(); }
  else if(hs===7){ smooth(ctx,[[0.1,0.06],[0.1,0.16],[-0.02,0.22],[-0.12,0.15],[-0.13,0.04],[-0.07,0.0],[-0.05,0.05],[0.04,0.06]]); ctx.fill(); }
  else if(hs===9){ smooth(ctx,[[0.115,0.065],[0.095,0.145],[0.0,0.175],[-0.115,0.14],[-0.155,0.02],[-0.15,-0.11],[-0.07,-0.115],[-0.055,-0.02],[-0.02,0.045],[0.06,0.08]]); ctx.fill(); }
  else if(hs===12){ smooth(ctx,CAP.map(([x,y])=>[x*0.97,y*0.97])); ctx.fill();
    ctx.beginPath(); ctx.moveTo(-0.1,0.12); for(let i=0;i<5;i++){ const x=-0.09+i*0.045; ctx.lineTo(x+0.03+sw*0.05,0.215-0.012*i); ctx.lineTo(x+0.045,0.15); } ctx.lineTo(0.1,0.1); ctx.closePath(); ctx.fill(); }
  else {
    if(hs===2){ ctx.save(); ctx.translate(-0.06,0.1); ctx.rotate(sw*0.5);
      smooth(ctx,[[0.0,0.05],[-0.09,0.02],[-0.105,-0.12],[-0.09,-0.25],[-0.03,-0.26],[-0.01,-0.12],[0.03,-0.05]]); ctx.fill(); ctx.restore(); }
    if(hs===13){ ctx.save(); ctx.translate(-0.11,0.05); ctx.rotate(sw*1.2);
      for(let i=0;i<6;i++) { ctx.beginPath(); ctx.ellipse(-0.012*i,-0.045*i,0.028-0.002*i,0.03,0.3,0,Math.PI*2); ctx.fillStyle=i%2?C.hair:C.hairD; ctx.fill(); }
      ctx.restore(); ctx.fillStyle=C.hair; }
    smooth(ctx, (hs===1||hs===8||hs===11||hs===13)? CAP.map(([x,y])=>[x*0.98,y*0.98]) : CAP); ctx.fill();
    if(hs===11){ for(const [x,y] of [[0.08,0.11],[0.02,0.16],[-0.06,0.155],[-0.12,0.1]]) disc(ctx,[x,y],0.04,C.hair); }
    if(hs===0){ ctx.save(); ctx.translate(0.0,0.125); ctx.rotate(sw);   // short quiff, ≈4 cm over the skull
      smooth(ctx,[[-0.07,0],[-0.02,0.04],[0.05,0.065],[0.115,0.055],[0.13,0.02],[0.11,-0.025],[0.06,-0.04]]); ctx.fill(); ctx.restore(); }
    if(hs===2){ smooth(ctx,[[0.115,0.06],[0.1,0.14],[0.0,0.172],[-0.1,0.14],[-0.13,0.05],[0.0,0.09]]); ctx.fill(); }
    if(hs===3){ ctx.save(); ctx.translate(-0.115,0.09); ctx.rotate(sw*1.6);
      smooth(ctx,[[0.0,0.03],[-0.08,0.01],[-0.11,-0.08],[-0.08,-0.17],[-0.05,-0.08],[0.0,-0.02]]); ctx.fill(); ctx.restore();
      disc(ctx,[-0.112,0.09],0.022,C.hairD); }
    if(hs===4){ disc(ctx,[-0.085,0.145],0.052,C.hair); }
  }
  if(C.phones){ ctx.beginPath(); ctx.ellipse(-0.03,0.0,0.14,0.168,0,0.12*Math.PI,0.97*Math.PI); ctx.lineWidth=0.013; ctx.strokeStyle=C.phc; ctx.stroke();
    ctx.beginPath(); ctx.ellipse(-0.035,-0.005,0.033,0.045,0,0,Math.PI*2); ctx.fillStyle=C.phc; ctx.fill(); }
  ctx.restore();
}

// ---------- looks ----------
function mulberry32(a){ return function(){ a|=0; a=a+0x6D2B79F5|0; let t=Math.imul(a^a>>>15,1|a); t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296; }; }
const hex2=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16));
const shade=(h,k)=>{ const c=hex2(h); return "#"+c.map(v=>Math.round(Math.max(0,Math.min(255,v*(1+k)))).toString(16).padStart(2,"0")).join(""); };
const lum=h=>{ const c=hex2(h); return (0.3*c[0]+0.59*c[1]+0.11*c[2])/255; };
const SKIN=["#f8d5bc","#f1c09e","#e8ab83","#d9956b","#c47f52","#a9673f","#8d5233","#6f3f26","#55301d","#f2675a","#e9b8a0","#b8865f"];
const CLOTH=["#fdb14d","#5b8def","#e8565a","#3fb68b","#f4f1ea","#2f3542","#9b6bd6","#f07fa6","#7cc6d6","#c9a46b","#ffd23f","#6c8b5e",
  "#ff7a3d","#4a5fc1","#e9c46a","#c8553d","#1d3557","#94d2bd","#ee9b00","#f2c4ce","#7f8c3a","#bb3e03","#005f73","#ffffff","#b5838d","#264653"];
const PANT=["#3f4f93","#2b2f3a","#6b5b4b","#8a8f99","#283c63","#7a3e3e","#c2b28f","#1f4d3a","#4d4f5c","#e9e4d8","#a24936","#5c6b8a"];
const SHOE=["#3d4c90","#22263a","#efefef","#8a3b2e","#5a5f6b","#c0392b","#d9c7a3","#f2c14e","#2a9d8f"];
const HAIR_N=["#252a3d","#3b2a20","#5e3a22","#8b5a2b","#c99a5b","#e8d5a8","#d8d2c8","#151515","#a8432b","#2c1d14"];
const HAIR_DYE=["#f29bc1","#6c8cf2","#4fc1b8","#b79cf0","#ff8a3d","#e94f6b","#9fd36a"];
const pick=(r,a)=>a[Math.floor(r()*a.length)];
function makeLook(r){
  const skin=pick(r,SKIN), shirt=pick(r,CLOTH), pant=pick(r,PANT), shoe=pick(r,SHOE);
  const hair = r()<0.16 ? pick(r,HAIR_DYE) : pick(r,HAIR_N);
  const hs=[0,0,1,1,1,2,2,3,3,4,5,6,7,7,8,8,9,9,10,11,11,12,13,13][Math.floor(r()*24)];
  const longish=[2,3,4,8,9,11,13].includes(hs);
  const skirt = r()<(longish?0.32:0.08);
  const jacket = r()<0.28, jk=pick(r,CLOTH);
  const pat = r()<0.38 ? 1+Math.floor(r()*5) : 0;
  let patc=pick(r,CLOTH); if(patc===shirt) patc=lum(shirt)>0.5?"#2f3542":"#f4f1ea";
  const skc = r()<0.4 ? shirt : pick(r,CLOTH);
  const bagc=pick(r,["#2f3542","#3f4f93","#7a3e3e","#264653","#c9a46b","#e8565a","#1f4d3a","#ee9b00"]), scarf=pick(r,CLOTH), tights=r()<0.4?pick(r,["#22263a","#3b2f2f","#5c4b6b"]):null;
  const dark=lum(skin)<0.45;
  return { skin, skinD:shade(skin,-0.1), skinDD:shade(skin,-0.2), shirt, shirtD:shade(shirt,-0.13), shirtDD:shade(shirt,-0.22),
    pant, pantD:shade(pant,-0.25), shoe, shoeD:shade(shoe,-0.25), sole:"#22263a", hair, hairD:shade(hair,-0.3),
    brow: lum(hair)>0.55 ? shade(hair,-0.45) : hair, hat:pick(r,CLOTH), face:"#2a2233", lip: dark?"#2a1a1a":"#2a2233", frame:pick(r,["#2a2233","#8a3b2e","#c9a46b","#2a2233"]),
    jk, jkD:shade(jk,-0.15), patc, skc, bagc, bagD:shade(bagc,-0.3), scarf, scarfD:shade(scarf,-0.18), tights, tightsD:tights?shade(tights,-0.2):null,
    gold:"#e3b54a", phc:pick(r,["#22263a","#f4f1ea","#e8565a"]),
    hs, b:0.85+r()*0.45, h:0.9+r()*0.2, skirt, skLen:r(), shorts:!skirt&&r()<0.16, ls:r()<0.25, jacket, pat,
    glasses:r()<0.2, beard:hs!==10&&!longish&&r()<0.3, earring: r()<0.28 ? 1+Math.floor(r()*2) : 0,
    necklace:r()<0.18, bag:r()<0.14, phones:hs!==10&&hs!==7&&r()<0.1, bangle:r()<0.15 };
}
const COLOR_KEYS=["skin","skinD","skinDD","shirt","shirtD","shirtDD","pant","pantD","shoe","shoeD","sole","hair","hairD","brow","hat","face","lip","frame",
  "jk","jkD","patc","skc","bagc","bagD","scarf","scarfD","tights","tightsD","gold","phc"];
function fogLook(L, f, bg){ const o={...L}, B=hex2(bg);
  for(const k of COLOR_KEYS){ if(!L[k]) continue; const c=hex2(L[k]); o[k]=`rgb(${c.map((v,i)=>Math.round(v+(B[i]-v)*f)).join(",")})`; } return o; }

// ---------- crowd ----------
const HSTEP=1/240;
const BG="#f3eee6", FOG_MAX=0.3;
// high camera looking down: the horizon sits above the frame, so each row further back stacks higher up the picture
const CAM={F:7, ZMAX:8.6, horizon:-0.6, near:1.48, S:0.35, focus:2.6, blur:0.045};
EX=0.5;
// height bins: one cadence for everyone (keeps the ±τ timing exact); stride in leg lengths scales as 1/h so the crowd shares one walking speed
const HB=[0.9,0.95,1.0,1.05,1.1];
for(const h of HB){ const n=STYLES.neutral, key="h"+h;
  STYLES[key]={curves:n.curves, mean:n.mean, stride:n.stride/h, cad:n.cad, bounce:n.bounce/h, clip:n.clip}; GS[key]=fitStyle(STYLES[key]); }
const useStyle=w=>{ styleA=styleB=w.sk; };
function newWalker(look, tau){ const hb=HB.reduce((a,b)=>Math.abs(b-look.h)<Math.abs(a-look.h)?b:a);
  return {look, tau, h:hb, sk:"h"+hb, spr:makeSprings(), t:0, blinkAt:3, phase:0, travel:0, A:1, pre:0, gs:"walk", gt:0, u:0, z:0}; }
function stepWalker(w,h){
  useStyle(w);
  w.t+=h; w.gt+=h;
  const f0=w.phase, a0=w.A, p0=w.pre;
  if(w.gs==="stand"){ if(w.gt>0.8){ w.gs="apa"; w.gt=0; } }
  else if(w.gs==="apa"){ w.pre=PRE_MAX*ssG(w.gt/0.45); if(w.gt>=0.45){ w.gs="go"; w.gt=0; } }
  else if(w.gs==="go"){ w.A=ssG(w.gt/1.15); w.pre=PRE_MAX*(1-ssG(w.gt/0.5)); if(w.gt>=1.15){ w.gs="walk"; w.A=1; w.pre=0; } }
  let d=0;
  if(w.gs==="go"||w.gs==="walk"){
    const cad=1+0.022*(0.6*Math.sin(TAU*w.t/7.3)+0.4*Math.sin(TAU*w.t/3.1+1));
    d=h*cad*cadB()/120; w.phase=G.mod1(w.phase+d);
  }
  let num=0, ws=0;
  for(const i of [0,1]){ const wt=G.wStance(f0+(i?0.5:0)); if(wt<=0) continue;
    const o=solePts(i,f0,a0,p0), n=solePts(i,f0+d,w.A,w.pre);
    const sH=1/(1+Math.exp((o[0][1]-o[1][1])/0.008));
    num+=wt*(sH*(n[0][0]-o[0][0])+(1-sH)*(n[1][0]-o[1][0])); ws+=wt; }
  w.travel += ws>0 ? -num/ws : d*strideB();
  compose(kin(w.phase,w.t,w.A,w.pre), true, h, w);
  if(w.t>w.blinkAt+0.2) w.blinkAt=w.t+2+((w.t*7919+w.tau*104729)%1+1)%1*3.5;
}
const kz=z=>CAM.F/(CAM.F+z);
function makeCrowd(seed, off, mode, aspect, N){
  const r=mulberry32(seed), out=[];
  // visible half-width at depth z (leg lengths), plus a margin so the edges stay filled
  const hw=z=>(aspect/2)/(CAM.S*kz(z))+0.9;
  let sx=0.62, sz=0.36, tries=0; const pos=[];
  while(pos.length<N){ const z=r()*CAM.ZMAX, x=(r()*2-1)*hw(z);
    if(pos.every(p=>((p.x-x)/sx)**2+((p.z-z)/sz)**2>1)) pos.push({x,z});
    if(++tries>6000){ tries=0; sx*=0.94; sz*=0.94; } }
  for(const p of pos){ const look=makeLook(r), w=newWalker(look,(r()*2-1)*off); w.u=p.x/hw(p.z); w.z=p.z;
    w.C=fogLook(look,FOG_MAX*p.z/CAM.ZMAX,BG); w.blinkAt=1+r()*4; out.push(w); }
  out.sort((a,b)=>b.z-a.z);
  for(const w of out){
    if(mode==="stand"){ w.gs="stand"; w.A=0; w.pre=0; w.phase=0.57; w.gt=w.tau; w.t=w.tau; }
    else { let T=1.5+w.tau; while(T>=HSTEP){ stepWalker(w,HSTEP); T-=HSTEP; } }
  }
  return out;
}

// ---------- renderer ----------
function makeRenderer(cv){
  const ctx=cv.getContext("2d");
  const ly=document.createElement("canvas"), lx=ly.getContext("2d");      // full-res layer (light blur)
  const hl=document.createElement("canvas"), hx=hl.getContext("2d");      // half-res layer (heavy blur)
  const hb=document.createElement("canvas"), hbx=hb.getContext("2d");
  let W=0,H=0,dpr=1,S=100,hy=0,gy=0,LV=[0];
  function resize(w,h,d){ W=w; H=h; dpr=d; LV=[0,1.5,3,5,8,12,16].map(v=>v*H/1080); for(const c of [cv,ly]){ c.width=Math.round(W*dpr); c.height=Math.round(H*dpr); }
    for(const c of [hl,hb]){ c.width=Math.round(W*dpr/2); c.height=Math.round(H*dpr/2); }
    S=H*CAM.S; hy=H*CAM.horizon; gy=H*CAM.near; }
  const gyz=z=>hy+(gy-hy)*kz(z);
  const hwz=z=>(W/H/2)/(CAM.S*kz(z))+0.9;
  // circle of confusion ∝ |k(z) − k(focus)| (softer behind the focus plane), snapped to a few levels so layers stay few
  const coc=z=>{ const d=kz(z)-kz(CAM.focus), raw=CAM.blur*H*Math.abs(d)*(d>0?1:0.45);
    let best=LV[0]; for(const v of LV) if(Math.abs(v-raw)<Math.abs(best-raw)) best=v; return best*dpr; };
  function shoeLow(L){ let m=9; for(const v of [[-0.085,-0.07],[0.17,-0.07],[0.255,-0.07]]) m=Math.min(m,G.shoePt(L.ankle,L.pitch,v)[1]); return Math.max(0,m); }
  function drawOne(c,o,k){ const d=dpr*k;
    c.save(); c.setTransform(d,0,0,d,0,0);
    for(const L of o.Q.legs){ const h=shoeLow(L), rr=G.rot([0.09,0],L.pitch);
      const x=o.X+o.s*(L.ankle[0]+rr[0]), a=0.3*Math.exp(-h/0.05), wd=o.s*(0.22+h*1.4), hh=o.s*(0.03+h*0.25);
      const g=c.createRadialGradient(0,0,0,0,0,1); g.addColorStop(0,`rgba(30,24,30,${a.toFixed(3)})`); g.addColorStop(1,"rgba(30,24,30,0)");
      c.save(); c.translate(x,o.Y+o.s*0.006); c.scale(wd,hh); c.fillStyle=g; c.beginPath(); c.arc(0,0,1,0,Math.PI*2); c.fill(); c.restore(); }
    c.restore();
    c.setTransform(d*o.s,0,0,-d*o.s,d*o.X,d*o.Y); drawFigure(c,o.Q,o.w.C);
  }
  function draw(crowd, camX){
    ctx.setTransform(1,0,0,1,0,0); ctx.fillStyle=BG; ctx.fillRect(0,0,cv.width,cv.height);
    const items=[];
    for(const w of crowd){ const k=kz(w.z), s=S*k*w.h, X=W/2+S*k*(w.u*hwz(w.z)+w.travel*w.h-camX);
      if(X<-s*1.5||X>W+s*1.5) continue;
      useStyle(w); items.push({w, s, X, Y:gyz(w.z), b:coc(w.z), Q:compose(kin(w.phase,w.t,w.A,w.pre),false,0,w)}); }
    // depth of field: consecutive walkers (far → near) sharing a blur level go into one layer, blurred once
    let i=0;
    while(i<items.length){ const b=items[i].b; let j=i; while(j<items.length && items[j].b===b) j++;
      if(b<0.75){ for(let q=i;q<j;q++) drawOne(ctx,items[q],1); }
      else if(b<4.5*dpr){ lx.setTransform(1,0,0,1,0,0); lx.clearRect(0,0,ly.width,ly.height);
        for(let q=i;q<j;q++) drawOne(lx,items[q],1);
        ctx.setTransform(1,0,0,1,0,0); ctx.filter=`blur(${b}px)`; ctx.drawImage(ly,0,0); ctx.filter="none"; }
      else { hx.setTransform(1,0,0,1,0,0); hx.clearRect(0,0,hl.width,hl.height);
        for(let q=i;q<j;q++) drawOne(hx,items[q],0.5);
        hbx.setTransform(1,0,0,1,0,0); hbx.clearRect(0,0,hb.width,hb.height); hbx.filter=`blur(${b/2}px)`; hbx.drawImage(hl,0,0); hbx.filter="none";
        ctx.setTransform(1,0,0,1,0,0); ctx.imageSmoothingQuality="high"; ctx.drawImage(hb,0,0,cv.width,cv.height); }
      i=j; }
    ctx.setTransform(1,0,0,1,0,0);
  }
  return {resize, draw};
}
const camOf=crowd=>crowd.reduce((s,w)=>s+w.travel*w.h,0)/crowd.length;
// ===== CROWD-END =====
