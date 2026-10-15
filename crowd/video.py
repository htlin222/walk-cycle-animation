# Render the crowd walk to MP4: python3 video.py  (Playwright Chromium + ffmpeg)
import base64, subprocess, os, sys, shutil
from multiprocessing import Process
W,H,FPS,SEC,N,SEED,OFF=1920,1080,30,20,140,7,0.1
HERE=os.path.dirname(os.path.abspath(__file__)); FR=os.path.join(HERE,"frames"); OUT=os.path.join(HERE,"walk-crowd-dof-1080p.mp4")
def work(a,b):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br=p.chromium.launch(); pg=br.new_page(viewport={"width":W,"height":H})
        pg.goto("file://"+os.path.join(HERE,"render.html")); pg.evaluate(f"setup({W},{H},{SEED},{OFF},'walk',{N})")
        if a: pg.evaluate(f"for(let i=0;i<{a};i++) advance(1/{FPS})")       # fast-forward the simulation to this chunk
        for i in range(a,b):
            if i>a: pg.evaluate(f"advance(1/{FPS})")
            d=pg.evaluate("drawNow(); document.getElementById('c').toDataURL('image/png')")
            open(f"{FR}/{i:05d}.png","wb").write(base64.b64decode(d.split(",",1)[1]))
        br.close()
def sync_gait():
    # gait.js is the GAIT-BEGIN…GAIT-END block of ../index.html; refresh it so the crowd always uses the page's gait
    src=os.path.join(HERE,"..","index.html")
    if not os.path.exists(src): return
    html=open(src,encoding="utf-8").read(); a=html.index("// ===== GAIT-BEGIN ====="); b=html.index("// ===== GAIT-END =====")
    open(os.path.join(HERE,"gait.js"),"w",encoding="utf-8").write(html[a:b]+"// ===== GAIT-END =====\n")
if __name__=="__main__":
    sync_gait()
    shutil.rmtree(FR,ignore_errors=True); os.makedirs(FR)
    T=FPS*SEC; K=int(sys.argv[1]) if len(sys.argv)>1 else 2
    ps=[Process(target=work,args=(T*k//K,T*(k+1)//K)) for k in range(K)]
    [p.start() for p in ps]; [p.join() for p in ps]
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",f"{FR}/%05d.png","-c:v","libx264","-preset","slow","-crf","17",
                    "-pix_fmt","yuv420p","-movflags","+faststart",OUT],check=True)
    print("done",OUT,os.path.getsize(OUT))
