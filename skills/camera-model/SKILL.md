---
name: camera-model
description: Use when working with camera projections, intrinsics, extrinsics, triangulation, reprojection, coordinate transforms between world/camera frames, or any code that touches camera_params dicts. Covers unit conventions (mm vs meters), the OpenCV world-to-camera extrinsic convention, and the required API functions from camera.py and camera_adapter.py.
---

# Camera Model Reference

## Overview

Our camera system is implemented in JAX and follows OpenCV conventions. There are two layers:

1. **Core library** (`multi_camera.analysis.camera`) - Low-level functions operating in **millimeters**
2. **Camera adapter** (`multiview_biomechanical_pose.geometry.camera_adapter`) - High-level functions accepting/returning **meters**

**Source files:**
- `MultiCameraTracking/multi_camera/analysis/camera.py` - Core camera functions
- `MultiviewBiomechanicalPose/multiview_biomechanical_pose/geometry/camera_adapter.py` - Meter-safe wrappers

---

## Camera Parameters Dict

All camera functions expect a single dict with parameters for ALL cameras:

```python
camera_params = {
    "mtx":  array,  # (num_cameras, 4)  - [fx, fy, cx, cy] stored at 1/1000 scale
    "rvec": array,  # (num_cameras, 3)  - Rodrigues rotation vectors (dimensionless)
    "tvec": array,  # (num_cameras, 3)  - Translation vectors in METERS (stored at 1/1000 scale)
    "dist": array,  # (num_cameras, 5+) - Distortion coefficients [k1, k2, p1, p2, k3, ...]
}
```

The `mtx` and `tvec` fields are stored at **1/1000 scale** (effectively meters). The library functions `get_intrinsic()` and `get_extrinsic()` multiply by 1000 internally to produce pixel-scale intrinsics and mm-scale extrinsics.

**TFRecord format** uses plural names (`camera_intrinsics`, `camera_rvecs`, `camera_tvecs`, `camera_distortion`) which the dataset pipeline converts to singular names automatically.

---

## Unit Conventions (CRITICAL)

| Context | Units | Notes |
|---------|-------|-------|
| 3D points throughout the system | **meters** | World coords, camera coords, joint positions |
| `camera_params["tvec"]` storage | **meters** (1/1000 scale) | Scaled up by 1000 inside `get_extrinsic()` |
| `camera_params["mtx"]` storage | **1/1000 of pixels** | Scaled up by 1000 inside `get_intrinsic()` |
| `get_extrinsic()` returns | 4x4 matrix in **mm** | Translation component is in millimeters |
| `get_intrinsic()` returns | 3x3 K matrix in **pixels** | fx, fy, cx, cy in pixel units |
| `project_distortion()` input | 3D points in **mm** | You MUST multiply meters by 1000 |
| `project_distortion()` output | 2D points in **pixels** | |
| `triangulate_point()` input | 2D points in **pixels** | With optional confidence channel |
| `triangulate_point()` output | 3D points in **mm** | Divide by 1000 to get meters |
| `camera_adapter` functions | **meters** in/out | Handle mm conversion internally |
| 2D keypoints | **pixels** | Original image resolution |

### The Conversion Rule

When calling core library functions directly, always convert:
```python
# Meters -> mm before projection
points_2d = cam_lib.project_distortion(camera_params, cam_idx, points_3d_m * 1000.0)

# mm -> meters after triangulation
points_3d_m = triangulate_point(camera_params, points_2d) / 1000.0
```

When using `camera_adapter` functions, no conversion is needed - they handle it internally.

---

## OpenCV Extrinsic Convention

Our camera model follows the **OpenCV world-to-camera** convention:

```
P_camera = E @ P_world
```

- `get_extrinsic()` returns a **4x4 SE(3) matrix** that transforms points FROM world coordinates TO camera coordinates
- This is **NOT** the camera position in world space
- The camera position in world space would be `-R^T @ t` (or `E_inv[:3, 3]`)
- Rotation is stored as Rodrigues vectors, converted via `SO3.exp(rvec)`
- Uses `jaxlie` SE3/SO3 for all rigid body transformations

```python
# get_extrinsic returns world-to-camera transform (units: mm)
E = get_extrinsic(camera_params, i)  # 4x4 matrix

# To get camera position in world (in mm):
camera_pos_mm = jnp.linalg.inv(E)[:3, 3]

# To get camera position in meters:
camera_pos_m = camera_pos_mm / 1000.0
```

### COLMAP Conversion Warning

COLMAP stores camera-to-world transforms. When converting from COLMAP:
```python
R_w2c = R_c2w.T
t_w2c = -R_w2c @ t_colmap
```

---

## Core Library Functions (`multi_camera.analysis.camera`)

All core functions operate in **millimeters**. Import as:

```python
from multi_camera.analysis import camera as cam_lib
from multi_camera.analysis.camera import get_intrinsic, get_extrinsic
```

### `get_intrinsic(camera_params, i)` -> 3x3 K matrix

Returns the intrinsic matrix with focal lengths and principal point in **pixel units**:
```python
K = get_intrinsic(camera_params, 0)
# [[fx,  0, cx],
#  [ 0, fy, cy],
#  [ 0,  0,  1]]
```

### `get_extrinsic(camera_params, i)` -> 4x4 SE(3) matrix

Returns the **world-to-camera** transformation matrix in **millimeters**:
```python
E = get_extrinsic(camera_params, 0)
# 4x4 homogeneous transform [R|t; 0 0 0 1]
# t is in MILLIMETERS
# This is NOT the camera position - it's a world-to-camera transform
```

### `get_projection(camera_params, i)` -> 3x4 projection matrix

Returns `K @ E[:3]` - the full 3x4 projection matrix:
```python
P = get_projection(camera_params, 0)  # 3x4
```

### `project_distortion(camera_params, i, points)` -> 2D pixels

Projects 3D points to 2D image coordinates with radial distortion:
```python
# CRITICAL: points must be in MILLIMETERS
points_2d = cam_lib.project_distortion(camera_params, cam_idx, points_3d_m * 1000.0)
```

Currently uses simplified radial model (k1 only). Handles behind-camera points by shrinking them toward image center.

### `undistort_points(points, K, dist, num_iters=5)` -> undistorted 2D

Iteratively removes lens distortion from 2D image points. Supports full OpenCV model (k1-k6, p1-p2, s1-s4, tau_x, tau_y):
```python
undistorted = cam_lib.undistort_points(
    points_2d[None, ...],   # (1, N, 2) - needs batch dim
    K[None, ...],           # (1, 3, 3)
    dist_coeffs[None, :],   # (1, n_coeffs)
)[0]                        # remove batch dim
```

### `distort_3d(camera_params, i, points)` -> distorted 3D in camera coords

Computes equivalent 3D camera-frame points that would project to the same 2D coordinates under an ideal pinhole camera. Used for rendering 3D models (e.g., SMPL) on distorted images:
```python
# points in mm, returns camera-frame coords in mm
vertices_distorted = cam_lib.distort_3d(camera_params, i, vertices_mm)
```

Uses full radial+tangential model (k1, k2, k3, p1, p2).

### `triangulate_point(camera_params, points2d, return_confidence=False)` -> 3D mm

DLT triangulation from multiple 2D observations. Handles undistortion internally:
```python
# points2d: (num_cameras, T, J, 3) with [u, v, confidence]
# Returns: (T, J, 3) or (T, J, 4) with confidence, in MILLIMETERS
points_3d_mm = cam_lib.triangulate_point(camera_params, points2d, return_confidence=True)
points_3d_m = points_3d_mm[..., :3] / 1000.0
```

### `robust_triangulate_points(camera_params, points2d, sigma=150, threshold=0.5)` -> 3D mm

Robust triangulation using geometric median of pairwise triangulations (Roy et al. 2022). Automatically weights cameras by agreement:
```python
points_3d, camera_weights = cam_lib.robust_triangulate_points(
    camera_params, points2d, return_weights=True
)
# points_3d: (T, J, 4) in mm
# camera_weights: (num_cameras, T, J)
```

### `reprojection_error(camera_params, points2d, points3d)` -> residual in pixels

Computes difference between observed and projected 2D points:
```python
# points3d must be in mm (same space as projection)
residual = cam_lib.reprojection_error(camera_params, points2d, points3d_mm)
```

---

## Camera Adapter Functions (Meter-Safe API)

These functions accept and return **meters**. Prefer these over direct core library calls when possible.

```python
from multiview_biomechanical_pose.geometry.camera_adapter import (
    transform_points_world_to_camera,
    transform_points_camera_to_world,
    transform_points_between_cameras,
    project_camera_coordinates,
    unproject_from_image_with_distortion,
    unproject_and_transform_to_world,
    transform_pose_se3_world_to_camera,
    transform_pose_se3_camera_to_world,
    compute_relative_extrinsics,
)
```

### Point Transformations

```python
# World -> Camera (meters in, meters out)
pts_cam = transform_points_world_to_camera(pts_world_m, camera_params, cam_idx)

# Camera -> World (meters in, meters out)
pts_world = transform_points_camera_to_world(pts_cam_m, camera_params, cam_idx)

# Camera A -> Camera B (meters in, meters out)
pts_target = transform_points_between_cameras(pts_source_m, camera_params, source_idx, target_idx)
```

### Projection from Camera Coordinates

```python
# Projects points already in camera frame to 2D (meters in, pixels out)
pts_2d = project_camera_coordinates(pts_cam_m, camera_params, cam_idx)
```

Uses identity extrinsics internally to avoid double-transformation.

### Unprojection

```python
# 2D pixels + depth -> 3D camera coords (pixels+meters in, meters out)
pts_cam = unproject_from_image_with_distortion(pts_2d, depth_m, camera_params, cam_idx)

# 2D pixels + depth -> 3D world coords (pixels+meters in, meters out)
pt_world = unproject_and_transform_to_world(image_point, depth_m, camera_params, cam_idx)
```

### SE(3) Pose Transformations

```python
# Transform full pose (position + quaternion) between frames
pos_cam, quat_cam = transform_pose_se3_world_to_camera(pos_world_m, quat_wxyz, camera_params, cam_idx)
pos_world, quat_world = transform_pose_se3_camera_to_world(pos_cam_m, quat_wxyz, camera_params, cam_idx)
```

Quaternions use **wxyz** format (jaxlie convention).

---

## Common Workflows

### Project 3D Skeleton to Image

```python
from multi_camera.analysis import camera as cam_lib

# joints_3d: (T, J, 3) in meters
# Project to camera i
joints_2d = cam_lib.project_distortion(camera_params, i, joints_3d * 1000.0)
# joints_2d: (T, J, 2) in pixels
```

### Triangulate from Multi-View 2D Keypoints

```python
# keypoints_2d: (num_cameras, T, J, 3) with [u, v, confidence]
points_3d = cam_lib.triangulate_point(camera_params, keypoints_2d, return_confidence=True)
# points_3d: (T, J, 4) in mm - convert to meters:
points_3d_m = points_3d[..., :3] / 1000.0
confidence = points_3d[..., 3]
```

### Render SMPL Mesh on Distorted Image

```python
from multi_camera.analysis.camera import get_intrinsic, distort_3d

# vertices: (N, 3) in meters
K = np.array(get_intrinsic(camera_params, i))
vertices_distorted_mm = np.array(distort_3d(camera_params, i, vertices * 1000.0))
vertices_distorted_m = vertices_distorted_mm / 1000.0

# Render with ideal pinhole (K, identity R/T) since distortion is baked into 3D
```

### Compute Reprojection Error

```python
from multi_camera.analysis.fit_quality import reprojection_quality

# keypoints3d: (T, J, 3) in mm
# keypoints2d: (N_cams, T, J, 3) with [u, v, confidence]
metrics = reprojection_quality(keypoints3d_mm, camera_params, keypoints2d)
```

### Convert Between Aniposelib and Our Format

```python
# Aniposelib -> our format (mm -> meter storage)
from aniposelib.cameras import CameraGroup
cgroup = CameraGroup.from_names(cam_names)
cam_dicts = cgroup.get_dicts()
camera_params = {
    "mtx": np.array([[c["matrix"][0][0], c["matrix"][1][1],
                       c["matrix"][0][2], c["matrix"][1][2]]
                      for c in cam_dicts]) / 1000.0,
    "dist": np.array([c["distortions"] for c in cam_dicts]),
    "rvec": np.array([c["rotation"] for c in cam_dicts]),
    "tvec": np.array([c["translation"] for c in cam_dicts]) / 1000.0,
}

# Our format -> Aniposelib (meter storage -> mm)
from aniposelib.cameras import Camera, CameraGroup
cameras = []
for i, name in enumerate(cam_names):
    K = np.array([[params["mtx"][i,0]*1000, 0, params["mtx"][i,2]*1000],
                  [0, params["mtx"][i,1]*1000, params["mtx"][i,3]*1000],
                  [0, 0, 1]])
    cam = Camera(name=name, matrix=K, dist=params["dist"][i],
                 rvec=params["rvec"][i], tvec=params["tvec"][i]*1000)
    cameras.append(cam)
cgroup = CameraGroup(cameras)
```

---

## Distortion Model

Our cameras use the **OpenCV radial-tangential** distortion model:

- **Projection** (`project_distortion`): Simplified model using k1 only (tangential terms commented out)
- **Unprojection** (`undistort_points`): Full model with k1-k6, p1-p2, s1-s4, tau
- **3D distortion** (`distort_3d`): Full model with k1, k2, k3, p1, p2

Distortion coefficients are stored in OpenCV order: `[k1, k2, p1, p2, k3, ...]`

For EgoHumans data: images are pre-undistorted and distortion is set to `[0, 0, 0, 0, 0]`.

---

## Anti-Patterns (NEVER DO THESE)

### 1. Never manually access camera parameter arrays

```python
# WRONG - bypasses scaling and formatting
fx = camera_params["mtx"][0, 0]
R = cv2.Rodrigues(camera_params["rvec"][0])[0]
t = camera_params["tvec"][0]
```

```python
# CORRECT - use library functions
K = get_intrinsic(camera_params, 0)        # Properly scaled 3x3
E = get_extrinsic(camera_params, 0)        # Properly scaled 4x4 SE(3)
```

### 2. Never create single-camera parameter dicts

```python
# WRONG - breaks the API contract
cam0_params = {
    "mtx": camera_params["mtx"][0:1],
    "rvec": camera_params["rvec"][0:1],
    "tvec": camera_params["tvec"][0:1],
    "dist": camera_params["dist"][0:1],
}
```

```python
# CORRECT - pass full dict with camera index
result = cam_lib.project_distortion(camera_params, 0, points)
```

### 3. Never forget the mm conversion for core library functions

```python
# WRONG - passing meters to mm-expecting function
projected = cam_lib.project_distortion(camera_params, i, points_3d_m)
```

```python
# CORRECT
projected = cam_lib.project_distortion(camera_params, i, points_3d_m * 1000.0)
```

### 4. Never reimplement geometric transforms

```python
# WRONG - manual projection ignoring distortion
x_2d = fx * (x_3d / z_3d) + cx
y_2d = fy * (y_3d / z_3d) + cy
```

```python
# CORRECT - use library with distortion
from multiview_biomechanical_pose.geometry.camera_adapter import project_camera_coordinates
pts_2d = project_camera_coordinates(pts_cam_m, camera_params, cam_idx)
```

### 5. Never manually unproject without distortion correction

```python
# WRONG - ignores lens distortion
x_3d = (x_2d - cx) * depth / fx
```

```python
# CORRECT
from multiview_biomechanical_pose.geometry.camera_adapter import unproject_from_image_with_distortion
pts_3d = unproject_from_image_with_distortion(pts_2d, depth_m, camera_params, cam_idx)
```

### 6. Never confuse extrinsic matrix with camera position

```python
# WRONG - treating tvec as camera position in world
camera_position = camera_params["tvec"][i]
```

```python
# CORRECT - extrinsic is world-to-camera, invert to get camera position
E = get_extrinsic(camera_params, i)
camera_pos_mm = jnp.linalg.inv(E)[:3, 3]
camera_pos_m = camera_pos_mm / 1000.0
```

---

## Quick Reference: Import Paths

```python
# Core camera library
from multi_camera.analysis import camera as cam_lib
from multi_camera.analysis.camera import (
    get_intrinsic,          # camera_params, i -> 3x3 K (pixels)
    get_extrinsic,          # camera_params, i -> 4x4 E (mm, world-to-camera)
    get_projection,         # camera_params, i -> 3x4 P (mm)
    project_distortion,     # camera_params, i, pts_mm -> 2D pixels
    undistort_points,       # pts_px, K, dist -> undistorted_px
    distort_3d,             # camera_params, i, pts_mm -> distorted 3D mm
    triangulate_point,      # camera_params, pts_2d -> 3D mm
    robust_triangulate_points,  # camera_params, pts_2d -> 3D mm + weights
    reprojection_error,     # camera_params, pts_2d, pts_3d_mm -> residual px
)

# High-level meter-safe adapter
from multiview_biomechanical_pose.geometry.camera_adapter import (
    transform_points_world_to_camera,       # pts_m -> pts_m (camera frame)
    transform_points_camera_to_world,       # pts_m -> pts_m (world frame)
    transform_points_between_cameras,       # pts_m -> pts_m (target camera)
    project_camera_coordinates,             # pts_cam_m -> 2D pixels
    unproject_from_image_with_distortion,   # 2D px + depth_m -> 3D cam_m
    unproject_and_transform_to_world,       # 2D px + depth_m -> 3D world_m
    transform_pose_se3_world_to_camera,     # pos_m, quat -> pos_m, quat
    transform_pose_se3_camera_to_world,     # pos_m, quat -> pos_m, quat
    compute_relative_extrinsics,            # -> 4x4 relative transform (mm)
)

# Fit quality metrics
from multi_camera.analysis.fit_quality import reprojection_quality
```

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Passing meters to `project_distortion` | Multiply by 1000 first |
| Treating `get_extrinsic()` translation as camera position | It's world-to-camera; invert for camera position |
| Accessing `camera_params["mtx"]` raw values | Use `get_intrinsic()` which applies 1000x scaling |
| Creating per-camera param dicts | Pass full dict + camera index |
| Ignoring distortion in projection/unprojection | Always use distortion-aware functions |
| Assuming `triangulate_point` returns meters | It returns **mm** - divide by 1000 |
| Forgetting batch dims for `undistort_points` | Needs `(batch, N, 2)` input shape |
| Using COLMAP extrinsics directly | COLMAP is camera-to-world; ours is world-to-camera |
