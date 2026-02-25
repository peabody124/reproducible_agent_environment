---
name: fetching-synchronized-data
description: >-
  Use when fetching 2D keypoints synchronized with kinematic reconstruction qpos,
  aligning video frames with reconstruction frames, working with fetch_keypoints,
  handling camera parameter ordering between Calibration and SingleCameraVideo,
  or debugging temporal misalignment between observations and poses
---

# Fetching Synchronized Keypoints + Reconstruction Data

## Overview

KinematicReconstruction qpos and 2D keypoints come from different DataJoint tables with **independently managed timestamps**. Naive timestamp matching silently produces frame offsets that corrupt downstream tasks (guidance, evaluation, metrics). The correct approach uses `fetch_keypoints(only_detected=True)` from BodyModels, which guarantees 1:1 frame correspondence with KR qpos by construction.

## When to Use

- Fetching 2D keypoints that must align frame-by-frame with KR qpos
- Building inference/guidance pipelines that pair observations with reconstruction
- Debugging high reprojection error or misaligned 2D-3D data
- Writing any code that joins TopDownPerson keypoints with KinematicReconstruction

**When NOT to use:** Fetching keypoints for standalone 2D analysis (no KR alignment needed), or querying KR qpos without 2D observations.

---

## The Correct Pattern

```python
from body_models.datajoint.dataset import fetch_keypoints as bm_fetch_keypoints
from body_models.datajoint.kinematic_dj import KinematicReconstruction

trial_key = {
    "participant_id": participant_id,
    "session_date": session_date,
    "recording_timestamps": recording_timestamps,
}
full_key = {**trial_key, "kinematic_reconstruction_settings_num": 137}

# 1. Fetch qpos from KR
qpos = (KinematicReconstruction.Trial & full_key).fetch1("qpos")  # (T, 41)

# 2. Fetch keypoints using the SAME function that built the KR
timestamps, keypoints_raw = bm_fetch_keypoints(trial_key, only_detected=True)
# timestamps: (T,) video-start-relative seconds
# keypoints_raw: (C, T, 87, 3) — (x, y, confidence) per camera/frame/marker

# 3. CRITICAL: verify 1:1 correspondence
assert qpos.shape[0] == keypoints_raw.shape[1], (
    f"Frame count mismatch: qpos={qpos.shape[0]} vs keypoints={keypoints_raw.shape[1]}"
)

# 4. Extract components
confidences = keypoints_raw[..., 2]    # (C, T, 87)
keypoints_2d = keypoints_raw[..., :2]  # (C, T, 87, 2)
```

**Why this works:** `fetch_keypoints(only_detected=True)` applies the exact same frame filtering as `KeypointDataset` used when building the KR. Both arrays share the same frame indices — `qpos[i]` corresponds to `keypoints[:, i]` by construction.

---

## Camera Parameter Reordering

`KinematicReconstruction.updated_calibration` stores camera parameters in **Calibration table order**. Keypoints from `fetch_keypoints` are in **alphabetical SingleCameraVideo order**. These may differ.

```python
from multi_camera.datajoint.calibrate_cameras import Calibration
from multi_camera.datajoint.multi_camera_dj import SingleCameraVideo

cal_camera_names = (Calibration & parent_key).fetch1("camera_names")
camera_rows = (SingleCameraVideo & trial_key).fetch(as_dict=True, order_by="camera_name")
kp_camera_names = [row["camera_name"] for row in camera_rows]

# Reindex camera_params to match keypoint camera order
cal_names_list = list(cal_camera_names)
reorder_idx = [cal_names_list.index(name) for name in kp_camera_names]
for pkey in ("mtx", "rvec", "tvec", "dist"):
    val = np.asarray(camera_params[pkey])
    if val.ndim > 1:
        camera_params[pkey] = val[reorder_idx]
```

Without this, camera `i` in `keypoints_2d` gets projected with the wrong camera's intrinsics/extrinsics.

---

## Contiguous Segment Selection

After alignment, find the longest window with continuous detections and no time gaps:

```python
detected = np.sum(confidences, axis=(0, 2))  # (T,) — sum across cameras and joints
dt = np.median(np.diff(timestamps))
time_gaps = np.concatenate([np.diff(timestamps), [dt]]) > (1.5 * dt)
valid = np.logical_and(detected > 0, ~time_gaps)

# find_longest_segment returns (start, end) exclusive
start, end = find_longest_segment(valid)
timestamps = timestamps[start:end]
qpos = qpos[start:end]
keypoints_2d = keypoints_2d[:, start:end]
confidences = confidences[:, start:end]
```

---

## Anti-Patterns

| Pattern | Why It Fails |
|---------|-------------|
| Fetching `TopDownPerson` keypoints + `VideoInfo` timestamps separately, then matching with `isin_with_tolerance()` | KR timestamps zeroed relative to first detection; VideoInfo zeroed relative to video start. When first detection is at frame N>0, KR[0] incorrectly matches video[0] instead of video[N]. |
| Zeroing timestamps with `ts - ts[0]` before matching | Destroys the physical time correspondence between independently-sourced arrays. |
| Using `fetch_keypoints(only_detected=False)` with KR qpos | Returns all video frames including those without detections. Frame count won't match KR qpos (which only covers detected frames). |
| Assuming `camera_params` order matches keypoint order | Calibration order != SingleCameraVideo alphabetical order. Must reorder explicitly. |

**Real-world impact:** The timestamp-matching anti-pattern caused a 38-frame temporal offset on trial ASB_144 cam 8 (first detection at video frame 38), producing 900px reprojection error and unusable guidance.

---

## Invariants

1. **Frame correspondence:** `qpos.shape[0] == keypoints_raw.shape[1]` — always assert this
2. **Camera ordering:** After reordering, `camera_params` index `i` matches `keypoints_2d[i]`
3. **Timestamps are video-start-relative:** Not zeroed by KR; usable directly for time-gap detection
4. **`only_detected=True` is mandatory** when aligning with KR qpos

---

## Quick Reference

| Function | Source | Returns |
|----------|--------|---------|
| `fetch_keypoints(key, only_detected=True)` | `body_models.datajoint.dataset` | `(timestamps, keypoints)` — (T,) and (C, T, 87, 3) |
| `KinematicReconstruction.Trial.fetch1("qpos")` | `body_models.datajoint.kinematic_dj` | `(T, 41)` MuJoCo state |
| `KinematicReconstruction.fetch1("updated_calibration")` | same | Camera params dict (Calibration order) |
| `Calibration.fetch1("camera_names")` | `multi_camera.datajoint.calibrate_cameras` | List of camera names in calibration order |

**Complete reference implementation:** `BiomechanicalFlowModel/src/biomechanical_fm/datajoint/datajoint_fetcher.py:fetch_trial_data()`

**Related skills:** `rae:datajoint-biomechanics-schema` for schema details, `rae:camera-model` for projection conventions.
