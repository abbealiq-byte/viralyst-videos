"""Render every storyboards/*.json that has no matching videos/*.mp4 yet."""
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import render
root=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..')
os.makedirs(os.path.join(root,'videos'),exist_ok=True)
done=0
for sb in sorted(glob.glob(os.path.join(root,'storyboards','*.json'))):
    name=os.path.splitext(os.path.basename(sb))[0]
    out=os.path.join(root,'videos',name+'.mp4')
    if os.path.exists(out): continue
    render(sb,out); done+=1
print(f'{done} new video(s)')
