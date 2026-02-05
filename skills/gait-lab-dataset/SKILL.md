---
name: gait-lab-dataset
description: >-
  Query and analyze clinical gait lab (marker-based motion capture) data.
  Use when asked about c3d files, gait lab sessions, mocap markers,
  MocapProjection synchronization, video-mocap temporal alignment,
  GaitLab-MMC trial matching, gait events, gait parameters, forceplate/EMG
  analog data, or comparing marker-based and markerless motion capture systems.
---

# GaitLab Dataset Reference

## Overview

The `gait_lab` schema stores traditional clinical gait lab data from Vicon c3d files. This is a **separate system** from the markerless multicamera (MMC) pipeline. The same participant may have data in both systems, recorded during the same session (MAC_LAB participants).

**Source:** `GaitLabDataset/gait_lab_dataset/`

**Schema name:** `gait_lab`

---

## Table Hierarchy

```
Subject (subject_hash)
    -> Session (subject_hash, session_name)
        -> Trial (subject_hash, session_name, trial_name)
        |   -> Mocap (point_names, points in mm, point_rate, timestamps)
        |   |   -> GaitEvents (event, side, time)
        |   |   -> GaitParameters (parameter, side, value)
        |   |   -> MocapAnalysis (property, value)
        |   |   -> MocapProjection (toffset, camera params, error, proj, frames)
        |   -> GaitTrialVideo -> pose_pipeline.Video
        |   -> Analog (analog_names, channels, timestamps, units)
        -> PTEval (eval_html) -> PTDemographics (age, diagnosis)
        -> Assessment (assessment)
        -> Height (computed, meters)
        -> Weight (computed, kg)
        -> SessionConditions -> SessionCondition + ConditionTrial
        -> MPParam (property, value, all_values)
    -> SubjectTrainTest (train boolean)
```

---

## Table Definitions

### Core Tables

**Subject** - De-identified subject identifier
```python
subject_hash: varchar(100)  # Primary key
```

**Session** - Clinical session grouping
```python
-> Subject
session_name: varchar(100)
```

**Trial** - Individual gait trial
```python
-> Session
trial_name: varchar(100)
---
timestamp: timestamp          # When the trial was recorded
description: varchar(1000)    # Free-text (e.g., "Barefoot with cane", "Right AFO")
vid_present: boolean          # Whether video was recorded
mocap_present: boolean        # Whether c3d mocap data exists
```

### Motion Capture Data

**Mocap** - 3D marker data from c3d files
```python
-> Trial
---
point_names: longblob    # List of marker names (e.g., ["SACR", "LASI", "RASI", ...])
points: longblob         # Shape: [n_frames, n_markers, 5]
                         #   Channels: [x, y, z, residual, visibility]
                         #   Units: MILLIMETERS
                         #   Visibility: 0 = valid, non-zero = occluded
point_rate: float        # Sampling rate, typically 100 Hz
frames: longblob         # Frame indices
timestamps: longblob     # Computed as frames / point_rate (seconds)
```

**Analog** - Force plate and EMG data
```python
-> Trial
---
analog_names: longblob   # Channel labels (e.g., forceplate channels, EMG channels)
channels: longblob       # Shape: [n_channels, n_samples] (transposed)
timestamps: longblob     # Synced to mocap: mocap_start + arange(n_samples) / analog_rate
units: longblob          # Physical units per channel (e.g., "N", "V")
```

Analog data is synchronized to mocap via a shared trigger pulse. Timestamps are computed relative to the mocap frame start time.

**GaitEvents** - Annotated gait events from Vicon processing
```python
-> Mocap
event_num: smallint
---
event: varchar(100)          # e.g., "The instant the heel strikes the ground"
side: enum('Left', 'Right')
time: float                  # Event time in seconds relative to mocap timestamps
```

**GaitParameters** - Pre-computed clinical gait parameters
```python
-> Mocap
parameter: varchar(50)       # e.g., stride length, cadence
side: enum('Left', 'Right')
---
value: float
```

### Video Linkage

**GaitTrialVideo** - Links gait trials to the pose pipeline's Video table
```python
-> Trial
-> Video                     # from pose_pipeline (video_project, filename)
```

### Session Metadata

**SessionConditions** (Computed) - Parsed trial conditions from descriptions
```python
-> Session
---
num_conditions: smallint     # Number of distinct gait conditions tested
```

Part table **SessionCondition**:
```python
-> SessionConditions
support: varchar(50)         # "none", "cane", "walker", "gait_trainer", "handheld", "crutch"
left_foot: varchar(50)       # "barefoot", "afo", "smo", "kafos", "brace", "ucb", "insert"
right_foot: varchar(50)      # Same options as left_foot
shoe: varchar(50)            # Whether shoes were worn
---
num_mocap: smallint           # Trials with synchronized mocap
num_frontal: smallint         # Frontal-view-only video trials
num_sagital: smallint         # Sagittal-view-only video trials
```

Part table **ConditionTrial**:
```python
-> GaitTrialVideo
-> SessionConditions.SessionCondition
---
view: smallint               # 0=with mocap sync, 1=frontal only, 2=sagittal only
```

**Height** (Computed) - Session-level height
```python
-> Session
---
height: float                # Meters, from MocapAnalysis("HEIGHT") or MPParam("Height")
```

**Weight** (Computed) - Session-level weight
```python
-> Session
---
weight: float                # kg, from MocapAnalysis("BODYMASS") or MPParam("Bodymass")
```

---

## MocapProjection: Video-Mocap Synchronization

The `MocapProjection` table synchronizes 3D mocap markers with 2D video keypoints, solving for both a temporal offset and camera projection parameters.

**Source:** `gait_lab_dataset/mocap_sync.py`

### Table Definition

```python
-> Mocap
-> GaitTrialVideo
-> TopDownPerson              # 2D keypoints from pose detection
-> VideoInfo
---
toffset: float               # Temporal offset (seconds) between mocap and video
fx, fy: float                # Camera focal lengths (pixels)
cx, cy: float                # Principal point (image center)
tx, ty, tz: float            # 3D translation (mocap -> camera frame)
rx, ry, rz: float            # Rotation (Rodrigues / exponential map, stored at 1/1000 scale)
error: float                 # Huber loss of final projection fit (lower = better)
proj: longblob               # Projected mocap positions in 2D [n_frames, n_joints, 2]
frames: longblob             # Video frame indices where projection was valid
```

### Synchronization Algorithm

The algorithm jointly optimizes temporal offset and camera parameters to align 3D mocap markers to 2D pose detections:

1. **Data extraction** (`get_dual_data()`):
   - Fetches mocap 3D markers (hip, knee, ankle via Plug-In Gait bone model)
   - Fetches 2D keypoints from TopDownPerson (COCO format)
   - Filters to frames with high confidence 2D detections (>0.2) and valid mocap markers (visibility==0)
   - Swaps Y/Z axes to align mocap vertical with image vertical
   - Clips to temporal overlap with 200ms buffer at each end

2. **OpenCV initialization** (`cv2_calibrate()`):
   - Uses `cv2.calibrateCamera()` with all points across time as one observation
   - Fixes principal point at image center, fixes all distortion coefficients
   - Initial focal length: ~1200 pixels
   - Must achieve Huber loss < 12 (quality gate)

3. **JAX/BFGS optimization** (`optimize_projection()`):
   - 9 parameters: `[tx, ty, tz, rx, ry, rz, fx, fy, toffset_raw]`
   - Time offset bounded: `toffset = tanh(toffset_raw) * 0.2` (max +/- 200ms)
   - Mocap is interpolated at `timestamps + toffset` for each candidate offset
   - Loss: Huber loss between detected 2D keypoints and projected 3D markers
   - Uses `jax.scipy.optimize.minimize(method="BFGS", maxiter=1000)`
   - Projection uses `SO3.exp(rvec)` for rotation (jaxlie)

4. **Storage**: Optimized parameters stored in MocapProjection table. Note `rx, ry, rz` are stored at **1/1000 scale** (divided by 1000 before insert).

### Marker Mapping (Mocap <-> COCO)

The synchronization maps Plug-In Gait bone markers to COCO keypoints:

| COCO Keypoint | Plug-In Gait Marker | Description |
|---------------|---------------------|-------------|
| Right Hip | RFEP | Right Femur Proximal |
| Right Knee | RFEO | Right Femur Origin |
| Right Ankle | RTIO | Right Tibia Origin |
| Left Hip | LFEP | Left Femur Proximal |
| Left Knee | LFEO | Left Femur Origin |
| Left Ankle | LTIO | Left Tibia Origin |

### Data Statistics

- ~8,568 successful MocapProjection rows computed
- ~9,405 rows with Mocap + GaitTrialVideo + TopDownPerson available
- ~1,000 potentially recoverable with improved alignment
- ~15,359 videos with mocap present total

---

## MMC-GaitLab Cross-System Matching

The `gait_lab_dataset.mmc` module compares markerless (MMC) and marker-based (GaitLab) motion capture data for the same participants (MAC_LAB sessions).

**Source:** `gait_lab_dataset/mmc/`

### Core Workflow

```python
from gait_lab_dataset.mmc import (
    get_gaitlab_session_for_participant,
    get_mmc_pelvis_data,
    get_gaitlab_pelvis_data,
    compute_session_times,
    find_optimal_matching,
    format_matching_report,
)

participant_id = "mac002"

# 1. Look up GaitLab session for this MMC participant (matches by date)
session_name = get_gaitlab_session_for_participant(participant_id)

# 2. Fetch pelvis trajectories from both systems
mmc_data = get_mmc_pelvis_data(participant_id)
gl_data = get_gaitlab_pelvis_data(session_name)

# 3. Compute session-relative timestamps
_, mmc_data = compute_session_times(mmc_data, "recording_time")
_, gl_data = compute_session_times(gl_data, "trial_time")

# 4. Find optimal trial matching (handles clock drift, spatial calibration)
result = find_optimal_matching(mmc_data, gl_data)

# 5. Human-readable report
report = format_matching_report(result, mmc_data, gl_data)
print(report)
```

### MatchingResult Fields

| Field | Type | Description |
|-------|------|-------------|
| `matches` | `list[tuple[int, int, float]]` | `(mmc_idx, gl_idx, offset_seconds)` per matched trial |
| `coverage` | `float` | Fraction of GaitLab trials matched (0-1) |
| `r_squared` | `float` | Combined R-squared across all matched trials |
| `offset_mean` | `float` | Mean temporal offset in seconds |
| `offset_std` | `float` | Temporal offset std dev in seconds |
| `cost_matrix` | `ndarray [n_mmc, n_gl]` | 1 - R-squared for each trial pair |
| `r_squared_matrix` | `ndarray [n_mmc, n_gl]` | Best R-squared for each pair |
| `unmatched_mmc` | `list[int]` | Indices of unmatched MMC trials |
| `unmatched_gl` | `list[int]` | Indices of unmatched GaitLab trials |
| `affine_A` | `ndarray [2,2]` | Global affine transform |
| `affine_b` | `ndarray [2]` | Affine offset |

### Synchronization Quality Interpretation

| Metric | Threshold | Interpretation |
|--------|-----------|----------------|
| R-squared > 0.95 | Excellent | High confidence in trial matching |
| R-squared 0.8-0.95 | Good | Matches likely correct |
| R-squared < 0.8 | Poor | Review manually |
| Offset std < 2s | Consistent | Clock alignment stable across trials |
| Offset std > 5s | Problematic | Clock drift or matching errors |

### Joint Angle Comparison

```python
from gait_lab_dataset.mmc import (
    get_mmc_joint_angles,
    get_gaitlab_joint_angles,
    align_joint_angles,
    compute_joint_r_squared,
    compute_joint_rmse,
    compute_axis_correlations,
)

mmc_angles = get_mmc_joint_angles(participant_id)
gl_angles = get_gaitlab_joint_angles(session_name)
_, mmc_angles = compute_session_times(mmc_angles, "recording_time")
_, gl_angles = compute_session_times(gl_angles, "trial_time")

# Compare matched trials
for mmc_idx, gl_idx, offset in result.matches:
    times, mmc, gl = align_joint_angles(mmc_angles[mmc_idx], gl_angles[gl_idx], offset)
    r2 = compute_joint_r_squared(mmc, gl)    # Per-joint R-squared (handles sign flips)
    rmse = compute_joint_rmse(mmc, gl)        # Per-joint RMSE in degrees
```

**Joint angle mappings:**
- Sagittal plane joints: `hip_flexion`, `knee_angle`, `ankle_angle` (bilateral)
- GaitLab markers: `LHipAngles`, `RHipAngles`, `LKneeAngles`, `RKneeAngles`, `LAnkleAngles`, `RAnkleAngles`
- Each has 3 channels: sagittal (X), frontal (Y), transverse (Z) in **degrees**

---

## Plug-In Gait Marker Names

### Surface Markers (17)

| Marker | Full Name |
|--------|-----------|
| SACR | Sacral |
| LASI / RASI | Left / Right Anterior Superior Iliac Spine |
| LPSI / RPSI | Left / Right Posterior Superior Iliac Spine |
| LTHI / RTHI | Left / Right Thigh |
| LKNE / RKNE | Left / Right Knee |
| LTIB / RTIB | Left / Right Tibia |
| LANK / RANK | Left / Right Ankle |
| LHEE / RHEE | Left / Right Heel |
| LTOE / RTOE | Left / Right Toe |

### Bone Markers (Used for Anatomical Calibration)

Naming pattern: `{SEGMENT}{SUFFIX}` where suffix is O=Origin, P=Proximal, A=Anterior, L=Lateral.

Segments: PEL (Pelvis), RFE/LFE (Femur), RTI/LTI (Tibia), RFO/LFO (Foot), RTO/LTO (Toe)

---

## Common Queries

### Count sessions with c3d data

```python
from gait_lab_dataset.dataset_dj import Trial, Session
sessions_with_mocap = Session & (Trial & 'mocap_present=1')
print(f"Sessions with c3d data: {len(sessions_with_mocap)}")
```

### Find MAC_LAB sessions with corresponding c3d files

```python
from multi_camera.datajoint.sessions import Session as MMCSession, Recording
from multi_camera.datajoint.multi_camera_dj import MultiCameraRecording
from gait_lab_dataset.dataset_dj import Session as GLSession, Trial, Mocap

# Get MAC_LAB MMC sessions
mmc_sessions = (MMCSession & (Recording & (MultiCameraRecording & "video_project='MAC_LAB'"))).fetch(as_dict=True)

# Get GaitLab sessions with mocap, compute dates from trial timestamps
gl_sessions = (GLSession & Mocap).fetch(as_dict=True)
gl_dates = {}
for gl in gl_sessions:
    timestamps = (Trial & gl).fetch('timestamp')
    if len(timestamps) > 0:
        gl_dates[gl['session_name']] = min(timestamps).date()

# Match by date
matched = sum(1 for mmc in mmc_sessions
              if any(mmc['session_date'] == d for d in gl_dates.values()))
```

### Query MocapProjection synchronization error

```python
from gait_lab_dataset.mocap_sync import MocapProjection
import numpy as np

errors = MocapProjection.fetch('error')
print(f"Entries: {len(errors)}, Median error: {np.median(errors):.4f}")
```

### Get gait events for a trial

```python
from gait_lab_dataset.dataset_dj import GaitEvents
events = (GaitEvents & key).fetch(as_dict=True)
for e in events:
    print(f"  {e['side']} {e['event']} at {e['time']:.3f}s")
```

### Get synchronized training data

```python
from gait_lab_dataset.fetch_training_dataset import get_synced_trial
# Returns aligned: [timestamps, keypoints3d, keypoints2d, mocap, mocap_weight, mocap_phase, mocap_phase_weight]
data = get_synced_trial(key)
```

---

## Data Conventions

### Units

| Data | Units |
|------|-------|
| Mocap marker positions (`points`) | **millimeters** |
| GaitLab joint angles | **degrees** |
| Height | **meters** |
| Weight | **kg** |
| Gait event times | **seconds** (relative to mocap start) |
| MocapProjection `toffset` | **seconds** |
| MocapProjection `rx, ry, rz` | Rodrigues vector / 1000 (stored scaled down) |
| Analog timestamps | **seconds** (synced to mocap clock) |
| MMC pelvis data | **meters** (from KinematicReconstruction) |

### Coordinate Axes

| System | X | Y | Z |
|--------|---|---|---|
| Mocap raw (Vicon) | Forward | Lateral | Vertical |
| After sync transform | Forward | **Vertical** | Lateral |

The synchronization code swaps Y/Z to align the mocap vertical axis with the image height axis: `points[:, :, [0, 2, 1, 3, 4]]`

### Visibility Flags

- **Mocap**: `points[:, :, 4] == 0` means visible/valid; non-zero means occluded
- **Video 2D keypoints**: `keypoints[:, :, 2] > 0.2` indicates high-confidence detection

---

## Known Issues

| Issue | Details |
|-------|---------|
| Knee angle sign convention | GaitLab and MMC use opposite signs (~-0.9 correlation). `compute_joint_r_squared` handles this via linear regression. |
| Unit mismatch | GaitLab `points` in mm; MMC `pelvis_xyz` in meters. Data loading functions handle conversion. |
| `find_optimal_matching` performance | Builds O(n*m) cost matrix with offset search. ~30s per participant. |
| `rx, ry, rz` storage scaling | Stored at 1/1000 scale in MocapProjection (divided before insert). Multiply by 1000 to recover original optimization values. |
| Missing TopDownPerson | ~5,959 videos lack 2D pose detections, preventing MocapProjection computation. |
| `cv2_calibrate` duplicate | `mocap_sync.py` contains two definitions of `cv2_calibrate`. The second (line 232) is the active one. |

---

## Quick Reference: Imports

```python
# Core schema tables
from gait_lab_dataset.dataset_dj import (
    Subject, Session, Trial, Mocap, GaitTrialVideo,
    GaitEvents, GaitParameters, Analog, Height, Weight,
    SessionConditions, MocapAnalysis, MPParam, SubjectTrainTest,
    ValidGaitEvents, PTEval, Assessment,
)

# Synchronization
from gait_lab_dataset.mocap_sync import MocapProjection

# MMC-GaitLab cross-system matching
from gait_lab_dataset.mmc import (
    get_gaitlab_session_for_participant,
    find_optimal_matching,
    format_matching_report,
    get_mmc_pelvis_data,
    get_gaitlab_pelvis_data,
    compute_session_times,
    get_mmc_joint_angles,
    get_gaitlab_joint_angles,
    align_joint_angles,
    compute_joint_r_squared,
    compute_joint_rmse,
    compute_axis_correlations,
)
from gait_lab_dataset.mmc.types import MatchingResult

# Training data
from gait_lab_dataset.fetch_training_dataset import get_synced_trial

# Associated tables from other systems
from pose_pipeline.pipeline import Video, VideoInfo, TopDownPerson
from multi_camera.datajoint.sessions import Session as MMCSession, Recording
from multi_camera.datajoint.multi_camera_dj import MultiCameraRecording
```

---

## File Paths

| Component | File |
|-----------|------|
| Schema definition | `gait_lab_dataset/dataset_dj.py` |
| Video-mocap sync | `gait_lab_dataset/mocap_sync.py` |
| Gait event processing | `gait_lab_dataset/mocap_processing.py` |
| Training data fetch | `gait_lab_dataset/fetch_training_dataset.py` |
| Gait phase estimation | `gait_lab_dataset/gait_phase_kalman.py` |
| MMC data loading | `gait_lab_dataset/mmc/data_loading.py` |
| MMC trial matching | `gait_lab_dataset/mmc/matching.py` |
| MMC joint comparison | `gait_lab_dataset/mmc/joint_comparison.py` |
| MMC types | `gait_lab_dataset/mmc/types.py` |
