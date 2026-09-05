---
name: blender-model
description: Build anything in Blender via Python — model, materials, lighting, cameras, render, animation, export. Renders after every change, looks at the picture, fixes until right. Never reports success without a visual pass. Use when user wants a 3D model, scene, render, animation, material, or any Blender work.
---

# blender-model — see it, fix it, repeat

Merged from: RobLe3 cc-blender-skill (30 skills, validated Blender 5.1.1), ra100 blender-claude-plugin (8 bpy reference skills), ahujasid blender-mcp, Blender Lab official MCP, LobeHub blender agent skill, SceneCraft (Google/Caltech dual-loop), 3D-Agent (perceive→reason→act→verify). Installed copies: `~/src/cc-blender-skill`, `~/src/blender-claude-plugin`, 38 individual skills symlinked in `~/.agents/skills/`.

## Triggers

Any 3D request, even without the word Blender: "model a…", "render…", "make it look like copper", "light this", "animate…", "export glTF…". Full-scene work: plan order first (block-out → camera lock → light v1 → refine geo → materials v1 → light v2 → detail → final render → composite → export).

## Two execution paths

**A. Live Blender via MCP** (user driving, Blender open): addon `blender_mcp.py` in Blender 5.0 addons dir, server `DISABLE_TELEMETRY=true uvx --python 3.11 blender-mcp`, Blender sidebar N-panel → Start MCP Server. Tools: `execute_blender_code`, `get_scene_info`/`get_objects_summary`, `get_object_detail_summary`, `get_viewport_screenshot`, `search_api_docs`. First call: `get_scene_info`; on "Could not connect" stop and tell user to start the addon.

**B. Headless loop** (default here, verified on this box Blender 5.0.0): write `bpy` script → `blender --background --python s.py` → render PNG → `read` the PNG → fix → repeat. Workbench preview renders ~0.2s/frame. This is how long autonomous sessions work: the PNG is the eyes.

## The loop (non-negotiable)

1. Small change (one object, one material, one light at a time).
2. Render and LOOK: headless path renders PNG and reads it; live path uses `get_viewport_screenshot`.
3. Compare against goal: subject visible and recognisable (not streak/magenta/shadow), proportions match real dimensions, in frame not clipped/microscopic, materials show variation (flat plastic → add Noise/Voronoi→ColorRamp→Roughness/Bump).
4. Wrong → fix + re-render. Never report success without a visual pass.
5. On repeated failure: freeze (keep baseline + failed version, honest names, no overwrite), name the failing dimension (geometry / UV / look / motion), fix the method not the artifact, then retry. Same failure twice → stop and say what is blocked.

Vision feedback is the single biggest quality factor. Blind code execution drifts into geometry soup after 3–4 steps.

## Global exec rules

- Each code call = fresh namespace (only `bpy` pre-imported). Re-import everything every call. Never reference Python vars across calls; identify objects by stable name `bpy.data.objects['GEO-x']`.
- Chunk ~5–20 lines per call. End each chunk with `print(...)` structured output (names, counts, verts).
- Names: `GEO-` mesh, `MAT-` material, `LGT-` light, `CAM-` camera, `ARM-` rig, `COL-` collection. Suffix `.L`/`.R` for pairs.
- Confirm files exist after render/export (`ls -la`).
- Real dimensions BEFORE modeling: sword ~95–100cm total (blade 78×4.5×0.8, guard 20×2.5, grip 13, pommel 5.6); chair seat 45×45×4, height 45; bottle 25–30 tall, body ø8–10, neck ø2–3. Unknown subject → dimensions.com/Wikipedia first.

## Scene setup snippets (verified)

World reset first (stale env texture = magenta flood):
```python
import bpy
def reset_world(scene, color=(0.04,0.04,0.05,1.0), strength=0.4):
    world=scene.world; world.use_nodes=True; nodes=world.node_tree.nodes
    for n in list(nodes): nodes.remove(n)
    output=nodes.new('ShaderNodeOutputWorld'); bg=nodes.new('ShaderNodeBackground')
    bg.inputs['Color'].default_value=color; bg.inputs['Strength'].default_value=strength
    world.node_tree.links.new(bg.outputs['Background'], output.inputs['Surface'])
```

Aim camera at target (headless-safe, no constraints):
```python
from mathutils import Vector, Matrix
target=Vector((1.0,0,1)); loc=cam.location
forward=(target-loc).normalized(); up=Vector((0,0,1))
right=forward.cross(up).normalized(); up2=right.cross(forward).normalized()
m=Matrix((right,up2,-forward)).transposed().to_4x4(); m.translation=loc
cam.matrix_world=m
```

Camera guard before any render:
```python
def ensure_camera(scene):
    if scene.camera is not None: return scene.camera.name
    cams=[o for o in bpy.data.objects if o.type=='CAMERA']
    if not cams: raise RuntimeError("No camera in scene")
    scene.camera=cams[0]; return cams[0].name
```

Headless Workbench preview (fast truth, unlit, distinct colors):
```python
sc=bpy.context.scene; sc.render.engine='BLENDER_WORKBENCH'
sc.display.shading.light='FLAT'; sc.display.shading.color_type='MATERIAL'
sc.render.resolution_x=480; sc.render.resolution_y=270
sc.render.filepath='/tmp/see.png'; sc.render.image_settings.file_format='PNG'
bpy.ops.render.render(write_still=True)
```
Give every mesh a different vivid `diffuse_color` (with `use_nodes=False`) so parts are distinguishable in preview.

## Modeling

- Elongated parts: thin/broad/long axes explicit; rotate broad axis toward camera.
- Overlap joins 5–15mm instead of exact touching. Same-material seamless = Boolean Union.
- Taper to point: collapse top verts to axis, `remove_doubles(threshold=0.001)`.
- Hard-surface stack order: Mirror → Array → Solidify → Bevel → SubSurf → Boolean. Bevel width 0.02, 3 segments, limit ANGLE 30°. SubSurf 2 viewport / 3 render. Mirror first with `use_clip`, merge threshold 0.001. SubSurf-before-Bevel = pinching (most common amateur error).
- Boolean cut: `operation='DIFFERENCE'`, `solver='EXACT'`, hide cutter viewport+render.
- Array+Curve: `fit_type='FIT_CURVE'`, `relative_offset_displace=(1,0,0)`, Curve modifier `deform_axis='POS_X'`.
- Cleanup after every build: `remove_doubles(0.0001)` + `normals_make_consistent(inside=False)` + `shade_smooth()`. Black faces = recompute normals. N-gons after boolean = fix to quads before SubSurf.
- bmesh pattern: `bm=bmesh.from_edit_mesh(obj.data)` … `bmesh.update_edit_mesh(obj.data)`. Standalone: `bmesh.new()` → build → `to_mesh(me)` → `free()`, link object to collection.
- Blender 5.x: no `Mesh.use_auto_smooth` (modifier/per-face instead); `shade_smooth()` per object.

## Modifiers (~50, `obj.modifiers.new(name,'TYPE')`)

Generate: ARRAY BEVEL BOOLEAN BUILD DECIMATE EDGE_SPLIT MASK MESH_TO_VOLUME MIRROR MULTIRES NODES REMESH SCREW SKIN SOLIDIFY SUBSURF TRIANGULATE VOLUME_TO_MESH WELD WIREFRAME. Deform: ARMATURE CAST CORRECTIVE_SMOOTH CURVE DISPLACE HOOK LAPLACIANDEFORM LATTICE MESH_DEFORM SHRINKWRAP SIMPLE_DEFORM SMOOTH LAPLACIANSMOOTH SURFACE_DEFORM VOLUME_DISPLACE WARP WAVE. Physics: CLOTH COLLISION DYNAMIC_PAINT EXPLODE FLUID OCEAN PARTICLE_INSTANCE PARTICLE_SYSTEM SOFT_BODY. Normals/UV: NORMAL_EDIT WEIGHTED_NORMAL DATA_TRANSFER UV_PROJECT UV_WARP.
- Shrinkwrap lock: `wrap_method='NEAREST_SURFACEPOINT'`, `wrap_mode='ON_SURFACE'`. Decimate web: `decimate_type='COLLAPSE'`, ratio 0.5–0.7.
- WeightedNormal after Bevel: `mode='FACE_AREA'`, `keep_sharp=True`.

## Materials (Principled BSDF only — only shader exporting cleanly to glTF)

- METALLIC IS A SWITCH: 0.0 dielectric or 1.0 metal. Never 0.2–0.8.
- Blender 5.x: string lookup of `Weight`/`Subsurface IOR` raises KeyError — use helper:
```python
def set_input(node,name,value):
    for inp in node.inputs:
        if inp.name==name: inp.default_value=value; return True
    return False
```
- Values: steel (0.56,0.57,0.58) M1 R0.25; gold (1.0,0.78,0.34) R0.05; copper (0.93,0.72,0.50) R0.05; chrome (0.55,0.56,0.55) R0.02; clear glass white M0 R0.02–0.05 Transmission 1.0 IOR 1.5; frosted R0.3; matte plastic IOR 1.45 R0.6; lacquer R0.15 + Coat 0.8/0.05; skin (0.85,0.65,0.55) R0.4 Subsurface 1.0 Radius (1.0,0.2,0.1) IOR 1.4; velvet R0.9 Sheen 0.5/0.5 Tint (0.8,0.6,0.6); silicone R0.7 IOR 1.4. Metals keep Base ≥0.5. Roughness min 0.01–0.05.
- Coloured glass: surface near-white + Volume Absorption on Material Output Volume. Density: 5–15 subtle, 30–50 medium, 60–100 bottle (wine 80, amber 70, cobalt 80, ruby 100, champagne 25). Never tint Base Color AND volume. Needs `scene.cycles.transmission_bounces=24`.
- Emission: replace Principled with `ShaderNodeEmission`. Strength ∝ 1/area: 1–2cm bulb 800–1500; 3–5cm 1500–3000; 10cm panel 100–300; neon 50–150; window 5–20. Tungsten (1.0,0.85,0.6).
- Procedural wood: TexCoord Generated→Mapping(3,3,3)→Wave BANDS X (Scale 5, Distortion 4) + Noise(8)→MixRGB MULTIPLY 0.5→ColorRamp dark (0.15,0.07,0.03)→light (0.6,0.35,0.18)→Base; R0.7. Procedurals don't export → bake first (`bake(type='DIFFUSE',pass_filter={'COLOR'},margin=16)`, needs UV + active Image Texture node, Cycles).
- Image textures: basecolor sRGB; roughness/metallic/bump/normal/AO/lightmap Non-Color. Bump strength 0.02.
- Plasticky metals → fix Metallic 0/1. Black metal → Base too dark. Black glass → bounces. Invisible in glTF → procedural, bake.

## Lighting

- Default Area lights (soft shadows free); Sun only for sun/moon. `size` = softness (0.1 hard, 2.0 soft); Sun `angle` likewise.
- Aim helper: `direction.to_track_quat('-Z','Y').to_euler()`. Bbox center via evaluated depsgraph (`evaluated_get(dg).to_mesh()`, then `to_mesh_clear()`).
- Three-point, `d=max(biggest*1.5,1.0)`, `base=100*(d/1.5)**2`: key (+0.7d,−0.7d,+0.5d) size 0.5; fill (−0.7d,−0.5d,+0.3d) size 1.0; rim (0,+d,+0.5d) spot 50°. Delete old LGT-key/fill/rim first. Ratios — high-key 2:1, portrait 4:1, low-key 8:1+, rim 50–100% key.
- Class presets (key:fill:rim + temp): metal 4:1:2 warm 3200K (1.0,0.95,0.85); glass 3:1:1.2 neutral 5500K, rim = AREA 1.5 (spot washes volume tint); wood 4:1:1.5 warm 3000K; fabric 3:1:0.5 neutral; skin 4:1:1 warm 3500K; product 5:1:1.5 neutral 5000K.
- Emissive subject: world dark (0.02,0.02,0.03) strength 0.10–0.20, one ambient Area 8–15W from camera, `cycles.max_bounces≥16`.
- HDRI: wipe world nodes → TexCoord Generated→Mapping→TexEnvironment (`env.image` load, verify not None)→Background 1.0→Output. polyhaven.com/hdris.
- Temps: candle (1.0,0.6,0.3), tungsten (1.0,0.85,0.6), sunset (1.0,0.85,0.65), noon (1,1,1), overcast (0.95,0.95,1.0), blue hour (0.8,0.9,1.0). Warm key + cool fill = Hollywood.
- Half-black → fill/HDRI. Flat → raise key:fill + rim. Rim blowout → rim≤key.

## Cameras

- Focal: 14–24 spectacle; 28–35 establishing; 50 neutral; 85 intimate; 100–135 hero product; 200+ compression. Portraits ≥50mm. f-stops: 1.2–2 dreamy; 2.8 portrait; 4 two-subject; 5.6–8 group; 11+ landscape.
- Bbox hero: 60mm, `dist=biggest/0.32`, cam at (cx+0.3d, cy−d, cz), Empty target at center, TRACK_TO (`TRACK_NEGATIVE_Z`/`UP_Y`), DoF on f/4 with `focus_object`.
- `show_composition_thirds=True` for framing (viewport only). Thirds, 10% headroom, nose room, foreground/mid/background layers.
- Orbit 10s: Empty pivot at target, cam child, keyframe pivot Z 0→360° frames 1–240, all fcurves LINEAR. Push-in: keyframe location, never zoom.
- Sensors: full-frame 36, APS-C 22.5, Super35 24.89, MFT 17.3.

## Rendering

- Cycles production: GPU, 256 samples, adaptive threshold 0.01 min 32, denoise OIDN (OPTIX on RTX), bounces total 12 / transmission 12. Draft: 64 samples, threshold 0.05, 50% res. Samples guide: sun 64–128, product 256, indoor 512, glass/SSS 1024–2048. 256+denoise ≈ 4096 raw.
- EEVEE version-safe: try `BLENDER_EEVEE_NEXT` except → `BLENDER_EEVEE`; `taa_render_samples=64`, `use_gtao=True` (distance 0.2), bloom+SSR+volumetrics on. SSR on-screen only (add probes); indirect baked; no caustics.
- Color: `view_transform='AgX'`, never Standard for photo. Exposure 0, gamma 1.
- Still: ensure_camera → PNG RGBA 16-bit absolute path → `render(write_still=True)` → verify file.
- Animation: PNG sequence `frame_` + `use_placeholder=True`, `use_overwrite=False`, `use_persistent_data=True`, `render(animation=True)`; then `ffmpeg -framerate 24 -i frame_%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 anim.mp4`. Never direct-to-MP4.
- GPU once: `addons['cycles'].preferences.compute_device_type='OPTIX'` (or CUDA/HIP/METAL), enable all devices.
- Light paths: total 12 (glass 16); diffuse 4 (interior 8); glossy 4; transmission 12 (glass 16–24); transparent 8.

## Geometry Nodes

- Type strings `GeometryNode<Pascal>`; shared math/tex/color are `ShaderNode*` (`ShaderNodeMath/TexNoise/ValToRGB`); bool/compare/random are `FunctionNode*`. Sockets `NodeSocketFloat/Vector/Color/Bool/Int/String/Geometry/Object/Collection/Material/Image/Rotation/Matrix/Menu` (+5.1 `NodeSocketFont`).
```python
ng=bpy.data.node_groups.new("G","GeometryNodeTree"); n=ng.nodes; l=ng.links; n.clear()
gi=n.new('NodeGroupInput'); go=n.new('NodeGroupOutput')
# 4.x+: ng.interface.new_socket(name,in_out='INPUT'/'OUTPUT',socket_type='NodeSocketGeometry')
a=n.new(type='GeometryNodeMeshCube'); b=n.new(type='GeometryNodeSetPosition')
l.new(a.outputs[0],b.inputs[0]); l.new(gi.outputs[0],b.inputs[0])
mod=obj.modifiers.new("GN",'NODES'); mod.node_group=ng
```
- Scatter: Grid→DistributePointsOnFaces→InstanceOnPoints (+RandomValue rot/scale). Realize only if mesh ops needed. Deform: GroupIn→SetPosition, offset = Position→Noise→VectorMath→Math. Conditional: SeparateGeometry→branches→JoinGeometry. Sim: SimInput→body→SimOutput; GroupInput defaults only inside sim → pass as state items (`state_items.new('VECTOR','name')`); NamedAttrs freeze after frame1. Mix by socket NAMES (indices shift). Set `operation` before linking. Link removal: iterate `list(ng.links)`.
- Slow tree: early Realize→late; static Capture→Bake node; dense distribute→Grid; subsurf vp 1–2; boolean→SDF Grid Boolean; sim payload minimal.
- Full node catalog (373): Constant Bool/Collection/Color/Image/Integer/Material/Object/Rotation/String/Value/Vector; Gizmo Dial/Linear/Transform; Import CSV/OBJ/PLY/STL/Text/VDB; Scene 3DCursor/ActiveCamera/CameraInfo/BoneInfo/CollectionChildren/CollectionInfo/ImageInfo/IsViewport/MousePosition/ObjectInfo/SceneTime/SelfObject/ViewportTransform; Output EnableOutput/GroupOutput/Viewer/Warning; Attr AttributeStatistic/DomainSize/BlurAttribute/CaptureAttribute/RemoveNamedAttribute/StoreNamedAttribute; Curve Read HandlePositions/CurveLength/CurveTangent/CurveTilt/EndpointSelection/HandleTypeSelection/SplineCyclic/SplineLength/SplineParameter/SplineResolution + SampleCurve + Write SetCurveNormal/SetCurveRadius/SetCurveTilt/SetHandlePositions/SetHandleType/SetSplineCyclic/SetSplineResolution/SetSplineType + Ops CurveToMesh/CurveToPoints/CurvesToGreasePencil/DeformCurvesOnSurface/CurveFill/CurveFillet/InterpolateCurves/ResampleCurve/ReverseCurve/SubdivideCurve/TrimCurve + Prim Arc/BezierSegment/Circle/Line/QuadraticBezier/Quadrilateral/Spiral/Star + Topo CurveOfPoint/OffsetPointInCurve/PointsOfCurve; GreasePencil NamedLayerSelection/SetColor/SetDepthMode/SetSoftness/GPtoCurves/MergeLayers; Geo Read ID/Index/NamedAttribute/Normal/Position/Radius/ToolSelection/ToolActiveElement/GetGeometryBundle + Sample GeometryProximity/IndexOfNearest/Raycast/SampleIndex/SampleNearest + Write SetGeometryBundle/SetGeometryName/SetID/SetPosition/ToolSetSelection + Ops Bake/BoundingBox/ConvexHull/DeleteGeometry/DuplicateElements/JoinGeometry/MergeByDistance/SortElements/TransformGeometry/SeparateComponents/SeparateGeometry/SplitToInstances/GeometryToInstance + Mat ReplaceMaterial/MaterialIndex/MaterialSelection/SetMaterial/SetMaterialIndex; Mesh Read EdgeAngle/EdgeNeighbors/EdgeVertices/EdgesToFaceGroups/FaceArea/FaceGroupBoundaries/FaceNeighbors/FaceIsPlanar/ShadeSmooth/EdgeSmooth/MeshIsland/ShortestEdgePaths/VertexNeighbors + Sample SampleNearestSurface/SampleUVSurface + Write SetFaceSet/SetMeshNormal/SetShadeSmooth + Ops DualMesh/EdgePathsToCurves/EdgePathsToSelection/ExtrudeMesh/FlipFaces/MeshBoolean/MeshToCurve/MeshToDensityGrid/MeshToPoints/MeshToSDFGrid/MeshToVolume/ScaleElements/SplitEdges/SubdivideMesh/SubdivisionSurface/Triangulate + Prim Cone/Cube/Cylinder/Grid/IcoSphere/Circle/Line/UVSphere + Topo CornersOfEdge/CornersOfFace/CornersOfVertex/EdgesOfCorner/EdgesOfVertex/FaceOfCorner/OffsetCornerInFace/VertexOfCorner + UV PackIslands/UVTangent/Unwrap; Instance InstanceOnPoints/InstancesToPoints/RealizeInstances/RotateInstances/ScaleInstances/SetInstanceTransform/TranslateInstances/InstanceBounds/InstanceTransform/InstanceRotation/InstanceScale; Point DistributeInGrid/InVolume/OnFaces/Points/PointsToCurves/PointsToSDFGrid/PointsToVertices/PointsToVolume/SetPointRadius; Volume Read GetNamedGrid/GridInfo/VoxelIndex + Sample SampleGrid/SampleGridIndex/GridAdvect/GridCurl/GridDivergence/GridGradient/GridLaplacian + Write SetGridBackground/SetGridTransform/StoreNamedGrid + Ops GridToMesh/GridToPoints/VolumeToMesh/SDFGridBoolean/SDFGridFillet/SDFGridLaplacian/SDFGridMean/SDFGridMeanCurvature/SDFGridMedian/SDFGridOffset/FieldToGrid/GridClip/GridDilateAndErode/GridMean/GridMedian/GridPrune/GridVoxelize + Prim CubeGridTopology/VolumeCube; Sim SimulationZone; Color Blackbody/Gamma/ColorRamp/ColorMix/CombineColor/SeparateColor; Texture Brick/Checker/Gabor/Gradient/Image/Magic/Noise/Voronoi/Wave/WhiteNoise; Util BitMath/BooleanMath/IntegerMath/Clamp/Compare/FloatCurve/FloatToInteger/HashValue/MapRange/Math/Mix + Text FormatString/StringJoin/MatchString/ReplaceString/SliceString/FindInString/StringLength/StringToCurves/StringToValue/ValueToString/SpecialCharacters + Vector CombineXYZ/VectorMapRange/MixVector/SeparateXYZ/RadialTiling/VectorCurves/VectorMath/VectorRotate + Field AccumulateField/EvaluateAtIndex/EvaluateOnDomain/FieldAverage/FieldMinMax/FieldVariance + Rotation AlignRotationToVector/AxesToRotation/AxisAngleToRotation/EulerToRotation/InvertRotation/MixRotation/RotateRotation/RotateVector/RotationToAxisAngle/RotationToEuler/RotationToQuaternion/QuaternionToRotation + Matrix CombineMatrix/CombineTransform/Determinant/InvertMatrix/MatrixMultiply/MatrixSVD/ProjectPoint/SeparateMatrix/SeparateTransform/TransformDirection/TransformPoint/TransposeMatrix + Bundle CombineBundle/SeparateBundle/GetBundleItem/StoreBundleItem/JoinBundle + Closure ClosureZone/EvaluateClosure + List FieldToList/ListGetItem/ListLength + Flow ForEachElementZone/IndexSwitch/MenuSwitch/RandomValue/RepeatZone/Switch; Layout Frame/Reroute. Prefix `GeometryNode` (5.1: BoneInfo, StringToCurves fields incl Font socket, volume grid nodes, UV Unwrap MinimumStretch SLIM, MatrixSVD).

## Shader nodes (~95, `ShaderNode<Pascal>`)

```python
mat=bpy.data.materials.new("M"); mat.use_nodes=True; nt=mat.node_tree; nt.nodes.clear()
out=nt.nodes.new('ShaderNodeOutputMaterial'); bsdf=nt.nodes.new('ShaderNodeBsdfPrincipled')
obj.data.materials.append(mat)
# Mix: mix=n.new('ShaderNodeMix'); mix.data_type='RGBA'
# World: Background + TexEnvironment + OutputWorld
```
- Exceptions: `ShaderNodeNewGeometry`, `ShaderNodeVertexColor`, `ShaderNodeValToRGB` (ColorRamp), `ShaderNodeMix`+`data_type`.
- PBR: TexCoord→Mapping→ImageTexs→Principled→Output. Procedural: TexCoord→Noise/Voronoi/Wave→ColorRamp→Principled. Glass: TransmissionWeight 1, IOR 1.45–1.52 (EEVEE: ScreenSpaceRefraction on mat+render). Metal: Metallic 1 + tint. Skin: SubsurfaceWeight 0.3–1, Radius (1,0.2,0.1), RandomWalk for Cycles. Emission node for glow (EEVEE Bloom). Toon EEVEE: BSDF→ShaderToRGB→ColorRamp(Constant)→Output. Displacement: Tex→Displacement→Output.Displacement + `mat.cycles.displacement_method='BOTH'`. Volume: PrincipledVolume→Volume, or Absorption+Scatter→AddShader→Volume. 5.1 Raycast node (Position/Normal/Distance/Object/IsHit, Cycles); NormalMap OpenGL/DirectX toggle.
- Catalog: Input AmbientOcclusion/Attribute/Bevel/CameraData/Color/HairInfo/CurvesInfo/Fresnel/NewGeometry/LayerWeight/LightPath/ObjectInfo/ParticleInfo/PointInfo/RGB/Tangent/TexCoord/UVMap/Value/VertexColor/VolumeInfo/Wireframe/UVAlongStroke/Raycast; Output Material/Light/World/AOV/LineStyle; Shader BsdfPrincipled/BsdfDiffuse/BsdfGlossy/BsdfGlass/BsdfMetallic/BsdfRefraction/BsdfTranslucent/BsdfTransparent/BsdfSheen/SubsurfaceScattering/Emission/BsdfHair/BsdfHairPrincipled/BsdfToon/VolumeAbsorption/VolumeScatter/VolumePrincipled/VolumeCoefficients/BsdfRayPortal/MixShader/AddShader/Holdout/Background/EeveeSpecular; Texture TexImage/TexEnvironment/TexSky/TexNoise/TexVoronoi/TexWave/TexMagic/TexChecker/TexBrick/TexGradient/TexWhiteNoise/TexGabor/TexIES/TexPointDensity; Color Mix/ValToRGB/RGBCurve/Invert/HueSaturation/BrightContrast/Gamma/LightFalloff/ShaderToRGB/CombineColor/SeparateColor; Vector Bump/Displacement/VectorDisplacement/Normal/NormalMap/VectorTransform/VectorCurve/VectorMath/VectorRotate/Mapping/RadialTiling; Converter Math/CombineXYZ/SeparateXYZ/MapRange/FloatCurve/Clamp/RGBToBW/Blackbody/Wavelength/Mix.
- Debug: black = no Surface link / no UV; white = missing texture / wrong colorspace; EEVEE glass needs refraction + AlphaHashed/Blend; fireflies = bounces/clamp/denoise.

## Compositing

```python
sc=bpy.context.scene; sc.use_nodes=True; t=sc.node_tree; t.nodes.clear()
rl=t.nodes.new('CompositorNodeRLayers'); comp=t.nodes.new('CompositorNodeComposite')
dn=t.nodes.new('CompositorNodeDenoise')
t.links.new(rl.outputs['Image'],dn.inputs['Image']); t.links.new(dn.outputs['Image'],comp.inputs['Image'])
```
- Grade chain: RL→BrightContrast→ColorBalance→HueSat→Curves→Composite. Key: Clip→Keying→Dilate/Erode→Blur→SetAlpha→AlphaOver. Glare BLOOM/STREAKS/FOG_GLOW/GHOSTS. Vignette: EllipseMask→Blur→Mix Multiply. Grain: Mix Overlay 0.05–0.15. Mist: `use_pass_mist` + World mist → ColorRamp→Mix. DOF: prefer camera DOF; else RL+Z (`use_pass_z`)→Defocus.
- EXR: RL→OutputFile (OpenEXR Multilayer), add socket per pass. Cryptomatte: enable passes → Cryptomatte node → pick.
- Not running = `use_nodes` + PostProcessing compositing off. Black = RL→Composite link missing or nothing rendered.

## Python scripting / add-ons

- Operators need context: check before `bpy.ops`, use `poll`, `temp_override(active_object=, selected_objects=)` for background-safe calls, mode check/set + return to OBJECT. `--background` failures → rewrite with `bpy.data`. Handlers have no context → override or no ops. `view_layer.update()` after structural changes.
- Addon skeleton: `bl_info` (name/author/version/blender/location/description/category) + `Operator` (`bl_idname`, `bl_label`, `bl_options={'REGISTER','UNDO'}`, `execute` returns `{'FINISHED'}`) + `Panel` (`bl_space_type='VIEW_3D'`, `bl_region_type='UI'`) + symmetric `register()`/`unregister()`. Props: Bool/Int/Float/String/Enum/FloatVector/Pointer/Collection with subtypes (PIXEL/PERCENTAGE/FACTOR/ANGLE/TIME/DISTANCE/COLOR/FILE_PATH…).
- Batch: `bpy.ops.wm.open_mainfile` loop; CLI `blender --background scene.blend --python s.py -- args` (`sys.argv` after `--`).
- Handlers: `bpy.app.handlers.frame_change_pre/post, render_pre/post, load_post, save_pre` + `@persistent`; timers `bpy.app.timers.register(fn, first_interval)` return delay or None.
- Python 3.13 on Blender 5.1; `int|None` hints OK.

## Animation / rigging

- Organic → BEZIER; mechanical constant-speed → LINEAR; cartoon → BOUNCE/ELASTIC/BACK. Euler >180° flips → multiple keys or quaternions. Set `fps` BEFORE animating. `keyframe_insert('location', index=0/1/2)` for single axis.
- 360° spin: keys 1 (0°) / 120 (180°) / 240 (360°). Idle loop: ±2° sway 1→48→96 + `modifiers.new('CYCLES')` on all fcurves. Bounce landing: last key BOUNCE + EASE_OUT on Z.
- Shape keys: add 'Basis' first; edit key verts then EXIT edit mode to commit; animate `key.value` 0→1. Lip sync: 15-viseme set.
- Blender 5.x: no `action.fcurves` — walk layers→strips→channelbags→fcurves. 5.1: FCurve Smooth (Gaussian) modifier, `pose.apply_to_basis()`, layered actions.
- Armature: `armatures.new` + object + link → EDIT mode `edit_bones.new` (head/tail/parent/use_connect) → OBJECT. IK: POSE mode `constraints.new('INVERSE_KINEMATICS')`, target + `chain_count` + pole target/angle. FK/IK switch: drivers on influence from `obj["ik_fk_switch"]`.
- Driver: `driver_add("location",2)`, SCRIPTED, TRANSFORMS var WORLD_SPACE, expr `'src_x * 2'`. Drivers need Preferences → Editing → Allow Driver Python Expression.
- NLA: `animation_data_create()` → track → `strips.new(name,start,action)` → `action=None`. After push, NLA owns animation.
- Constraints (~45, `constraints.new('TYPE')`): MotionTracking CAMERA_SOLVER/FOLLOW_TRACK/OBJECT_SOLVER; Copy COPY_LOCATION/COPY_ROTATION/COPY_SCALE/COPY_TRANSFORMS; Limit LIMIT_DISTANCE/LIMIT_LOCATION/LIMIT_ROTATION/LIMIT_SCALE; MAINTAIN_VOLUME/TRANSFORM/TRANSFORM_CACHE; Track CLAMP_TO/DAMPED_TRACK/LOCKED_TRACK/STRETCH_TO/TRACK_TO; Rel ACTION/ARMATURE/CHILD_OF/FLOOR/FOLLOW_PATH/PIVOT/SHRINKWRAP; IK INVERSE_KINEMATICS/SPLINE_IK. Spaces WORLD/CUSTOM/POSE/LOCAL_WITH_PARENT/LOCAL/LOCAL_OWNER_ORIENT. FollowPath: target curve + `use_fixed_location` + `offset_factor` keys.

## Physics / simulation

- Rigid: `rigidbody.object_add(type='ACTIVE')` mass/friction/restitution, shape CONVEX_HULL (passthrough → MESH + substeps), margin 0.04, damping 0.04/0.1; floor PASSIVE MESH kinematic. World: `rigidbody.world_add()`, substeps 10, solver 10, split impulse. Constraints FIXED/POINT/HINGE/SLIDER/PISTON/GENERIC/GENERIC_SPRING/MOTOR + breaking threshold.
- Cloth: `modifier_add(type='CLOTH')` quality 5; presets mass/tension/bending/air — Silk .1/5/.05/1, Cotton .3/15/.5/1, Denim .5/40/10/1, Leather .5/80/150/1, Rubber .3/15/25/1. Pin via `vertex_group_mass`. Collision modifier on obstacles (thickness 0.02, friction 5) + self-collision. Explode → timescale/quality/intersections.
- Fluid domain: `modifier_add(type='FLUID')`, `fluid_type='DOMAIN'`, GAS/LIQUID, resolution 32–64 preview / 128–256 final + adaptive, cache REPLAY. Gas: noise/dissolve/burning/flame; liquid: mesh/spray/foam/bubble, water viscosity base 1 exp 6. Flow INFLOW/OUTFLOW/GEOMETRY (SMOKE/FIRE/BOTH/LIQUID); effector COLLISION/GUIDE. Bake data/noise/mesh/particles before render.
- Particles: `particle_system_add()`, EMITTER/HAIR, count/range/lifetime, emit FACE, physics NEWTON. Hair: length/step/root/tip + INTERPOLATED children. Render HALO/OBJECT/COLLECTION + instance.
- Force fields: FORCE/WIND/VORTEX/MAGNETIC/HARMONIC/CHARGE/LENNARDJ/TEXTURE/GUIDE/BOID/TURBULENCE/DRAG/SMOKE; strength, SPHERE falloff, max distance. Effector weights decide particle response.
- Soft body: mass 1, goal 0.7, pull/push 0.5, bending 0.1.
- Nondeterministic → set seed + bake (`ptcache.bake_all`).

## UV / texturing

- Image texture MUST have material nodes; viewport UV alone is nothing. Atlas: per-part regions only, never full atlas on every part. Alpha decals: `blend_method='BLEND'` + Alpha→BSDF Alpha, no black backing plane. GLB: Principled + Image Texture + UVs only.
- Front-projected UV: `(x-minx)/dx, (z-minz)/dz` over world X/Z bounds. Atlas remap: `uv=(u0+u*(u1-u0), v0+v*(v1-v0))`.
- Checker shows no stretch; supplementals (rough/bump/normal) must share the base UV layout or stay disconnected.

## Export

- Unknown target → GLB. Principled only. PNG ≤1024², no KTX2/Draco. Polycount: web ≤30k tris, hero web ≤60k, Unity/Unreal hero 50–100k, mobile ≤10k, AR USDZ ≤50k. GLB caps: hard 15MB, soft 8MB.
- Pre-export: apply location=False rotation=True scale=True; edit-mode select-all → normals consistent → remove_doubles 0.0001.
- GLB: `export_format='GLB', export_apply=True, export_materials='EXPORT', export_yup=True, export_animations=True, export_morph=True, export_normals=True`. Too big → Decimate COLLAPSE ratio 0.7, re-export.
- FBX: `apply_unit_scale=True, bake_space_transform=True, mesh_smooth_type='FACE', bake_anim=True (+all_bones/nla/all_actions/force_startend)`, `embed_textures=True, path_mode='COPY'`, `-Z forward, Y up`.
- STL: geometry only, must be manifold, no units, no color.
- USD: `.usdc` default, `.usdz` Apple AR, `use_instancing=True`.
- Rotated-90° = axis settings. 100× scale = unapplied transform. Missing anim = bake flags.

## Source-locked reconstruction (must-match-template work)

- Hierarchy: 1 front template, 2 texture atlas, 3 side/back/top (depth only, never alter front), 4 user feedback. Front X/Z locked; side→Y/Z depth; top→X/Y; back rear-only. Coordinate contract: front=X/Z, side=Y/Z, top=X/Y. Front rotation = `(0,angle,0)`, never Z-rotation.
- Preflight `reference_manifest.json`: sources, primary view, expected part count+labels, thresholds (front IoU ≥0.90 rigid / ≥0.82 mascot first pass, bbox center ≤12px @1024, size ≤3%, landmarks ≤2%).
- Chain: segment parts → register views → contour-to-mesh → atlas fit → materials/light (only after geo+UV pass) → validate → export (gates only) → animate (static accepted first).
- Validate on flat white-on-black silhouettes, not beauty renders. No export if count differs, IoU under threshold, or structural landmarks over tolerance. Contradictory views (side depth vs top depth) → stop, write conflict report, pick canonical policy (front_side / front_top / corrected sheets) — never average contradictions.
- Closed surfaces: front cap + back cap + sidewall each need real material/UV (curves/planes are accents, don't count). QA sheet: front, 45°, edge-on, back, opposite 45°.

## bpy safety rules (from LobeHub agent skill)

- Prefer `bpy.data` (RNA) over `bpy.ops` (operators need context, fail headless). Operators only for true tool actions with deliberately set mode/selection/active object, keyword args only, check `'FINISHED'` in return.
- Treat `bpy.context` as read-only and situational; verify active object, mode, view layer before context-sensitive work. Be explicit about mode changes (OBJECT for datablocks, EDIT_MESH for mesh ops).
- Modifiers/constraints/animation state → read via depsgraph evaluated data (`evaluated_get(depsgraph)`), not original datablocks.
- Link created objects into a collection or they don't exist in the scene. Version-tolerant: avoid undocumented behavior, isolate version-specific calls.
- Never bluff on uncertain API/version details — state the assumption, give the safest partial solution.

## Honest limits

Functionally correct, not art-directed: aesthetic refinement (silhouettes, curved backs, composed shapes) stays human. Human faces from primitives read as abstract avatars — use Poly Haven / Sketchfab / Hyper3D import, sculpt mode, or an artist. No sculpt-mode access via MCP. Thin-metal hero shots catch side streaks — top-down softbox or crop. Clean animation-ready topology needs retopo by hand. Spatial placement is approximate — expect correction rounds.

## Sources (all installed)

- `~/src/cc-blender-skill` — 30 skills + knowledge/ (16 domains) + docs. Individual: `~/.agents/skills/{text-to-blender,blender-modeling,blender-materials,blender-lighting,blender-cameras,blender-rendering,blender-animation,blender-export,blender-pro-workflow,blender-skill-harmonizer,quality-refinement-autoloop,blender-uv-texturing,wireframe-to-3d,reference-to-3d,…}` (30 total).
- `~/src/blender-claude-plugin` — 8 skills with full node/modifier/constraint catalogs: `~/.agents/skills/{blender-geometry-nodes,blender-shader-nodes,blender-compositing-nodes,blender-python-scripting,blender-animation-rigging,blender-modeling-modifiers,blender-physics-simulation,blender-scene-rendering}`.
- MCP server: `uvx --python 3.11 blender-mcp` (telemetry off), addon at `~/.config/blender/5.0/scripts/addons/blender_mcp.py`. Official Lab MCP needs Blender 5.1+ (we have 5.0.0) — revisit after upgrade.
- Papers/threads behind the loop: SceneCraft (arxiv 2403.01248, render→VLM-judge→refine + reusable skill library), 3D-Agent (LangGraph perceive→reason→act→verify, vision feedback = biggest gain), MindStudio MCP limits review.
