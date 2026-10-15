import numpy as np, re, sys, json
def parse(path):
    txt=open(path).read(); head,motion=txt.split('MOTION')
    tok=head.split(); i=0; joints=[]; stack=[]
    while i<len(tok):
        t=tok[i]
        if t in('ROOT','JOINT'):
            joints.append({'name':tok[i+1],'parent':stack[-1] if stack else -1,'ch':[],'end':None}); cur=len(joints)-1; i+=2
        elif t=='End':
            joints.append({'name':joints[stack[-1]]['name']+'_End','parent':stack[-1],'ch':[],'end':True}); cur=len(joints)-1; i+=2
        elif t=='{': stack.append(cur); i+=1
        elif t=='}': stack.pop(); i+=1
        elif t=='OFFSET': joints[cur]['off']=np.array(list(map(float,tok[i+1:i+4]))); i+=4
        elif t=='CHANNELS': n=int(tok[i+1]); joints[cur]['ch']=tok[i+2:i+2+n]; i+=2+n
        else: i+=1
    lines=motion.strip().split('\n'); nf=int(lines[0].split()[1]); ft=float(lines[1].split()[-1])
    data=np.array([list(map(float,l.split())) for l in lines[2:2+nf]])
    return joints,data,ft
def R(axis,deg):
    a=np.radians(deg); c,s=np.cos(a),np.sin(a)
    if axis=='X': return np.array([[1,0,0],[0,c,-s],[0,s,c]])
    if axis=='Y': return np.array([[c,0,s],[0,1,0],[-s,0,c]])
    return np.array([[c,-s,0],[s,c,0],[0,0,1]])
def fk(joints,data):
    nf=len(data); nj=len(joints); P=np.zeros((nf,nj,3))
    for f in range(nf):
        row=data[f]; k=0; G=[None]*nj
        for j,J in enumerate(joints):
            rot=np.eye(3); pos=J['off'].copy()
            for c in J['ch']:
                v=row[k]; k+=1
                if c.endswith('position'): pos['XYZ'.index(c[0])]=v if J['parent']==-1 else pos['XYZ'.index(c[0])]
                else: rot=rot@R(c[0],v)
            if J['parent']==-1:
                M=np.eye(4); M[:3,:3]=rot; M[:3,3]=pos
            else:
                Mp=G[J['parent']]; L=np.eye(4); L[:3,:3]=rot; L[:3,3]=J['off']; M=Mp@L
            G[j]=M; P[f,j]=M[:3,3]
    return P
