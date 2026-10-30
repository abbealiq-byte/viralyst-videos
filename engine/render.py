"""Viralyst render engine: storyboard JSON -> voiced 9:16 MP4.
Usage: python engine/render.py storyboards/<name>.json videos/<name>.mp4
"""
import json, math, random, subprocess, sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FR = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BG=(6,12,29); GRID=(17,24,50); CY=(67,213,239); PK=(255,60,126); YL=(254,221,84)
WH=(238,242,250); MU=(136,144,184); PANEL=(14,22,52); DARK=(12,12,16); GREY=(60,68,98)
COLORS={'cyan':CY,'pink':PK,'yellow':YL,'white':WH,'muted':MU,'dark':DARK,'grey':GREY}
def C(c,default=WH): return COLORS.get(c,default) if isinstance(c,str) or c is None else tuple(c)

_fc={}
def F(sz,b=True):
    k=(int(sz),b)
    if k not in _fc: _fc[k]=ImageFont.truetype(FB if b else FR,int(sz))
    return _fc[k]
def ease(x): x=min(max(x,0),1); return 1-(1-x)**3
def back(x):
    x=min(max(x,0),1); c=1.7; return 1+(c+1)*(x-1)**3+c*(x-1)**2
def fade(col,a): return tuple(int(c*a+BG[i]*(1-a)) for i,c in enumerate(col))
def tw(dr,s,f): b=dr.textbbox((0,0),s,font=f); return b[2]-b[0],b[3]-b[1],b[1]
def fit(dr,s,size,maxw=960):
    while size>36 and tw(dr,s,F(size))[0]>maxw: size-=4
    return F(size)
def ctext(dr,s,f,cy,col,cx=W/2):
    w,h,oy=tw(dr,s,f); dr.text((cx-w/2,cy-h/2-oy),s,font=f,fill=col); return h

def make_base():
    g=np.linspace(0,1,H)[:,None,None]
    bg=(np.array([5,10,26])*(1-g)+np.array([8,14,34])*g)*np.ones((1,W,1))
    im=Image.fromarray(bg.astype(np.uint8)); d=ImageDraw.Draw(im)
    for x in range(25,W,120): d.line([(x,12),(x,H)],fill=GRID,width=2)
    for y in range(80,H,120): d.line([(0,y),(W,y)],fill=GRID,width=2)
    return im

def heading(dr,s,lt,cy=330,col=PK):
    if not s: return
    a=ease(lt/0.3); f=fit(dr,s,62,940); ctext(dr,s,f,cy+int(30*(1-a)),fade(col,a))

def lines_block(dr,lines,lt,y0,start=0.0,step=0.25,gap=26):
    y=y0
    for k,ln in enumerate(lines):
        if isinstance(ln,str): ln={'t':ln}
        a=ease((lt-start-ln.get('at',k*step))/0.25)
        size=ln.get('size',96); f=fit(dr,ln['t'],size)
        h=tw(dr,ln['t'],f)[1]
        if a>0:
            pop=ln.get('pop',False)
            if pop and a<1: f=fit(dr,ln['t'],int(size*(1.25-0.25*a)))
            ctext(dr,ln['t'],f,y+h/2+int((0 if pop else 18)*(1-a)),fade(C(ln.get('color'),WH),a))
        y+=h+gap
    return y

def sub(dr,s,lt,cy,at=0.8,col=MU,size=44):
    if not s: return
    a=ease((lt-at)/0.3); ctext(dr,s,fit(dr,s,size,960) if False else F(size,False),cy,fade(col,a))

def crown(dr,cx,cy,s,col=YL):
    pts=[(cx-s,cy+s*0.5),(cx-s,cy-s*0.35),(cx-s*0.5,cy+s*0.05),(cx,cy-s*0.6),(cx+s*0.5,cy+s*0.05),(cx+s,cy-s*0.35),(cx+s,cy+s*0.5)]
    dr.polygon(pts,fill=col)
def cube(dr,cx,cy,s,col):
    top=tuple(min(255,int(c*1.25)) for c in col)
    dr.rounded_rectangle([cx-s/2,cy-s/2,cx+s/2,cy+s/2],radius=s*0.18,fill=col)
    dr.rounded_rectangle([cx-s/2,cy-s/2,cx+s/2,cy-s/2+s*0.28],radius=s*0.18,fill=top)
def bubble(dr,cx,cy,w,h,col):
    dr.rounded_rectangle([cx-w/2,cy-h/2,cx+w/2,cy+h/2],radius=34,fill=col)
    dr.polygon([(cx-w/2+70,cy+h/2-4),(cx-w/2+70,cy+h/2+70),(cx-w/2+150,cy+h/2-4)],fill=col)
def stamp_img(lines,col,w=820):
    h=110+100*len(lines)
    L=Image.new('RGBA',(w,h),(0,0,0,0)); ld=ImageDraw.Draw(L)
    ld.rounded_rectangle([8,8,w-8,h-8],radius=24,outline=col+(255,),width=12)
    for k,t in enumerate(lines):
        f=F(86); 
        while tw(ld,t,f)[0]>w-80: f=F(f.size-4)
        ww,hh,oy=tw(ld,t,f); ld.text((w/2-ww/2,55+k*100-oy),t,font=f,fill=col)
    return L
def paste_rot(img,L,cx,cy,angle,scale,alpha):
    L=L.rotate(angle,expand=True,resample=Image.BICUBIC)
    L=L.resize((max(1,int(L.width*scale)),max(1,int(L.height*scale))))
    L.putalpha(L.split()[3].point(lambda v:int(v*alpha)))
    img.paste(L,(int(cx-L.width/2),int(cy-L.height/2)),L)

random.seed(7)
STARS=[(random.uniform(-1,1),random.uniform(-1,1),random.uniform(0.2,1.0)) for _ in range(180)]

# ---------------- scene types ----------------
def s_text(dr,img,sc,lt,dur):
    heading(dr,sc.get('heading'),lt)
    if sc.get('crown'): crown(dr,W/2,500,95*back(lt/0.3))
    y=lines_block(dr,sc.get('lines',[]),lt,sc.get('y',620),start=0.05,step=sc.get('step',0.25))
    sub(dr,sc.get('sub'),lt,y+50,at=sc.get('sub_at',0.8))

def s_quote(dr,img,sc,lt,dur):
    a=ease(lt/0.4); ctext(dr,"\u201c",F(220),470,fade(PK,a))
    y=lines_block(dr,sc.get('lines',[]),lt,600,start=0.6,step=0.45,gap=24)
    sub(dr,sc.get('by'),lt,y+60,at=0.6+0.45*len(sc.get('lines',[]))+0.2)

def s_counter(dr,img,sc,lt,dur):
    heading(dr,sc.get('heading'),lt)
    if sc.get('top'): ctext(dr,sc['top'],fit(dr,sc['top'],100),480,fade(WH,ease(lt/0.3)))
    v=sc['value']; dec=sc.get('decimals',0); p=ease((lt-0.15)/sc.get('count_time',1.3))
    val=v*p; s=f"{sc.get('prefix','')}{val:,.{dec}f}{sc.get('suffix','')}"
    ctext(dr,s,fit(dr,sc.get('prefix','')+f"{v:,.{dec}f}"+sc.get('suffix',''),200),720,C(sc.get('color'),YL))
    sub(dr,sc.get('label'),lt,880,at=0.4,col=WH,size=52)
    sub(dr,sc.get('sub'),lt,970,at=1.2)
    if sc.get('stopwatch'):
        cx,cy=W/2,1180; r=90; dr.ellipse([cx-r,cy-r,cx+r,cy+r],outline=CY,width=10)
        ang=-math.pi/2+lt*4; dr.line([(cx,cy),(cx+70*math.cos(ang),cy+70*math.sin(ang))],fill=YL,width=8)
        dr.rectangle([cx-18,cy-r-30,cx+18,cy-r-8],fill=CY)

def s_dots(dr,img,sc,lt,dur):
    heading(dr,sc.get('heading'),lt)
    total=sc.get('total',50); cols=sc.get('cols',10); hit=sc.get('highlight',0)
    hc=C(sc.get('highlight_color'),GREY); base=C(sc.get('color'),CY)
    s=62 if cols>=10 else 90; gap=26 if cols>=10 else 40
    rows=math.ceil(total/cols); tot=cols*s+(cols-1)*gap; x0=(W-tot)/2+s/2; y0=sc.get('y',600)
    rnd=random.Random(3); order=list(range(total)); rnd.shuffle(order); hset=order[:hit]
    for i in range(total):
        r,c=divmod(i,cols); cx=x0+c*(s+gap); cy=y0+r*(s+gap)
        p=back((lt*1.6-0.02*i)/0.35)
        if p<=0.01: continue
        col=base
        if i in hset:
            k=hset.index(i); q=ease((lt-sc.get('hit_at',0.4)-0.06*k)/0.25)
            col=tuple(int(base[j]*(1-q)+hc[j]*q) for j in range(3))
        if sc.get('shape','cube')=='cube': cube(dr,cx,cy,s*p,col)
        else: dr.ellipse([cx-s*p/2,cy-s*p/2,cx+s*p/2,cy+s*p/2],fill=col)
    yb=y0+rows*(s+gap)+60
    if sc.get('count'):
        n=int(min(hit,max(0,(lt-sc.get('hit_at',0.4))/0.06+1)))
        ctext(dr,str(n),F(160),yb+60,YL); sub(dr,sc.get('label'),lt,yb+170,at=0.3)
    else:
        sub(dr,sc.get('label'),lt,yb+30,at=0.6,col=WH,size=50)
    if sc.get('moon'):
        a=ease(lt/0.3); mx,my=880,330
        dr.ellipse([mx-55,my-55,mx+55,my+55],fill=fade(YL,a)); dr.ellipse([mx-25,my-75,mx+75,my+25],fill=BG)

def s_list(dr,img,sc,lt,dur):
    heading(dr,sc.get('heading'),lt)
    items=sc['items']; hl=sc.get('highlight',0); hat=sc.get('highlight_at',0.6)
    for k,nm in enumerate(items):
        p=ease((lt-0.08*k)/0.25); y=520+k*125
        if p<=0: continue
        x0=180+int(60*(1-p)); on=(k==hl and lt>hat)
        dr.rounded_rectangle([x0,y-48,x0+720,y+48],radius=20,fill=CY if on else PANEL)
        dr.text((x0+40,y-30),f"{k+1}.",font=F(48),fill=DARK if on else MU)
        dr.text((x0+130,y-30),nm,font=F(52) if k==hl else F(48,False),fill=DARK if on else (WH if k==hl else MU))
        if on and sc.get('crown'): crown(dr,x0+640,y-2,30*back((lt-hat)/0.3))
    yb=520+len(items)*125+80
    lines_block(dr,sc.get('lines',[]),lt,yb,start=sc.get('lines_at',0.8),step=0.15)

def s_ring(dr,img,sc,lt,dur):
    heading(dr,sc.get('heading'),lt)
    cx,cy=W/2,720; R=330; tot=sc.get('total',49); cnt=sc.get('count',46)
    n=int(min(cnt,max(0,(lt-0.1)/0.025)))
    skip=set(range(tot))-set(np.linspace(0,tot-1,cnt).astype(int).tolist())
    for k in range(tot):
        ang=-math.pi/2+2*math.pi*k/tot; x=cx+R*math.cos(ang); y=cy+R*math.sin(ang)
        on=k<n+len([s for s in skip if s<k]) and k not in skip
        if on: dr.line([(x,y),(cx+90*math.cos(ang),cy+90*math.sin(ang))],fill=(40,90,120),width=3)
        dr.ellipse([x-13,y-13,x+13,y+13],fill=CY if on else GREY)
    p=back(lt/0.3); r=85*p; dr.ellipse([cx-r,cy-r,cx+r,cy+r],fill=YL)
    if p>0.8:
        ctext(dr,sc.get('center',''),fit(dr,sc.get('center',''),46,150),cy,DARK)
        if sc.get('crown'): crown(dr,cx,cy-118,30)
    lines_block(dr,sc.get('lines',[]),lt,1110,start=0.8)

def s_stamps(dr,img,sc,lt,dur):
    heading(dr,sc.get('heading'),lt)
    items=sc['items']; n=len(items)
    for k,it in enumerate(items):
        st=it.get('at',0.3+k*0.9); p=ease((lt-st)/0.18)
        if p<=0: continue
        y=sc.get('y',560)+k*(265 if n>1 else 0)
        paste_rot(img,stamp_img(it['t'] if isinstance(it['t'],list) else [it['t']],C(it.get('color'),PK),760),W/2,y,[-5,4,-3,5][k%4],1.5-0.5*p,p)
    sub(dr,sc.get('sub'),lt,sc.get('sub_y',1050),at=sc.get('sub_at',1.0))

def s_bars(dr,img,sc,lt,dur):
    heading(dr,sc.get('heading'),lt)
    items=sc['items']; mx=max(i['value'] for i in items); base_y=1250; maxh=600
    bw=260; gap=120; tot=len(items)*bw+(len(items)-1)*gap; x0=(W-tot)/2
    for k,it in enumerate(items):
        p=ease((lt-0.2-0.5*k)/0.7); h=maxh*it['value']/mx*p; x=x0+k*(bw+gap)
        col=C(it.get('color'),CY)
        if h>2: dr.rounded_rectangle([x,base_y-h,x+bw,base_y],radius=18,fill=col)
        if p>0.05:
            ctext(dr,it.get('show',str(it['value'])),F(64),base_y-h-60,fade(WH,min(1,p*2)),x+bw/2)
            ctext(dr,it['label'],F(44),base_y+60,fade(MU,min(1,p*2)),x+bw/2)
    sub(dr,sc.get('sub'),lt,base_y+150,at=1.4,col=YL,size=56)

def s_calendar(dr,img,sc,lt,dur):
    heading(dr,sc.get('heading'),lt)
    p=back((lt-sc.get('cal_at',0.3))/0.4)
    if p>0.02:
        w,h=330*p,330*p; cx,cy=W/2,720
        dr.rounded_rectangle([cx-w/2,cy-h/2,cx+w/2,cy+h/2],radius=24,fill=(238,242,250))
        dr.rounded_rectangle([cx-w/2,cy-h/2,cx+w/2,cy-h/2+90*p],radius=24,fill=C(sc.get('color'),PK))
        if p>0.9: ctext(dr,sc['month'],F(56),cy-h/2+45,WH); ctext(dr,str(sc['day']),F(150),cy+40,DARK)
    lines_block(dr,sc.get('lines',[]),lt,980,start=sc.get('lines_at',1.0))

def s_buttons(dr,img,sc,lt,dur):
    y=lines_block(dr,sc.get('lines',[]),lt,sc.get('y',470),start=0.0,step=0.15)
    opts=sc['options']; stack=sc.get('stack', any(len(o)>6 for o in opts))
    cols=[CY,PK]
    for k,lab in enumerate(opts):
        p=back((lt-0.4-0.15*k)/0.35)
        if p<=0.02: continue
        if stack: cx,cy,w,h=W/2,y+100+k*180,640*p,140*p
        else: cx,cy,w,h=W/2+(-210 if k==0 else 210),y+110,340*p,170*p
        dr.rounded_rectangle([cx-w/2,cy-h/2,cx+w/2,cy+h/2],radius=30,fill=cols[k%2])
        if p>0.9: ctext(dr,lab,fit(dr,lab,80,w-40),cy,DARK,cx)
    yb=y+(100+len(opts)*180 if stack else 280)
    sub(dr,sc.get('sub','tell us in the comments'),lt,yb+20,at=1.0)
    if sc.get('footer'): sub(dr,sc['footer'],lt,yb+140,at=2.0,col=WH,size=40)

def s_icon(dr,img,sc,lt,dur):
    heading(dr,sc.get('heading'),lt)
    kind=sc.get('icon','laptop'); p=back((lt-0.1)/0.4); cx,cy=W/2,700
    if p>0.02:
        s=p
        if kind=='laptop':
            dr.rounded_rectangle([cx-220*s,cy-150*s,cx+220*s,cy+110*s],radius=16,fill=PANEL,outline=CY,width=8)
            dr.polygon([(cx-280*s,cy+120*s),(cx+280*s,cy+120*s),(cx+320*s,cy+170*s),(cx-320*s,cy+170*s)],fill=CY)
            if int(lt*3)%2==0 and p>0.9: ctext(dr,"!",F(160),cy-20,PK)
        elif kind=='lock':
            dr.rounded_rectangle([cx-170*s,cy-40*s,cx+170*s,cy+200*s],radius=24,fill=YL)
            dr.arc([cx-120*s,cy-230*s,cx+120*s,cy+10*s],180,360,fill=YL,width=int(36*s)+1)
        elif kind=='shield':
            dr.polygon([(cx,cy-220*s),(cx+190*s,cy-150*s),(cx+160*s,cy+90*s),(cx,cy+220*s),(cx-160*s,cy+90*s),(cx-190*s,cy-150*s)],fill=CY)
            if p>0.9: ctext(dr,"\u2713",F(180),cy,DARK)
        elif kind=='trophy':
            dr.polygon([(cx-160*s,cy-200*s),(cx+160*s,cy-200*s),(cx+120*s,cy+20*s),(cx-120*s,cy+20*s)],fill=YL)
            dr.rectangle([cx-30*s,cy+20*s,cx+30*s,cy+120*s],fill=YL); dr.rectangle([cx-120*s,cy+120*s,cx+120*s,cy+170*s],fill=YL)
            if lt>0.5:
                rnd=random.Random(int(lt*10))
                for _ in range(40):
                    x=rnd.uniform(100,W-100); y=rnd.uniform(250,1300); dr.rectangle([x,y,x+14,y+24],fill=rnd.choice([CY,PK,YL,WH]))
        elif kind=='alarm':
            on=int(lt*4)%2==0; dr.ellipse([cx-150*s,cy-150*s,cx+150*s,cy+150*s],fill=PK if on else (120,30,60))
            if p>0.9: ctext(dr,"!",F(200),cy,WH)
    lines_block(dr,sc.get('lines',[]),lt,sc.get('lines_y',1000),start=sc.get('lines_at',0.6),step=0.2)

def s_stars(dr,img,sc,lt,dur):
    cx,cy=W/2,760
    for (x,y,z) in STARS:
        zz=(z-lt*0.25)%1.0+0.05; px=cx+x*380/zz; py=cy+y*380/zz
        if 0<px<W and 200<py<1500:
            r=max(1,int(4*(1.05-zz))); c=int(255*(1.05-zz)); dr.ellipse([px-r,py-r,px+r,py+r],fill=(c,c,min(255,c+20)))
    s_text(dr,img,sc,lt,dur)

def s_curtain(dr,img,sc,lt,dur):
    op=ease((lt-0.2)/1.0)
    sp=Image.new('L',(W,H),0); sd=ImageDraw.Draw(sp)
    sd.polygon([(W/2-60,250),(W/2+60,250),(W/2+330,1250),(W/2-330,1250)],fill=int(55*op))
    img.paste((255,240,200),(0,0),sp); d2=ImageDraw.Draw(img)
    d2.ellipse([W/2-330,1200,W/2+330,1300],fill=fade((120,110,90),op))
    cw=int((W/2)*(1-0.85*op))
    for side in (0,1):
        x0,x1=(0,cw) if side==0 else (W-cw,W)
        d2.rectangle([x0,230,x1,1330],fill=(150,30,60))
        for f in range(x0,x1,45): d2.line([(f,230),(f,1330)],fill=(120,20,50),width=8)
    d2.rectangle([0,200,W,250],fill=(110,20,45))
    lines_block(d2,sc.get('lines',[]),lt,sc.get('y',580),start=0.8)

TYPES={'text':s_text,'quote':s_quote,'counter':s_counter,'dots':s_dots,'list':s_list,'ring':s_ring,
       'stamps':s_stamps,'bars':s_bars,'calendar':s_calendar,'buttons':s_buttons,'icon':s_icon,
       'stars':s_stars,'curtain':s_curtain}

def chrome(dr,t,total,hide_until):
    dr.rectangle([0,0,W,10],fill=(18,29,60)); dr.rectangle([0,0,int(W*t/total),10],fill=CY)
    if t<hide_until: return
    dr.rounded_rectangle([55,97,420,167],radius=16,fill=DARK); ctext(dr,"VIRALYST",F(46),132,WH,237)
    dr.rounded_rectangle([55,176,420,222],radius=10,fill=PK); ctext(dr,"TRENDS, EXPLAINED",F(26),199,WH,237)

def voice(scenes,speed,out_wav,models):
    from kokoro_onnx import Kokoro
    import soundfile as sf
    k=Kokoro(os.path.join(models,'kokoro-v1.0.onnx'),os.path.join(models,'voices-v1.0.bin'))
    sr=24000; parts=[]; t=0.0; times=[]
    for sc in scenes:
        s,sr=k.create(sc['say'],voice=sc.get('voice','af_jessica'),speed=sc.get('speed',speed),lang='en-us')
        idx=np.where(np.abs(s)>0.01)[0]; s=s[max(0,idx[0]-300):idx[-1]+600]
        d=len(s)/sr; gap=sc.get('pause',0.3)
        times.append([t,t+d+gap]); parts+=[s,np.zeros(int(gap*sr),dtype=s.dtype)]; t+=d+gap
    tail=scenes[-1].get('hold',1.2); parts.append(np.zeros(int(tail*sr),dtype=parts[0].dtype)); times[-1][1]=t+tail
    sf.write(out_wav,np.concatenate(parts),sr); return times

def render(sb_path,out_mp4,models=None):
    sb=json.load(open(sb_path)); scenes=sb['scenes']
    models=models or os.environ.get('KOKORO_DIR',os.path.join(HERE,'..','models'))
    wav=out_mp4[:-4]+'.wav'
    times=voice(scenes,sb.get('speed',1.1),wav,models); total=times[-1][1]
    hide=times[0][1] if sb.get('hide_brand_on_hook',True) else 0
    base=make_base()
    proc=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i',wav,
      '-af','loudnorm=I=-14:TP=-1.5','-c:v','libx264','-preset','medium','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',out_mp4],stdin=subprocess.PIPE)
    for n in range(int(total*FPS)):
        t=n/FPS; i=max(j for j in range(len(times)) if times[j][0]<=t+1e-6); lt=t-times[i][0]
        img=base.copy(); dr=ImageDraw.Draw(img); sc=scenes[i]
        TYPES[sc.get('type','text')](dr,img,sc,lt,times[i][1]-times[i][0])
        dr=ImageDraw.Draw(img); chrome(dr,t,total,hide)
        proc.stdin.write(img.tobytes())
    proc.stdin.close(); proc.wait(); os.remove(wav)
    if proc.returncode: raise SystemExit('ffmpeg failed')
    print(f'rendered {out_mp4} ({total:.1f}s)')

if __name__=='__main__':
    render(sys.argv[1],sys.argv[2])
