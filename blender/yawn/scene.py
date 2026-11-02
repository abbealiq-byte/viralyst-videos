"""Viralyst 3D: Why do we yawn when someone else yawns?
python blender/yawn/scene.py OUT_DIR W H SAMPLES F0 F1
"""
import bpy, math, sys, os, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
OUT = argv[0]; RW, RH, SAMPLES = int(argv[1]), int(argv[2]), int(argv[3])
TL = json.load(open(os.path.join(HERE, 'timeline.json'))); FPS = TL['fps']
NFR = int(math.ceil(TL['total']*FPS))
F0 = int(argv[4]) if len(argv) > 4 else 1
F1 = min(int(argv[5]) if len(argv) > 5 else NFR, NFR)
SEG = {s['name']: s for s in TL['segments']}

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def hexc(h):
    h = h.lstrip('#'); f = lambda c: c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4
    return tuple(f(int(h[i:i+2], 16)/255) for i in (0, 2, 4)) + (1.0,)
_mats = {}
def mat(color, rough=0.32, emit=0.0, coat=0.0):
    k = (color, rough, emit, coat)
    if k in _mats: return _mats[k]
    m = bpy.data.materials.new(f'm{len(_mats)}'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = hexc(color); b.inputs['Roughness'].default_value = rough
    if coat: b.inputs['Coat Weight'].default_value = coat
    if emit:
        b.inputs['Emission Color'].default_value = hexc(color); b.inputs['Emission Strength'].default_value = emit
    _mats[k] = m; return m

NAVY, CYAN, PINK, YEL, WHITE = '#0b1430', '#43d5ef', '#ff3c7e', '#fedd54', '#eef2fa'

def finish(o, m, parent):
    o.data.materials.append(m); bpy.ops.object.shade_smooth()
    if parent: o.parent = parent
    return o
def rbox(size, loc, m, bevel=0.12, parent=None, seg=4):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.object
    o.scale = size; bpy.ops.object.transform_apply(scale=True)
    b = o.modifiers.new('b', 'BEVEL'); b.width = bevel; b.segments = seg; b.limit_method = 'NONE'
    return finish(o, m, parent)
def sph(r, loc, m, parent=None, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=24, ring_count=12)
    o = bpy.context.object; o.scale = scale; return finish(o, m, parent)
def cyl(r, depth, loc, m, parent=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=20)
    o = bpy.context.object; b = o.modifiers.new('b', 'BEVEL'); b.width = r*0.45; b.segments = 3
    return finish(o, m, parent)
def empty(name, loc, parent=None):
    o = bpy.data.objects.new(name, None); sc.collection.objects.link(o); o.location = loc
    if parent: o.parent = parent
    return o

# ---------------- set ----------------
bpy.ops.mesh.primitive_plane_add(size=400, location=(30, 0, 0)); bpy.context.object.data.materials.append(mat(NAVY, 0.45))
bpy.ops.mesh.primitive_cylinder_add(radius=8, depth=260, location=(30, 8.5, 8), rotation=(0, math.pi/2, 0), vertices=96)
bpy.context.object.data.materials.append(mat('#101c42', 0.8)); bpy.ops.object.shade_smooth()

# ---------------- characters ----------------
def robot(name, loc, body=WHITE, acc=CYAN, bulb=PINK, s=1.0, face=0.0):
    R = {}
    R['root'] = root = empty(name, loc); root.scale = (s, s, s); root.rotation_euler = (0, 0, face)
    R['hips'] = hips = empty(name+'_hips', (0, 0, 0.42), root)
    rbox((0.72, 0.52, 0.62), (0, 0, 0.32), mat(body, 0.28, coat=0.6), 0.16, hips)
    rbox((0.36, 0.06, 0.22), (0, -0.27, 0.30), mat(acc, 0.3), 0.04, hips)
    R['neck'] = neck = empty(name+'_neck', (0, 0, 0.66), hips)
    rbox((0.95, 0.72, 0.66), (0, 0, 0.36), mat(body, 0.28, coat=0.6), 0.2, neck)
    rbox((0.74, 0.08, 0.44), (0, -0.33, 0.37), mat('#0a0f22', 0.12, coat=1.0), 0.12, neck)
    em = mat(acc, 0.2, emit=12.0)
    R['eyes'] = [sph(0.075, (x, -0.38, 0.43), em, neck, (1, 0.5, 1.35)) for x in (-0.16, 0.16)]
    R['mouth'] = sph(0.10, (0, -0.38, 0.30), mat(acc, 0.2, emit=10.0), neck, (1, 0.4, 0.04))
    cyl(0.022, 0.3, (0, 0, 0.82), mat(acc, 0.3), neck)
    R['bulb'] = sph(0.07, (0, 0, 0.99), mat(bulb, 0.2, emit=4.0), neck)
    R['sh'], R['hp'] = {}, {}
    for side, x in (('L', -1), ('R', 1)):
        sh = empty(f'{name}_sh{side}', (x*0.43, 0, 0.55), hips); R['sh'][side] = sh
        cyl(0.075, 0.42, (0, 0, -0.2), mat(body, 0.28, coat=0.6), sh); sph(0.09, (0, 0, -0.43), mat(acc, 0.3), sh)
        hp = empty(f'{name}_hp{side}', (x*0.18, 0, 0.05), hips); R['hp'][side] = hp
        cyl(0.085, 0.36, (0, 0, -0.2), mat(acc, 0.3), hp); rbox((0.2, 0.28, 0.1), (0, -0.04, -0.4), mat(body, 0.28), 0.04, hp)
    return R

def dog(name, loc, face=0.0):
    D = {}
    D['root'] = root = empty(name, loc); root.rotation_euler = (0, 0, face)
    body = mat('#c98a4b', 0.5); dark = mat('#1a1a22', 0.3); light = mat('#f1d7b0', 0.5)
    D['body'] = rbox((1.0, 0.45, 0.45), (0, 0, 0.62), body, 0.18, root)
    D['neck'] = neck = empty(name+'_neck', (0.45, 0, 0.82), root)
    rbox((0.42, 0.40, 0.40), (0.12, 0, 0.12), body, 0.15, neck)
    rbox((0.24, 0.24, 0.18), (0.38, 0, 0.04), light, 0.08, neck)
    sph(0.05, (0.51, 0, 0.09), dark, neck)
    for y in (-0.11, 0.11):
        sph(0.04, (0.32, y, 0.22), dark, neck)
        rbox((0.12, 0.06, 0.22), (0.02, y*1.6, 0.36), mat('#8a5a2e', 0.5), 0.03, neck)
    D['mouth'] = sph(0.08, (0.47, 0, -0.04), mat('#5a1a22', 0.5), neck, (0.6, 1, 0.05))
    for x in (-0.35, 0.35):
        for y in (-0.15, 0.15): cyl(0.07, 0.42, (x, y, 0.22), body, root)
    D['tail'] = tail = empty(name+'_tail', (-0.5, 0, 0.75), root)
    cyl(0.04, 0.32, (-0.05, 0, 0.14), body, tail, rot=(0, -0.5, 0))
    return D

# set A (x=0): Vee + Pinky ; set B (x=25): adult + kid ; set C (x=50): Vee + dog ; set D (x=75): row of 5
vee = robot('vee', (0.55, 0, 0), face=0.25)
pinky = robot('pinky', (-0.75, 0.25, 0), body='#ffd6e4', acc=PINK, bulb=CYAN, face=-0.35)
adult = robot('adult', (24.4, 0, 0), body=WHITE, acc=YEL, bulb=PINK, face=-0.2)
kid = robot('kid', (25.6, -0.2, 0), body='#e3f6ff', acc=CYAN, bulb=YEL, s=0.6, face=0.2)
vee2 = robot('vee2', (49.2, 0, 0), face=0.3)
pup = dog('pup', (50.7, -0.1, 0), face=math.pi+0.35)
row = [robot(f'r{i}', (73.2 + i*0.9, (i % 2)*0.25, 0), acc=[CYAN, PINK, YEL, CYAN, PINK][i], bulb=[PINK, CYAN, PINK, YEL, CYAN][i], face=0.0) for i in range(5)]

bpy.ops.object.text_add(location=(1.6, 0.4, 8)); q = bpy.context.object
q.data.body = '?'; q.data.extrude = 0.12; q.data.bevel_depth = 0.03; q.data.size = 1.3; q.data.align_x = 'CENTER'
q.rotation_euler = (math.pi/2, 0, 0); q.data.materials.append(mat(YEL, 0.25, coat=0.8))

# ---------------- lights (rig follows the active set) + world ----------------
rig = empty('rig', (0, 0, 0))
def area(loc, rot, energy, color, size):
    l = bpy.data.lights.new('l', 'AREA'); l.energy = energy; l.color = hexc(color)[:3]; l.size = size
    o = bpy.data.objects.new('l', l); sc.collection.objects.link(o); o.location = loc; o.rotation_euler = rot; o.parent = rig
area((-2.5, -4, 4.5), (math.radians(55), 0, math.radians(-30)), 950, '#fff4e8', 4)
area((-3.5, 2.5, 2.5), (math.radians(-60), math.radians(-40), 0), 650, CYAN, 2)
area((3.5, 2.5, 2.5), (math.radians(-60), math.radians(40), 0), 650, PINK, 2)
area((3, -4, 1.5), (math.radians(80), 0, math.radians(35)), 220, '#cfe0ff', 5)
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = hexc('#0b1430')
w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.35
cd = bpy.data.cameras.new('cam'); cd.lens = 40
cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
tgt = empty('tgt', (0, 0, 1)); tc = cam.constraints.new('TRACK_TO'); tc.target = tgt; tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'

# ---------------- animation helpers ----------------
def ease(x): x = min(max(x, 0), 1); return x*x*(3-2*x)
def bell(t, t0, d):
    x = (t-t0)/d
    return math.sin(math.pi*x)**2 if 0 <= x <= 1 else 0.0
def K(o, path, v, f): setattr(o, path, v); o.keyframe_insert(data_path=path, frame=f)

def pose(R, f, t, yawn=0.0, look=0.0, tilt=0.0, arms=(0.0, 0.0), bob=0.0, blink=False, squeeze=0.0, shake=0.0):
    K(R['hips'], 'location', Vector((shake*0.03*math.sin(t*60), 0, 0.42+bob)), f)
    K(R['neck'], 'rotation_euler', Vector((0.35*yawn - 0.05, tilt, look)), f)
    ey = 1.35*(1-0.85*yawn)*(1-0.7*squeeze)
    if blink: ey = 0.12
    for e in R['eyes']: K(e, 'scale', Vector((1, 0.5, max(0.1, ey))), f)
    K(R['mouth'], 'scale', Vector((1.0, 0.4, 0.04+0.8*yawn)), f)
    K(R['sh']['L'], 'rotation_euler', Vector((arms[0], 0, 0)), f)
    K(R['sh']['R'], 'rotation_euler', Vector((arms[1], 0, 0)), f)
    for s in 'LR': K(R['hp'][s], 'rotation_euler', Vector((0, 0, 0)), f)

def dogpose(D, f, t, yawn=0.0, look=0.0):
    K(D['neck'], 'rotation_euler', Vector((0, -0.45*yawn, look)), f)
    K(D['mouth'], 'scale', Vector((0.6, 1, 0.05+1.3*yawn)), f)
    K(D['tail'], 'rotation_euler', Vector((0.5*math.sin(t*12), 0, 0)), f)

def segp(name, t): s = SEG[name]; return (t - s['start']) / (s['end'] - s['start']), t - s['start']

# camera shots per segment: (set_x, cam offset, target offset, lens, push)
SHOTS = {
 'hook':   (0,  (0.45, -3.0, 1.45), (0.5, 0, 1.25), 45, 0.5),
 'copy':   (0,  (-0.1, -5.6, 1.6), (-0.1, 0, 1.05), 40, 0.6),
 'resist': (0,  (0.6, -3.2, 1.45), (0.55, 0, 1.2), 45, 0.4),
 'kids':   (25, (0.0, -5.4, 1.5), (0.0, 0, 0.9), 40, 0.5),
 'dog':    (50, (0.0, -5.2, 1.4), (0.0, 0, 0.85), 40, 0.5),
 'chain':  (75, (0.0, -9.2, 1.8), (0.0, 0, 0.95), 32, 0.8),
 'why':    (0,  (0.4, -5.0, 1.55), (0.6, 0, 1.2), 40, 0.4),
 'payoff': (0,  (0.55, -2.9, 1.42), (0.55, 0, 1.25), 46, 0.6),
}

for f in range(1, NFR+1):
    t = (f-1)/FPS
    cur = [s for s in TL['segments'] if s['start'] <= t][-1]['name']
    sx, co, to, lens, push = SHOTS[cur]; p, lt = segp(cur, t)
    K(rig, 'location', Vector((sx if cur not in ('why', 'payoff', 'hook', 'copy', 'resist') else 0, 0, 0)), f)
    K(cam, 'location', Vector((sx+co[0], co[1] + push*ease(p), co[2])), f)
    K(tgt, 'location', Vector((sx+to[0], to[1], to[2])), f)
    cd.lens = lens; cd.keyframe_insert(data_path='lens', frame=f)
    blink = (t % 3.1) < 0.12
    # ---- set A: vee + pinky ----
    vy = 0.0; va = (0.0, 0.0); vlook = 0.0; vtilt = 0.0; vsq = 0.0; vshake = 0.0
    py = 0.0
    if cur == 'hook':
        vlook = -0.25  # looks at camera
    if cur == 'copy':
        py = bell(lt, 0.2, 1.8)                     # pinky yawns
        vy = bell(lt, 1.6, 1.7); vlook = -0.6*ease(lt/0.4)
    if cur == 'resist':
        if lt < 2.2: vsq = ease(lt/0.4); vshake = 1.0; vy = 0.12 + 0.06*math.sin(lt*18)
        else: vy = bell(lt, 2.0, 1.9); va = (-2.6*vy, -2.6*vy)
        vlook = -0.2
    if cur == 'why':
        va = (-0.9*ease(lt/0.4), -0.9*ease(lt/0.4)); vtilt = 0.3*ease((lt-0.5)/0.5); vlook = -0.1
    if cur == 'payoff':
        vlook = -0.25; vy = bell(lt, max(0.1, SEG['payoff']['speech']-0.4), 2.0)
        va = (-2.2*vy, -2.2*vy)
    pose(vee, f, t, vy, vlook, vtilt, va, blink=blink and vy < 0.1, squeeze=vsq, shake=vshake)
    pose(pinky, f, t, py, 0.45 if cur != 'hook' else 0.2, 0.0, (-2.4*py, -2.4*py), blink=blink)
    # question mark drops during 'why'
    if cur == 'why': z = 8 - 7.98*ease(min(1, lt/0.6)); K(q, 'location', Vector((1.6, 0.4, z)), f)
    elif t < SEG['why']['start']: K(q, 'location', Vector((1.6, 0.4, 8)), f)
    else: K(q, 'location', Vector((1.6, 0.4, 30)), f)
    # ---- set B: adult yawns, kid doesn't react ----
    p_b, lt_b = segp('kids', t)
    ay = bell(lt_b, 0.3, 2.0) if cur == 'kids' else 0.0
    pose(adult, f, t, ay, 0.3, 0.0, (-2.4*ay, -2.4*ay), blink=blink)
    kidwave = -2.4 + 0.4*math.sin(lt_b*10) if cur == 'kids' and lt_b > 1.6 else 0.0
    pose(kid, f, t, 0.0, -0.4 + 0.3*math.sin(lt_b*3), 0.15*math.sin(lt_b*4), (0.0, kidwave), bob=0.03*abs(math.sin(lt_b*6)), blink=blink)
    # ---- set C: vee2 yawns, dog copies ----
    p_c, lt_c = segp('dog', t)
    v2y = bell(lt_c, 0.2, 1.8) if cur == 'dog' else 0.0
    dyy = bell(lt_c, 1.5, 1.8) if cur == 'dog' else 0.0
    pose(vee2, f, t, v2y, 0.35, 0.0, (-2.3*v2y, -2.3*v2y), blink=blink)
    dogpose(pup, f, t, dyy, 0.0)
    # ---- set D: yawn travels down the row ----
    p_d, lt_d = segp('chain', t)
    for i, r in enumerate(row):
        y = bell(lt_d, 0.15 + i*0.55, 1.4) if cur == 'chain' else 0.0
        pose(r, f, t, y, 0.0, 0.0, (-2.3*y, -2.3*y), blink=blink and y < 0.1)

sc.frame_start, sc.frame_end = F0, F1
sc.render.fps = FPS; sc.render.resolution_x, sc.render.resolution_y = RW, RH
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True; sc.cycles.max_bounces = 3; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2
sc.cycles.transmission_bounces = 0; sc.cycles.volume_bounces = 0; sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
sc.cycles.adaptive_threshold = 0.05; sc.render.use_persistent_data = True
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'
sc.render.image_settings.file_format = 'PNG'
os.makedirs(OUT, exist_ok=True); sc.render.filepath = os.path.join(OUT, 'f_')
print('frames', NFR)
bpy.ops.render.render(animation=True)
