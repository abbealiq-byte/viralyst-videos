"""Viralyst 3D proof of concept: mascot robot walks in, a question mark drops, robot reacts.
Run: blender -b -P blender/poc_robot.py -- OUT_DIR WIDTH HEIGHT SAMPLES [FRAME_START FRAME_END]
or with the bpy module: python blender/poc_robot.py OUT_DIR ...
"""
import bpy, math, sys, os
from mathutils import Vector

argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
OUT = argv[0] if len(argv) > 0 else '/tmp/poc'
RW = int(argv[1]) if len(argv) > 1 else 720
RH = int(argv[2]) if len(argv) > 2 else 1280
SAMPLES = int(argv[3]) if len(argv) > 3 else 24
F0 = int(argv[4]) if len(argv) > 4 else 1
F1 = int(argv[5]) if len(argv) > 5 else 192
FPS = 24

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def hexc(h, a=1.0):
    h = h.lstrip('#'); r, g, b = (int(h[i:i+2], 16)/255 for i in (0, 2, 4))
    f = lambda c: c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4
    return (f(r), f(g), f(b), a)

NAVY, CYAN, PINK, YEL, WHITE = '#0b1430', '#43d5ef', '#ff3c7e', '#fedd54', '#eef2fa'

def mat(name, color, rough=0.35, emit=0.0, metal=0.0, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = hexc(color)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if coat: b.inputs['Coat Weight'].default_value = coat
    if emit:
        b.inputs['Emission Color'].default_value = hexc(color)
        b.inputs['Emission Strength'].default_value = emit
    return m

M_BODY = mat('body', WHITE, 0.28, coat=0.6)
M_ACC = mat('accent', CYAN, 0.3)
M_DARK = mat('screen', '#0a0f22', 0.12, coat=1.0)
M_EYE = mat('eye', CYAN, 0.2, emit=12.0)
M_BULB = mat('bulb', PINK, 0.2, emit=4.0)
M_Q = mat('question', YEL, 0.25, coat=0.8)
M_FLOOR = mat('floor', NAVY, 0.45)
M_BACK = mat('backdrop', '#101c42', 0.8)

def rbox(name, size, loc, m, bevel=0.12, parent=None, seg=4):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.object; o.name = name
    o.scale = size; bpy.ops.object.transform_apply(scale=True)
    bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = bevel; bv.segments = seg; bv.limit_method = 'NONE'
    o.data.materials.append(m); bpy.ops.object.shade_smooth()
    if parent: o.parent = parent
    return o

def sphere(name, r, loc, m, parent=None, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=32, ring_count=16)
    o = bpy.context.object; o.name = name; o.scale = scale; o.data.materials.append(m); bpy.ops.object.shade_smooth()
    if parent: o.parent = parent
    return o

def cyl(name, r, depth, loc, m, parent=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=24)
    o = bpy.context.object; o.name = name; o.data.materials.append(m); bpy.ops.object.shade_smooth()
    bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = r*0.45; bv.segments = 3
    if parent: o.parent = parent
    return o

def empty(name, loc, parent=None):
    o = bpy.data.objects.new(name, None); sc.collection.objects.link(o); o.location = loc
    if parent: o.parent = parent
    return o

# ---------- set: floor + curved backdrop ----------
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0)); fl = bpy.context.object; fl.data.materials.append(M_FLOOR)
bpy.ops.mesh.primitive_cylinder_add(radius=8, depth=40, location=(0, 8, 8), rotation=(0, math.pi/2, 0), vertices=96)
bk = bpy.context.object; bk.data.materials.append(M_BACK); bpy.ops.object.shade_smooth()

# ---------- robot "Vee" (all parts parented to rig root) ----------
root = empty('vee_root', (-2.4, 0, 0))
hips = empty('vee_hips', (0, 0, 0.42), root)
body = rbox('vee_body', (0.72, 0.52, 0.62), (0, 0, 0.32), M_BODY, 0.16, hips)
belly = rbox('vee_belly', (0.36, 0.06, 0.22), (0, -0.27, 0.30), M_ACC, 0.04, hips)
neck = empty('vee_neck', (0, 0, 0.66), hips)
head = rbox('vee_head', (0.95, 0.72, 0.66), (0, 0, 0.36), M_BODY, 0.2, neck)
screen = rbox('vee_screen', (0.74, 0.08, 0.44), (0, -0.33, 0.37), M_DARK, 0.12, neck)
eyeL = sphere('vee_eyeL', 0.075, (-0.16, -0.38, 0.39), M_EYE, neck, (1, 0.5, 1.35))
eyeR = sphere('vee_eyeR', 0.075, (0.16, -0.38, 0.39), M_EYE, neck, (1, 0.5, 1.35))
cyl('vee_ant', 0.022, 0.3, (0, 0, 0.82), M_ACC, neck)
bulb = sphere('vee_bulb', 0.07, (0, 0, 0.99), M_BULB, neck)
for side, x in (('L', -1), ('R', 1)):
    sh = empty(f'vee_sh{side}', (x*0.43, 0, 0.55), hips)
    cyl(f'vee_arm{side}', 0.075, 0.42, (0, 0, -0.2), M_BODY, sh)
    sphere(f'vee_hand{side}', 0.09, (0, 0, -0.43), M_ACC, sh)
    hp = empty(f'vee_hip{side}', (x*0.18, 0, 0.05), hips)
    cyl(f'vee_leg{side}', 0.085, 0.36, (0, 0, -0.2), M_ACC, hp)
    rbox(f'vee_foot{side}', (0.2, 0.28, 0.1), (0, -0.04, -0.4), M_BODY, 0.04, hp)
SH = {s: bpy.data.objects[f'vee_sh{s}'] for s in 'LR'}; HP = {s: bpy.data.objects[f'vee_hip{s}'] for s in 'LR'}

# ---------- prop: big 3D question mark ----------
bpy.ops.object.text_add(location=(1.0, 0.3, 6)); q = bpy.context.object
q.data.body = '?'; q.data.extrude = 0.12; q.data.bevel_depth = 0.03; q.data.bevel_resolution = 3
q.data.size = 1.6; q.data.align_x = 'CENTER'; q.rotation_euler = (math.pi/2, 0, 0); q.data.materials.append(M_Q)

# ---------- lights + world ----------
def area(name, loc, rot, energy, color, size):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.color = hexc(color)[:3]; l.size = size
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc; o.rotation_euler = rot
    return o
area('key', (-2.5, -4, 4.5), (math.radians(55), 0, math.radians(-30)), 900, '#fff4e8', 4)
area('rimC', (-3.5, 2.5, 2.5), (math.radians(-60), math.radians(-40), 0), 700, CYAN, 2)
area('rimP', (3.5, 2.5, 2.5), (math.radians(-60), math.radians(40), 0), 700, PINK, 2)
area('fill', (3, -4, 1.5), (math.radians(80), 0, math.radians(35)), 200, '#cfe0ff', 5)
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = hexc('#0b1430')
w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.35

# ---------- camera ----------
cd = bpy.data.cameras.new('cam'); cd.lens = 36
cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
tgt = empty('cam_target', (0, 0, 1.15))
tc = cam.constraints.new('TRACK_TO'); tc.target = tgt; tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'

# ---------- animation ----------
def ease(x): x = min(max(x, 0), 1); return x*x*(3-2*x)
def bounce(x):
    x = min(max(x, 0), 1)
    if x < 0.6: return (x/0.6)**2
    y = (x-0.6)/0.4; return 1 - 0.12*math.sin(y*math.pi)*(1-y)
def key(o, path, val, f):
    setattr(o, path, val); o.keyframe_insert(data_path=path, frame=f)

for f in range(1, 193):
    t = (f-1)/FPS
    # walk in 0..3 s
    wp = ease(t/3.0); x = -2.4 + 2.0*wp
    walking = t < 3.0
    ph = t*2*math.pi*1.8
    bob = 0.05*abs(math.sin(ph)) if walking else 0.0
    # jump at 4.3..5.0 s
    jt = (t-4.3)/0.7; jump = 0.45*math.sin(math.pi*jt) if 0 <= jt <= 1 else 0.0
    key(root, 'location', Vector((x, 0, 0)), f)
    key(hips, 'location', Vector((0, 0, 0.42+bob+jump)), f)
    lean = 0.08*math.sin(ph) if walking else 0.0
    key(hips, 'rotation_euler', Vector((0, lean*0.4, 0)), f)
    for s, sg in (('L', 1), ('R', -1)):
        sw = 0.6*math.sin(ph)*sg if walking else 0.0
        arm = sw
        if 4.3 <= t <= 5.0: arm = -2.4*math.sin(math.pi*jt)  # arms up in surprise
        if t > 5.6 and s == 'R': arm = -2.6*ease((t-5.6)/0.4) + 0.15*math.sin(t*14)*ease((t-5.9)/0.3)  # scratch head
        key(SH[s], 'rotation_euler', Vector((arm, 0, 0)), f)
        leg = -0.55*math.sin(ph)*sg if walking else 0.0
        key(HP[s], 'rotation_euler', Vector((leg, 0, 0)), f)
    # head: look toward the question mark, then tilt (curious)
    look = ease((t-3.2)/0.4)*0.55
    tilt = ease((t-5.5)/0.5)*0.28
    key(neck, 'rotation_euler', Vector((-0.12*ease((t-3.6)/0.4), tilt, look)), f)
    # eyes: blink at 2 s, wide at surprise, squint while thinking
    ey = 1.35
    if 1.9 < t < 2.05: ey = 0.15
    if 4.2 <= t <= 5.2: ey = 1.35 + 0.6*math.sin(math.pi*min(1, (t-4.2)/1.0))
    if t > 5.8: ey = 1.0
    for e in (eyeL, eyeR): key(e, 'scale', Vector((1, 0.5, ey)), f)
    # antenna bulb flashes on surprise
    bs = 1.0 + (0.6 if 4.3 <= t <= 5.2 and int(t*10) % 2 == 0 else 0.0)
    key(bulb, 'scale', Vector((bs, bs, bs)), f)
    # question mark drops at 3.7 s and bounces, then slowly spins
    dq = bounce((t-3.7)/0.7)
    key(q, 'location', Vector((0.95, 0.3, 6 - 5.98*dq if t >= 3.7 else 6)), f)
    sq = 1.0
    if 4.12 <= t <= 4.35: sq = 0.82
    key(q, 'scale', Vector((1/sq**0.5, 1/sq**0.5, sq)), f)
    key(q, 'rotation_euler', Vector((math.pi/2, 0, 0.35*math.sin(max(0, t-4.6)*1.4))), f)
    # camera: slow push-in and slight drift
    tx = x*0.45 + 0.45*ease((t-3)/1.5)
    cy = -6.4 + 1.4*ease(t/8.0)
    key(cam, 'location', Vector((tx - 0.25, cy, 1.7 - 0.15*ease(t/8.0))), f)
    key(tgt, 'location', Vector((tx, 0, 1.0)), f)

# ---------- render settings ----------
sc.frame_start, sc.frame_end = F0, F1
sc.render.fps = FPS
sc.render.resolution_x, sc.render.resolution_y = RW, RH
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 3
sc.cycles.diffuse_bounces = 2
sc.cycles.glossy_bounces = 2
sc.cycles.transmission_bounces = 0
sc.cycles.volume_bounces = 0
sc.cycles.caustics_reflective = False
sc.cycles.caustics_refractive = False
sc.render.use_persistent_data = True
sc.cycles.adaptive_threshold = 0.05
sc.cycles.use_adaptive_sampling = True
sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = 'AgX - Punchy'
sc.render.film_transparent = False
sc.render.image_settings.file_format = 'PNG'
os.makedirs(OUT, exist_ok=True)
sc.render.filepath = os.path.join(OUT, 'f_')
bpy.ops.render.render(animation=True)
print('done')
