---
name: efficient-rendering
description: Use when building or speeding up visualization that renders 3D meshes, point clouds, skeletons/keypoints, or overlays onto video — especially offscreen/headless (EGL) rendering, differentiable rasterization in JAX, compositing renders over real camera footage, or anything that must align with a calibrated camera (intrinsics/extrinsics/distortion). Also use for the symptoms — "rendering is slow", "llvmpipe" / CPU GL fallback, "OffscreenRenderer slow", render is "upside-down" or "mirrored", overlay "doesn't line up with the video", blank/clipped renders, or an OOM in a rasterizer. Covers the OpenCV↔GL camera conventions, the two distortion strategies (undistort-the-image vs bake-distortion-into-vertices), GPU device probing and context reuse, chunked/checkpointed rasterizers, and the video-overlay pipeline. Pairs with the camera-model skill for the geometry API.
---

# Efficient Rendering

Performance and correctness patterns for rendering meshes, point clouds, and
overlays — offline batches and differentiable in-the-loop rendering alike. The
two recurring failure modes are (1) silently falling back to a CPU software GL
rasterizer (10–50× slower) and (2) renders that don't line up with the real
camera because a convention was dropped. Most of this skill is about avoiding
those two.

This skill is about *how to render fast and correctly*. For the camera math
itself (projection, triangulation, unit conventions), see the **camera-model**
skill — this one assumes you already have intrinsics `K`, an extrinsic
`world→camera` transform, and distortion coefficients.

---

## The golden rules

1. **Pin a real GPU for EGL before importing any GL library**, and verify you
   didn't land on `llvmpipe`. This is the single biggest win.
2. **Create the renderer/context once per resolution and reuse it** across every
   frame at that size. Context creation is ~60 ms (Mesa/EGL path); per-frame
   work should be single-digit ms.
3. **Pick one distortion strategy and apply it consistently** — either undistort
   the image and render with a pinhole, or keep the distorted image and bake
   distortion into the 3D vertices. Never half of each.
4. **Keep one coordinate convention end to end** (OpenCV: +X right, +Y down,
   +Z forward). Convert to GL exactly once, at the camera node.
5. **Composite only the dirty region** (mesh bounding box), not the whole frame.
6. **Precompute everything pose-independent once** (skinning weights, normals
   topology, projection matrices, undistort remaps, camera frusta/bounds).
7. **For JAX rasterizers, chunk pixels and `jax.checkpoint`** so peak memory is
   `chunk × primitives`, not `H·W × primitives`.

---

## 1. Headless GPU rendering with EGL

Offscreen rendering (no X server) goes through EGL. The trap: if the NVIDIA EGL
vendor library isn't selected, GL silently falls back to Mesa's `llvmpipe` CPU
rasterizer and everything still "works" — just 10–50× slower.

**Set the platform before importing OpenGL/pyrender/anything that pulls in GL:**

```python
import os
os.environ.setdefault("PYOPENGL_PLATFORM", "egl")  # MUST precede any GL import
# only now:
import pyrender
```

**Pin a GPU — but do not assume the EGL device index equals the CUDA index.**
EGL device order does *not* match `nvidia-smi` / `CUDA_VISIBLE_DEVICES` order,
and there is no reliable EGL→card mapping. So don't set `EGL_DEVICE_ID` to a
CUDA index and trust it — that's the classic way to land on the wrong card or on
`llvmpipe`. Instead **enumerate EGL devices, build a throwaway context on each,
read `GL_RENDERER`, and pick a hardware GPU** (rank by free memory from
`nvidia-smi` if you want the emptiest one):

```python
from OpenGL import EGL
devices = EGL.eglQueryDevicesEXT(...)        # enumerate
for d in devices:
    # create a context on `d`, read GL_RENDERER, keep the first non-llvmpipe one
    ...
os.environ["EGL_DEVICE_ID"] = str(chosen_egl_index)  # only after probing/verifying
# If GLVND can't find the NVIDIA ICD, point it at the vendor JSON:
#   os.environ["__EGL_VENDOR_LIBRARY_FILENAMES"] = "/path/to/10_nvidia.json"
```

If you must honor a pre-set `EGL_DEVICE_ID`, still validate it resolves to real
hardware (the `GL_RENDERER` assert below) rather than trusting the number.

**Always verify you got the GPU, not the CPU fallback.** Do this once at startup
and fail loudly:

```python
r = pyrender.OffscreenRenderer(W, H)
import OpenGL.GL as gl
renderer_str = gl.glGetString(gl.GL_RENDERER).decode()
assert "llvmpipe" not in renderer_str.lower(), f"CPU GL fallback: {renderer_str}"
```

Typical impact at ~2K resolution / ~18k-vertex mesh: `llvmpipe` ≈ 800 ms/frame,
NVIDIA EGL ≈ 15 ms/frame.

**One process, one context.** EGL contexts cannot be shared across processes.
If you parallelize across processes, each worker needs its own context (and
must not have CUDA/JAX forked into it — use `multiprocessing.get_context("spawn")`,
never `fork`, once CUDA is initialized). For most workloads a single process
with a reused context beats multiprocessing.

---

## 2. Reuse the GL context and scene

Allocate the `OffscreenRenderer` (plus Scene, camera node, lights) once per
viewport size and cache it. Re-pose the geometry each frame; never reallocate
the renderer.

```python
_RENDER_CACHE: dict[tuple[int, int], dict] = {}

def get_context(h: int, w: int) -> dict:
    key = (int(h), int(w))
    if key not in _RENDER_CACHE:
        renderer = pyrender.OffscreenRenderer(viewport_width=w, viewport_height=h)
        scene = pyrender.Scene(bg_color=[0, 0, 0, 0])  # transparent for compositing
        _RENDER_CACHE[key] = {"renderer": renderer, "scene": scene}
    return _RENDER_CACHE[key]

import atexit
atexit.register(lambda: [c["renderer"].delete() for c in _RENDER_CACHE.values()])
```

The cached Scene, camera, and lights persist; only the mesh churns. Add the
posed mesh, render, then remove its node in a `finally` so the next frame starts
clean without rebuilding the scene:

```python
node = ctx["scene"].add(mesh)
try:
    color, depth = ctx["renderer"].render(ctx["scene"], flags=pyrender.RenderFlags.RGBA)
finally:
    ctx["scene"].remove_node(node)
```

Keep video captures open too — a `VideoCapture` held across frames reads
sequentially in O(1); reopening or seeking per frame is a large hidden cost.

---

## 3. Camera handling for rendering

Getting the render to land on the right pixels is mostly about three
conversions: OpenCV→GL axis flip, intrinsics→projection, and a single decision
about distortion.

### 3a. OpenCV → GL axis convention

OpenCV cameras look down **+Z** with **+Y down**; OpenGL cameras look down
**−Z** with **+Y up**. The camera *pose* (camera→world) for a GL renderer is the
inverse of your `world→camera` extrinsic, post-multiplied by a flip:

```python
GL_FLIP = np.diag([1.0, -1.0, -1.0, 1.0])   # OpenCV -> OpenGL
cam_pose = np.linalg.inv(extrinsic_w2c) @ GL_FLIP   # what pyrender wants
```

Apply this flip in exactly one place. If your overlay is upside-down or
mirrored, this is almost always the culprit — don't compensate elsewhere.

### 3b. Intrinsics → projection

Use an intrinsics camera directly rather than hand-rolling a projection matrix;
it handles the principal-point offset correctly:

```python
camera = pyrender.IntrinsicsCamera(fx=fx, fy=fy, cx=cx, cy=cy,
                                   znear=0.05, zfar=100.0)
```

Set `znear`/`zfar` to bracket your actual scene depth — too wide wastes z-buffer
precision (z-fighting), too tight clips geometry. For a self-contained object,
deriving the frustum from the vertex bounds once per sequence (not per frame)
both fixes clipping and avoids recomputation.

**Watch your units against the frustum.** A `zfar` that's fine in meters will
clip the whole subject to a blank frame if the mesh is in centimeters — keep
`znear`/`zfar`/`depth_tolerance` in the same unit as your geometry.

For a canonical "look at the object" view (no real camera), an orthographic
camera sized to the vertex extent is robust: set `xmag = ymag = extent`, stand
the camera off at `center.z + extent·3`, and `zfar = extent·10` so the standoff
plus body depth always fits. A fixed small `zfar` here is the usual cause of a
blank render.

When projecting points yourself, use the OpenCV pinhole with a safe-z guard and
**pixel centers** (the 0.5 offset matters for alignment with sampled images):

```python
z = jnp.maximum(verts_cam[:, 2], 1e-3)
u = fx * verts_cam[:, 0] / z + cx
v = fy * verts_cam[:, 1] / z + cy
# pixel grid for sampling: xs + 0.5, ys + 0.5
```

### 3c. Distortion — pick ONE of two strategies

Real lenses have radial/tangential distortion. There are two correct ways to
make a render line up with a distorted photo; mixing them produces a subtle,
maddening misalignment near the image edges.

**Strategy A — undistort the image (preferred when you control the footage).**
Undistort the video frame once, then render and project with a plain pinhole.
Use the *original* `K` as the new camera matrix so the projection model is
unchanged (do **not** use `getOptimalNewCameraMatrix`, which shifts the image
plane and breaks alignment with your `K`):

```python
map1, map2 = cv2.initUndistortRectifyMap(K, dist, np.eye(3), K, (w, h), cv2.CV_32FC1)
# precompute once; reuse for every frame:
frame_undist = cv2.remap(frame, map1, map2, cv2.INTER_LINEAR)
# now render + project with plain pinhole K, no distortion anywhere
```

Likewise undistort 2D keypoints before unprojecting/triangulating. This keeps
all 3D math pinhole-simple and is the right call for differentiable rendering.

**Strategy B — bake distortion into the vertices (when you must keep the
original image).** Transform the 3D vertices in camera space into the
"pre-distorted" positions that, under an ideal pinhole, land where the real lens
would put them. Then render with a plain pinhole onto the *untouched* distorted
image:

```python
verts_distorted_cam = distort_3d(camera_params, cam_idx, verts_cam_mm)  # see camera-model
# render with pinhole K, identity extrinsic, over the original distorted frame
```

Use B when the deliverable must overlay the raw footage (e.g. you can't ship
undistorted video) or distortion is strong. Use A everywhere else — it's
simpler and differentiable. Whichever you choose, apply it to *both* the image
and the geometry, never one without the other.

---

## 4. Mesh rendering

- **Skip geometry validation** when you trust your topology: `trimesh.Trimesh(v,
  f, process=False)` avoids a surprisingly expensive cleanup pass per frame.
- **Batch all meshes into one scene** before a single `render()` so the shared
  z-buffer resolves inter-mesh occlusion correctly in one pass — don't render
  bodies separately and composite, or near/far occlusion will be wrong.
- **Materials:** `MetallicRoughnessMaterial(metallicFactor=0, roughnessFactor≈0.7)`
  with modest ambient (~0.35) and a camera-mounted directional light reads well
  for anatomy/body meshes. Render `RGBA` so you get an alpha mask for free.
- **Per-vertex color / heatmaps:** render with the `FLAT` flag to skip lighting
  so the raw vertex colors survive (error maps, region labels, confidence).
- **Translucent over opaque:** for a skin shell over bones, render bones
  `OPAQUE` and skin `BLEND` with `SKIP_CULL_FACES` so the back of the
  semi-transparent shell isn't culled.
- **Backface culling** for a single closed opaque shell: drop faces whose normal
  points away from the camera (`n · view_dir ≥ 0`) — fewer triangles, identical
  result.
- **Layered translucency, exactly:** rasterize each layer *opaquely* (its own
  z-buffer fixes self-occlusion) and composite back-to-front in numpy
  (painter's order). More predictable than GL depth-sorted blending.
- **Precompute skinning once.** Nearest-vertex skin weights/indices depend only
  on the template geometry, not the pose — compute once, reuse every frame.
  Skinning is often the dominant per-frame cost otherwise.

---

## 5. Point clouds and points "inside" a mesh

Rendering markers/points that may be occluded by (or embedded within) a body
mesh needs real depth reasoning, not just `cv2.circle` at projected locations.

**Cheap occlusion via a coarse z-buffer.** Project all points, bucket them into
a coarse pixel grid, take the per-bucket nearest depth with `segment_min`, and
flag a point visible only if it's within a depth tolerance (~3 cm) of its
bucket's front. Avoids a full per-pixel depth compare and is fully vectorized:

```python
bu = jnp.clip(jnp.floor(u * scale).astype(jnp.int32), 0, Wb - 1)
bv = jnp.clip(jnp.floor(v * scale).astype(jnp.int32), 0, Hb - 1)
bucket = bv * Wb + bu
bucket_min = jax.ops.segment_min(jnp.where(candidate, z, 1e6), bucket, num_segments=Hb*Wb)
visible = z <= bucket_min[bucket] + depth_tolerance
```

**Differentiable point/soft rendering (SoftRas-style).** Per pixel, take a
depth-aware softmax over nearby points/vertices:
`w ∝ exp(-‖pix − proj‖² / 2σ²) · exp(−z / depth_temp)`, normalized with
`logsumexp` for stability. The alpha channel is the max spatial weight. This is
what lets a renderer pass gradients back to 3D positions.

**Keep peak memory bounded with chunking + remat.** The naive weight matrix is
`(H·W, V)` — multiple GiB. Tile pixels into chunks and recompute each chunk's
weights in the backward pass instead of storing them:

```python
@jax.checkpoint
def render_chunk(pix_chunk):           # (C, 2)
    d2 = jnp.sum((pix_chunk[:, None] - proj[None])**2, -1)      # (C, V)
    logit = jnp.where(vis[None], -d2/(2*sigma**2) - z[None]/depth_temp, -1e30)
    w = jnp.exp(logit - jax.scipy.special.logsumexp(logit, -1, keepdims=True))
    return w @ vertex_attr             # (C, attr)

img = jax.lax.map(render_chunk, pix.reshape(n_chunks, C, 2))
```

`256² × 18k` verts drops from ~4.5 GiB to a few hundred MiB. The `@jax.checkpoint`
is load-bearing: without it the enclosing `scan`/`map` stores every chunk's
intermediate weight matrix on the autodiff tape, which defeats the chunking.
Pick the chunk size to divide `H·W` evenly and mark `H, W, chunk` as static JIT
args (one compile per resolution).

**Hard triangle rasterization, differentiable where it counts.** When you need
crisp coverage: compute barycentrics for every face per pixel, z-buffer to pick
the nearest covering face (`argmin` over depth). Make the *face id and coverage*
`stop_gradient` (a hard mask shouldn't leak gradient), but let the **barycentric
coordinates and depth flow gradients** to the vertex positions. Same
chunk-and-checkpoint trick for memory.

**Vertex normals, vectorized:** accumulate (area-weighted) face normals onto
vertices with `segment_sum` over the flattened face index — no Python loop:

```python
fn = jnp.cross(v1 - v0, v2 - v0)                      # (F,3), |fn| = 2·area
vn = jax.ops.segment_sum(jnp.repeat(fn, 3, 0), faces.reshape(-1), num_segments=V)
vn = vn / jnp.maximum(jnp.linalg.norm(vn, axis=-1, keepdims=True), 1e-8)
```

---

## 6. 2D overlays: keypoints, skeletons, trails

- **Project once in camera frame**, rescale to the output resolution, then draw.
  Vectorize the projection across frames/cameras with `jax.vmap` rather than a
  Python loop.
- **Encode visibility in the marker, not just position:** filled circle + white
  halo for visible, a dim hollow ring for occluded/low-confidence. Skip NaN /
  out-of-bounds points.
- **Comet-tail trails** via accumulated alpha blends — width and alpha ramp from
  tail to head:

  ```python
  for seg in range(t0 + 1, t + 1):
      frac = (seg - t0) / max(t - t0, 1)
      cv2.line(overlay, p0, p1, color, thickness=max(1, int(1 + (w_max-1)*frac)))
      cv2.addWeighted(overlay, 0.15 + 0.85*frac, img, 1 - (0.15 + 0.85*frac), 0, img)
  ```

- **Crisp small markers:** upscale the frame 2–4×, draw markers at scaled
  coordinates, downscale the final video. Cheaper and sharper than antialiasing
  every primitive.
- **Smooth playback:** interpolate tracks onto a denser time grid and repeat the
  nearest source frame, so markers glide while video steps.

---

## 7. Video overlay pipeline

- **Composite only the bounding box** of the render's alpha mask. For sparse
  overlays this is most of the speedup:

  ```python
  ys, xs = np.where(mask)
  y0, y1, x0, x1 = ys.min(), ys.max()+1, xs.min(), xs.max()+1
  a = (mask[y0:y1, x0:x1, None] * alpha)
  out[y0:y1, x0:x1] = (rgb[y0:y1, x0:x1] * a + frame[y0:y1, x0:x1] * (1 - a))
  ```

  Integer (uint16) intermediates with a `// 255` divide avoid a full float32
  round-trip of the whole frame.
- **Prefer piping raw frames to `ffmpeg`** over `cv2.VideoWriter` for H.264:
  more reliable codecs, faster, and you control pixel format. Use `yuv420p` +
  `-movflags +faststart` for browser-playable output.

  ```python
  proc = subprocess.Popen([ffmpeg, "-f","rawvideo","-pix_fmt","bgr24",
      "-s",f"{w}x{h}","-r",str(fps),"-i","-","-an","-c:v","libx264",
      "-crf","18","-pix_fmt","yuv420p","-movflags","+faststart", out_path],
      stdin=subprocess.PIPE)   # -an: no audio, -crf 18: visually lossless
  for f in frames_bgr:
      proc.stdin.write(np.ascontiguousarray(f).tobytes())
  ```

  If you must use `cv2.VideoWriter` (`mp4v`), a best-effort `ffmpeg` re-encode to
  H.264 afterward makes it streamable.

---

## 8. JAX-specific performance

- **One JIT boundary for FK + mesh extraction.** Wrap forward kinematics and
  world-space vertex extraction in a single `jax.jit` so it all runs on device;
  crossing the host boundary between them costs ~100 ms of dispatch.
- **Vectorize vertex extraction** — gather per-vertex transforms and `einsum`
  instead of a Python loop. Vectorizing alone (numpy) takes a body mesh from
  ~275 ms to ~2 ms; the same `einsum` jitted on-device is sub-millisecond:

  ```python
  world = xpos[v2g] + jnp.einsum("vij,vj->vi", xmat[v2g].reshape(-1,3,3), local_vert)
  ```
- **`vmap` for multi-instance**, padding to a fixed count so shapes stay stable
  and you compile once. Carry a validity mask rather than slicing.
- **Cache compiled functions by instance id** when the static model object can't
  be a JIT argument, and `stop_gradient` static models inside the jitted fn.
- **Donate buffers** in the training/render step (`eqx.filter_jit(donate=...)`)
  to free large inputs immediately.
- **Static-arg the resolution/chunk size**; accept one compile per resolution.

See the **jax-memory-and-retracing** skill for diagnosing OOMs and unexpected
recompiles.

---

## Pre-flight checklist

- [ ] `PYOPENGL_PLATFORM=egl` set **before** any GL import.
- [ ] Verified `GL_RENDERER` is the NVIDIA GPU, not `llvmpipe`.
- [ ] Renderer/context allocated once and reused; cleaned up at exit.
- [ ] Exactly one OpenCV→GL flip, at the camera node.
- [ ] `znear`/`zfar` bracket the real scene depth (no z-fighting, no clipping).
- [ ] One distortion strategy, applied to both image and geometry.
- [ ] Pose-independent work (skinning, normals topology, remaps, frusta,
      projection matrices) precomputed once.
- [ ] Compositing restricted to the mask bounding box.
- [ ] JAX rasterizer chunks pixels + `jax.checkpoint`; statics are resolution/chunk.
- [ ] Output encoded `yuv420p` + faststart if it needs to play in a browser.

## Anti-patterns

| Anti-pattern | Fix |
|---|---|
| Importing GL before setting `PYOPENGL_PLATFORM` | Set the env var first, at the very top |
| Trusting it "works" without checking `GL_RENDERER` | Assert no `llvmpipe` at startup |
| New `OffscreenRenderer` per frame | Cache by viewport size, reuse |
| Distorting vertices *and* undistorting the image | Pick one strategy, apply consistently |
| `getOptimalNewCameraMatrix` as the undistort target | Keep the original `K` as the new matrix |
| Compensating an upside-down render downstream | Fix the single OpenCV→GL flip instead |
| Materializing `(H·W, primitives)` in a JAX rasterizer | Chunk pixels + `jax.checkpoint` |
| Recomputing skinning/normals/frusta every frame | Precompute once per sequence |
| Compositing the whole frame for a small overlay | Restrict to the mask bbox |
| `cv2.VideoWriter` mp4v for a deliverable | Pipe raw frames to `ffmpeg` H.264/yuv420p |
| `fork` for render workers after CUDA init | `multiprocessing.get_context("spawn")` |
