"""Render chunk IDX of N for a 3D project: python blender/run_chunk.py PROJECT IDX N W H SAMPLES"""
import sys, os, json, math, subprocess
proj, idx, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
w, h, smp = sys.argv[4], sys.argv[5], sys.argv[6]
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), proj)
tl = json.load(open(os.path.join(base, 'timeline.json')))
nfr = int(math.ceil(tl['total']*tl['fps'])); per = int(math.ceil(nfr/n))
f0, f1 = idx*per + 1, min(nfr, (idx+1)*per)
if f0 > nfr: print('nothing to do'); sys.exit(0)
subprocess.check_call([sys.executable, os.path.join(base, 'scene.py'), 'frames', w, h, smp, str(f0), str(f1)])
