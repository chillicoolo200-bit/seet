"""Generate a simple, editable 8C-style humanoid blockout in Blender.

This is intentionally a proportion/material blockout, NOT a final likeness-matched
character. It creates a lightweight GLB artifact so the mobile viewer pipeline can
be tested before detailed modeling, facial rigging, and reference matching.
Run: blender --background --python tools/8c_blender_build.py -- --output dist/8c-blockout.glb
"""
import argparse
import os
import sys
import bpy
from mathutils import Vector

def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="dist/8c-blockout.glb")
    p.add_argument("--quality", choices=("mobile", "standard"), default="mobile")
    return p.parse_args(argv)

def mat(name, color, metallic=0.0, roughness=0.55):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (*color, 1.0)
    bs.inputs["Metallic"].default_value = metallic
    bs.inputs["Roughness"].default_value = roughness
    return m

def uv(name, loc, scale, material, segments):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=max(8, segments//2), location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    return o

def cube(name, loc, scale, material, bevel=0.12):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    if bevel:
        mod = o.modifiers.new("Soft garment edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        o.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    return o

def bone_parent(obj, rig, bone):
    world = obj.matrix_world.copy()
    obj.parent = rig
    obj.parent_type = "BONE"
    obj.parent_bone = bone
    obj.matrix_world = world

def main():
    a = args()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    seg = 16 if a.quality == "mobile" else 32

    ink = mat("8C | charcoal streetwear", (0.025,0.03,0.055), 0.12)
    white = mat("8C | soft white", (0.82,0.86,0.94))
    skin = mat("8C | warm porcelain", (0.92,0.72,0.64))
    hair = mat("8C | midnight bob", (0.012,0.018,0.04), 0.18)
    purple = mat("8C | violet accents", (0.32,0.12,0.72), 0.35)
    blue = mat("8C | electric blue", (0.08,0.38,0.95), 0.25)

    # Humanoid skeleton with a small, useful set of animation bones.
    arm = bpy.data.armatures.new("8C_HumanoidRig")
    rig = bpy.data.objects.new("8C_HumanoidRig", arm)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bones = {
      "root": ((0,0,0.05),(0,0,0.9),None),
      "spine": ((0,0,0.9),(0,0,1.65),"root"),
      "head": ((0,0,1.65),(0,0,2.25),"spine"),
      "arm.L": ((-0.28,0,1.55),(-0.72,0,1.12),"spine"),
      "arm.R": ((0.28,0,1.55),(0.72,0,1.12),"spine"),
      "leg.L": ((-0.16,0,0.9),(-0.18,0,0.12),"root"),
      "leg.R": ((0.16,0,0.9),(0.18,0,0.12),"root"),
    }
    for name,(head,tail,parent) in bones.items():
        b=arm.edit_bones.new(name); b.head=head; b.tail=tail
        if parent: b.parent=arm.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.show_in_front=True

    # Simplified outfit silhouette. Objects are bone-parented for safe preview posing.
    parts = [
      (uv("Face", (0,0,2.02),(.27,.23,.32),skin,seg),"head"),
      (uv("Bob hair cap", (0,.015,2.20),(.31,.25,.25),hair,seg),"head"),
      (uv("Bob hair left",(-.255,0,2.02),(.105,.20,.28),hair,seg),"head"),
      (uv("Bob hair right",(.255,0,2.02),(.105,.20,.28),hair,seg),"head"),
      (uv("Torso jacket",(0,0,1.36),(.43,.28,.48),ink,seg),"spine"),
      (uv("Jacket white panel",(0,-.255,1.40),(.19,.035,.37),white,seg),"spine"),
      (uv("Left sleeve",(-.48,0,1.35),(.17,.19,.36),ink,seg),"spine"),
      (uv("Right sleeve",(.48,0,1.35),(.17,.19,.36),ink,seg),"spine"),
      (uv("Left cargo leg",(-.17,0,.55),(.16,.19,.43),ink,seg),"leg.L"),
      (uv("Right cargo leg",(.17,0,.55),(.16,.19,.43),ink,seg),"leg.R"),
      (uv("Left sneaker",(-.18,-.07,.12),(.18,.28,.11),white,seg),"leg.L"),
      (uv("Right sneaker",(.18,-.07,.12),(.18,.28,.11),white,seg),"leg.R"),
      (uv("Left headphone cup",(-.30,0,2.05),(.075,.13,.16),purple,seg),"head"),
      (uv("Right headphone cup",(.30,0,2.05),(.075,.13,.16),purple,seg),"head"),
      (uv("Headphone band",(0,.02,2.30),(.31,.055,.06),blue,seg),"head"),
      (uv("Left eye",(-.105,-.218,2.06),(.045,.025,.027),blue,seg),"head"),
      (uv("Right eye",(.105,-.218,2.06),(.045,.025,.027),blue,seg),"head"),
    ]
    for obj,bone in parts: bone_parent(obj,rig,bone)

    # Gentle looping idle: breathing/spine sway and small head turn.
    scene=bpy.context.scene
    scene.frame_start=1; scene.frame_end=48; scene.render.fps=24
    for frame, angle in ((1,0.0),(13,0.025),(25,0.0),(37,-0.025),(48,0.0)):
        scene.frame_set(frame)
        pb=rig.pose.bones["spine"]; pb.rotation_mode="XYZ"; pb.rotation_euler[1]=angle
        pb.keyframe_insert(data_path="rotation_euler",frame=frame,group="Idle | breathing")
        hb=rig.pose.bones["head"]; hb.rotation_mode="XYZ"; hb.rotation_euler[2]=angle*1.8
        hb.keyframe_insert(data_path="rotation_euler",frame=frame,group="Idle | head")
    if rig.animation_data and rig.animation_data.action:
        for fc in rig.animation_data.action.fcurves:
            for key in fc.keyframe_points: key.interpolation="BEZIER"
    scene.frame_set(1)

    # Export only the character and rig, not a scene camera or lights.
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    for obj,_ in parts: obj.select_set(True)
    bpy.context.view_layer.objects.active=rig
    out=os.path.abspath(a.output)
    os.makedirs(os.path.dirname(out),exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True,
                              export_animations=True, export_skins=True)
    print("8C_BLOCKOUT_EXPORTED:",out)

if __name__ == "__main__":
    main()
