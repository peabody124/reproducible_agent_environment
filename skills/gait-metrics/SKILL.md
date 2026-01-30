---
name: gait-metrics
description: Use when analyzing gait data, computing spatiotemporal metrics, finding valid walking segments, calculating step length/cadence/velocity, joint ROM per gait cycle, gait phase percentages, asymmetry indices, or Gait Deviation Index (GDI) from kinematic reconstructions
---

# Gait Metrics Reference

## Overview

The gait analysis pipeline detects walking segments from kinematic reconstructions, extracts gait events (foot contacts), and computes spatiotemporal metrics, joint kinematics, and the Gait Deviation Index (GDI). It works with both multi-camera (MMC) and monocular (PBL) data.

**Schemas:** `project_body_models_gait_cycles` (walking detection, gait events) and `project_gdi` (GDI computation)

**Source:** `BodyModels/body_models/datajoint/gait/` and `BodyModels/body_models/biomechanics_mjx/gait/`

---

## Finding Valid Walking Segments

Walking segments are detected by `GaitTransformer` (MMC) and `GaitTransformerMonocular` (PBL). Both use a GaitTransformer neural network + Kalman filter pipeline to identify when a person is walking.

### Detection Pipeline

1. **Keypoint extraction** from sites (17 keypoints mapped to GastNet order)
2. **GaitTransformer inference** produces 8-channel gait phase output
3. **Kalman filter smoothing** refines phase estimates, produces error signal
4. **Walking probability** = `prob_err * prob_speed` where:
   - `prob_err = exp(-errors * 2)` (Kalman filter prediction error)
   - `prob_speed` = sigmoid of phase velocity * consistency with median
5. **Hysteresis thresholding** (0.35/0.65) + median filter deglitching
6. **Minimum segment length** filter (>100 frames)

### Querying Walking Segments

```python
from body_models.datajoint.gait.gait_cycles_dj import GaitTransformer, GaitTransformerMonocular

# Get the longest walking segment for a trial
key = {
    'participant_id': '104', 'session_date': date(2023, 7, 21),
    'kinematic_reconstruction_settings_num': 137,
    'transformer_method_name': 'default',
}

# WalkingSegment part table has aggregate stats per segment
segments = (GaitTransformer.WalkingSegment & key).fetch(as_dict=True, order_by='num_frames DESC')
best_segment = segments[0]  # Longest segment

# Aggregate stats available per segment:
#   num_frames, cadence, velocity,
#   stance_left, stance_right, ss_left, ss_right, dst,
#   length_left, length_right, width_left, width_right,
#   cycles_left, cycles_right (interpolated gait cycles, 100 timepoints each)
```

### Filtering for Walking Trials

```python
from multi_camera.datajoint.annotation import VideoActivity

# Only trials annotated as walking
walking_trials = (
    GaitTransformer
    & (VideoActivity & {'video_activity': 'Overground Walking'})
    & {'kinematic_reconstruction_settings_num': 137}
)

# From a specific project
from multi_camera.datajoint.multi_camera_dj import MultiCameraRecording
walking_controls = walking_trials & (MultiCameraRecording & {'video_project': 'GAIT_CONTROLS'})
```

### Monocular Walking Segments

```python
from portable_biomechanics_sessions.session_annotations import VideoActivity as PBLVideoActivity

monocular_walking = (
    GaitTransformerMonocular
    & (PBLVideoActivity & {'video_activity': 'Overground Walking'})
    & {'monocular_reconstruction_settings_num': -108}
)
```

---

## Gait Events

`GaitTransformer` stores four event arrays as longblobs:

| Field | Description |
|-------|-------------|
| `left_down` | Left foot initial contact timestamps |
| `left_up` | Left foot toe-off timestamps |
| `right_down` | Right foot initial contact timestamps |
| `right_up` | Right foot toe-off timestamps |

```python
events = (GaitTransformer & key).fetch1()
left_down = events['left_down']    # numpy array of timestamps
right_down = events['right_down']

# Filter events to longest walking segment
timestamps = (KinematicReconstruction.Trial & key).fetch1('timestamps')
start, end = (GaitTransformer.WalkingSegment & key).fetch(
    'segment_start', 'segment_end', order_by='num_frames DESC', limit=1
)
t0, te = timestamps[start[0]], timestamps[end[0]]
valid_left_down = [t for t in left_down if t0 <= t <= te]
```

### Gait Cycle Definition

A gait cycle runs from one foot contact to the next same-foot contact:
- **Stride** = foot_down[i] to foot_down[i+1] (one full cycle)
- **Stance phase** = foot_down to foot_up (foot on ground)
- **Swing phase** = foot_up to next foot_down (foot in air)
- **Step** = contralateral foot_down to ipsilateral foot_down

---

## Spatiotemporal Metrics

### Step-by-Step Metrics (Steps Part Table)

`GaitTransformer.Steps` stores per-step metrics:

| Field | Description |
|-------|-------------|
| `side` | Left or Right |
| `step_time` | Timestamp of the step |
| `velocity` | Walking velocity (m/s) at this step |
| `cadence` | Steps/min at this step |
| `ss_left` | Left single support (%) |
| `ss_right` | Right single support (%) |
| `dst` | Double support time (%) |
| `length` | Step length (m), NULL for monocular |
| `width` | Step width (m), NULL for monocular |

```python
steps = (GaitTransformer.Steps & key).fetch(as_dict=True)
```

### Computing Detailed Metrics from Raw Data

For more detailed analysis beyond the stored tables, use `gait_analysis.py`:

```python
from body_models.datajoint.gait.gait_analysis import compute_gait_analysis, summarize_gait_metrics

results = compute_gait_analysis(key)
# Returns dict with: timestamps, reoriented_qpos, reoriented_joints, events_raw, metrics

# metrics contains DataFrames:
#   step_metrics: step_time, step_length per step
#   gait_cycle_metrics: cycle_time, stride_length, walking_speed per cycle
#   phase_metrics: stance%, swing% per cycle
#   joint_rom: ROM per joint per cycle (radians)
#   knee_swing_rom: knee ROM during swing only
#   ankle_at_foot_down: ankle angle at each foot contact

summary = summarize_gait_metrics(results)
# Returns DataFrame with Mean/Std per side + asymmetry indices
```

Or use the standalone function (does not require GaitTransformer table):

```python
from body_models.biomechanics_mjx.gait.gait_metrics import compute_gait_analysis

results = compute_gait_analysis(key, remove_first_cycle=True)
# metrics dict: step_metrics, phase_metrics, cycle_rom, phase_rom, ankle_at_foot_down
```

---

## Metric Definitions

### Step Metrics

| Metric | Definition | Units |
|--------|-----------|-------|
| Step length | Distance between opposite heels at foot contact | m or mm |
| Step width | Lateral distance between heels at foot contact | m or mm |
| Step time | Time between contralateral contacts | s |
| Stride length | Pelvis displacement over one gait cycle | m |
| Cycle time | Duration of one full gait cycle | s |
| Walking speed | Stride length / cycle time | m/s |
| Cadence | Steps per minute derived from phase velocity | steps/min |

### Phase Metrics

| Metric | Definition | Normal Range |
|--------|-----------|-------------|
| Stance phase | % of stride foot is on ground | ~60% |
| Swing phase | % of stride foot is in air | ~40% |
| Single support | % of stride only one foot on ground | ~40% |
| Double support | % of stride both feet on ground | ~20% |

### Joint Angles Analyzed

| Joint | Index in qpos | Description |
|-------|---------------|-------------|
| `hip_flexion_r/l` | via ForwardKinematics | Hip flexion/extension |
| `hip_adduction_r/l` | via ForwardKinematics | Hip adduction/abduction |
| `hip_rotation_r/l` | via ForwardKinematics | Hip internal/external rotation |
| `knee_angle_r/l` | via ForwardKinematics | Knee flexion/extension |
| `ankle_angle_r/l` | via ForwardKinematics | Ankle dorsiflexion/plantarflexion |

### Asymmetry Index

```
asymmetry = |left_mean - right_mean| / max(left_mean, right_mean) * 100
```

Computed for: step time, step length, cycle time, stride length, walking speed, stance phase, hip flexion ROM, knee angle ROM.

---

## Gait Deviation Index (GDI)

GDI quantifies overall gait pathology by comparing joint angle patterns to a control group using PCA.

### Schema: `project_gdi`

### Tables

| Table | Description |
|-------|-------------|
| `GDIJointsLookup` | Defines which joints to use (method 0 = 13 joints: pelvis tilt/list/rotation + bilateral hip/knee/ankle) |
| `GDICyclesMethod` | Links GaitTransformer trials to GDI computation (MMC) |
| `GDICycles` | Stores parsed gait cycles per trial: `parsed_cycles_right`, `parsed_cycles_left` (Joint x 50 timepoints x Steps) |
| `GDICyclesMethodMonocular` | Links GaitTransformerMonocular trials to GDI (PBL) |
| `GDICyclesMonocular` | Same as GDICycles for monocular data |

### Computing GDI

```python
from body_models.biomechanics_mjx.gait.gdi import get_gdi_matrix_session, pca_gdi

# Get control group matrix (aggregate per session)
ctrl_keys = (GDICyclesMethod & {'video_project': 'GAIT_CONTROLS'}).fetch('KEY')
ctrl_matrix, ctrl_session_keys = get_gdi_matrix_session(ctrl_keys)

# Get treatment group matrix
trtmt_keys = (GDICyclesMethod & {'video_project': 'PROSTHETIC_GAIT'}).fetch('KEY')
trtmt_matrix, trtmt_session_keys = get_gdi_matrix_session(trtmt_keys)

# Compute GDI scores
gdi_ctrl, gdi_trtmt, ctrl_pca, trtmt_pca, n_components = pca_gdi(ctrl_matrix, trtmt_matrix)
# GDI ~ 100 = normal, lower = more pathological (each 10-point drop = 1 SD from normal)
```

### GDI Interpretation

| GDI Score | Interpretation |
|-----------|---------------|
| >= 100 | Normal gait pattern |
| 90-100 | Mild deviation |
| 80-90 | Moderate deviation |
| < 80 | Severe deviation |

---

## Walking Segment Validation

### Stride Length Filter

`gait_analysis.py` filters cycles by minimum stride length (default 0.1m) using pelvis displacement. It also discards the first valid cycle per side to remove gait initiation artifacts.

```python
# Internal logic in _filter_events_by_valid_cycles:
# 1. For each foot-down-to-foot-down cycle, compute pelvis displacement
# 2. Keep cycles where displacement >= 0.1m (walking forward)
# 3. Drop first valid cycle per side (initiation artifact)
```

### Quality Filtering with MultiTrackingDetection

```python
from multi_camera.datajoint.quality_metrics import MultiTrackingDetection

# Filter for trials with no tracking breaks
good_track = (MultiTrackingDetection & "top_down_method=12 and reconstruction_method=2") & "num_breaks=0"
clean_gait = GaitTransformer & good_track
```

---

## Quick Reference: Imports

```python
# Walking detection tables
from body_models.datajoint.gait.gait_cycles_dj import (
    GaitTransformer, GaitTransformerMonocular,
    TransformerMethod, TransformerMethodMonocular,
    TransformerMethodLookup,
)

# GDI tables
from body_models.datajoint.gait.gdi_dj import (
    GDICycles, GDICyclesMonocular,
    GDICyclesMethod, GDICyclesMethodMonocular,
    GDIJointsLookup,
)

# Detailed gait analysis (DataJoint-based, uses GaitTransformer)
from body_models.datajoint.gait.gait_analysis import (
    compute_gait_analysis, summarize_gait_metrics, plot_gait_analysis, StepMetrics,
)

# Standalone gait metrics (direct from KinematicReconstruction)
from body_models.biomechanics_mjx.gait.gait_metrics import (
    compute_gait_analysis as compute_gait_analysis_standalone,
    calculate_step_metrics,
)

# GDI computation
from body_models.biomechanics_mjx.gait.gdi import (
    get_gdi_matrix_session, get_gdi_matrix_steps, pca_gdi,
)

# Walking activity annotations
from multi_camera.datajoint.annotation import VideoActivity
from portable_biomechanics_sessions.session_annotations import VideoActivity as PBLVideoActivity
```

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Querying GaitTransformer without `transformer_method_name` | Add `'transformer_method_name': 'default'` to key |
| Using all events instead of filtering to walking segment | Filter events to `[t0, te]` of best WalkingSegment |
| Forgetting `kinematic_reconstruction_settings_num=137` | Always specify method number |
| Computing metrics on gait initiation | Use `remove_first_cycle=True` or the built-in stride-length filter |
| Mixing `gait_metrics.py` and `gait_analysis.py` | `gait_metrics.py` is standalone; `gait_analysis.py` uses GaitTransformer events |
| Monocular GaitTransformer uses different settings | Default `monocular_reconstruction_settings_num=-108` for monocular |
