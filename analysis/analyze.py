"""Sagittal-plane gait curves from CMU motion-capture BVH files.

Usage: python analyze.py 104_02 82_12 82_10 ...   (BVH files in analysis/bvh/)
Projects 3D joints onto the walking plane, detects right heel strikes, keeps straight steady cycles,
time-normalises them to 100 samples and averages per clip. Prints stride, cadence, bounce, arm ROM etc.
"""
import numpy as np, json, sys, pathlib
HERE=pathlib.Path(__file__).parent
BVH_DIR=HERE/'bvh'   # put CMU BVH files here (cgspeed / Shriinivas/cmubvh conversion)
from bvh import parse, fk
from numpy import degrees as deg
def smooth(x,w):
    k=np.ones(w)/w; pad=w//2
    xp=np.pad(x,((pad,pad),)+((0,0),)*(x.ndim-1),mode='edge'); return np.array([np.convolve(xp[:,i] if x.ndim>1 else xp,k,'valid') for i in range(x.shape[1])]).T if x.ndim>1 else np.convolve(xp,k,'valid')
def analyze(path, Tmin=0.7, Tmax=2.0):
    J,D,ft=parse(path); D=D[1:]  # drop T-pose frame
    P=fk(J,D); N=[j['name'] for j in J]; g=lambda n:P[:,N.index(n)]
    fps=1/ft; root=g('Hips')
    vel=np.gradient(smooth(root[:,[0,2]],int(fps*0.8)|1),axis=0)*fps
    spd=np.linalg.norm(vel,axis=1); fwd=vel/np.maximum(spd[:,None],1e-6); lat=np.stack([-fwd[:,1],fwd[:,0]],1)
    def proj(p):   # → (forward, up, lateral) relative to hips
        r=p-root; h=r[:,[0,2]]; return np.stack([(h*fwd).sum(1), r[:,1], (h*lat).sum(1)],1)
    Q={n:proj(g(n)) for n in N}
    legL=np.linalg.norm(g('RightUpLeg')-g('RightLeg'),axis=1).mean()+np.linalg.norm(g('RightLeg')-g('RightFoot'),axis=1).mean()
    ang=lambda a,b: deg(np.arctan2(Q[b][:,0]-Q[a][:,0], Q[a][:,1]-Q[b][:,1]))      # segment a→b below a, fwd +
    angU=lambda a,b: deg(np.arctan2(Q[b][:,0]-Q[a][:,0], Q[b][:,1]-Q[a][:,1]))     # segment a→b above a, fwd lean +
    thR=ang('RightUpLeg','RightLeg'); shR=ang('RightLeg','RightFoot')
    footR=deg(np.arctan2(Q['RightToeBase'][:,1]-Q['RightFoot'][:,1], Q['RightToeBase'][:,0]-Q['RightFoot'][:,0]))
    hl=Q['RightUpLeg']-Q['LeftUpLeg']; sl=Q['RightArm']-Q['LeftArm']
    prot=deg(np.arctan2(hl[:,0],np.abs(hl[:,2]))); pobl=deg(np.arctan2(hl[:,1],np.abs(hl[:,2])))
    throt=deg(np.arctan2(sl[:,0],np.abs(sl[:,2])))
    curves=dict(thigh=thR, shank=shR, foot=footR, prot=prot, pobl=pobl, throt=throt,
        lumbar=angU('Hips','Spine'), thorax=angU('Spine','Neck1'), neck=angU('Neck1','Head'), head=angU('Head','Head_End'),
        uarm=ang('RightArm','RightForeArm'), farm=ang('RightForeArm','RightHand'),
        sh_x=(Q['RightArm'][:,0]-Q['Spine1'][:,0])/legL, sh_y=(Q['RightArm'][:,1]-Q['Spine1'][:,1])/legL,
        hipy=root[:,1]/legL, footyR=g('RightFoot')[:,1]/legL)
    # heel strike: foot most forward (relative to hips), then first frame its world speed collapses
    ax=Q['RightFoot'][:,0]; aw=g('RightFoot')[:,[0,2]]; asp=np.linalg.norm(np.gradient(aw,axis=0),axis=1)*fps
    hs=[]
    for i in range(2,len(ax)-2):
        if ax[i]>=ax[i-1] and ax[i]>ax[i+1] and ax[i]>np.percentile(ax,70):
            for j in range(i,min(len(ax),i+int(0.3*fps))):
                if asp[j]<0.25*np.median(spd): hs.append(j); break
    hs=sorted(set(hs)); cyc=[]
    for a,b in zip(hs[:-1],hs[1:]):
        T=(b-a)/fps
        if Tmin<T<Tmax:
            turn=abs(np.degrees(np.arctan2(fwd[b,1],fwd[b,0])-np.arctan2(fwd[a,1],fwd[a,0])))%360; turn=min(turn,360-turn)
            if turn<20 and spd[a:b].min()>0.5*np.median(spd): cyc.append((a,b))
    if not cyc: return None
    Ts=np.array([(b-a)/fps for a,b in cyc]); med=np.median(Ts); cyc=[c for c,t in zip(cyc,Ts) if abs(t-med)<0.15*med]
    def norm(x):
        out=[]
        for a,b in cyc:
            t=np.linspace(a,b,101); out.append(np.interp(t,np.arange(len(x)),x)[:100])
        return np.array(out)
    M={k:norm(v) for k,v in curves.items()}
    stride=np.mean([np.linalg.norm(root[b,[0,2]]-root[a,[0,2]]) for a,b in cyc])/legL
    T=np.mean([(b-a)/fps for a,b in cyc])
    mean={k:v.mean(0) for k,v in M.items()}; mean['knee']=mean['thigh']-mean['shank']
    stats=dict(cycles=len(cyc), stride=stride, cadence=120/T, speed=stride/T,
       bounce=np.ptp(mean['hipy']), uarm_rom=np.ptp(mean['uarm']), elbow_mean=np.mean(mean['farm']-mean['uarm']), elbow_rom=np.ptp(mean['farm']-mean['uarm']),
       thigh_rom=np.ptp(mean['thigh']), knee_max=mean['knee'].max(), lean=np.mean(mean['thorax']), head=np.mean(mean['head']),
       prot_rom=np.ptp(mean['prot']), throt_rom=np.ptp(mean['throt']), head_bob=np.ptp(mean['hipy']), sh_x_rom=np.ptp(mean['sh_x']))
    return stats, {k:[round(float(x),3) for x in v] for k,v in mean.items()}, legL
if __name__=='__main__':
    out={}
    for name in sys.argv[1:]:
        r=analyze(str(BVH_DIR/f'{name}.bvh'))
        if r is None: print(name,'no clean cycles'); continue
        s,c,L=r; out[name]=c
        print(f"{name:7s} n={s['cycles']:2d} stride={s['stride']:.2f}L cad={s['cadence']:.0f} spd={s['speed']:.2f}L/s bounce={s['bounce']:.3f}L thighROM={s['thigh_rom']:.0f} kneeMax={s['knee_max']:.0f} uarmROM={s['uarm_rom']:.0f} elbow={s['elbow_mean']:.0f}±{s['elbow_rom']/2:.0f} lean={s['lean']:.1f} head={s['head']:.1f} pelvRot={s['prot_rom']:.0f} thxRot={s['throt_rom']:.0f} shX={s['sh_x_rom']:.3f}")
    json.dump(out,open(HERE/'data'/'cmu_sagittal_curves.json','w'))
