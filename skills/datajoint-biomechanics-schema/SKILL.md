---
name: datajoint-biomechanics-schema
description: Use when working with biomechanics DataJoint pipeline - querying KinematicReconstruction, understanding Video-Session relationships, using bridging algorithms, debugging schema issues across PosePipeline/MultiCameraTracking/BodyModels, or working with method 137 results
---

# DataJoint Biomechanics Schema Reference

## Overview

The biomechanics pipeline uses DataJoint across four repositories with **two complementary data collection approaches**:

1. **Multi-Camera (MMC)** - Lab-based with calibrated camera rigs → `MultiCameraTracking` + `BodyModels/kinematic_dj.py`
2. **Portable/Monocular (PBL)** - Smartphone videos with optional IMU → `PortableBiomechanicsSessions` + `BodyModels/monocular_dj.py`

Both produce the same output format: **qpos, qvel, joints, sites** from MuJoCo body models.

---

## DataJoint Query Basics

### Operators
| Operator | Meaning | Example |
|----------|---------|---------|
| `&` | Restrict (filter) | `(Table & {'field': value})` |
| `*` | Join tables | `(Table1 * Table2)` |
| `-` | Set difference | `(Table1 - Table2)` finds rows NOT in Table2 |
| `.proj()` | Select attributes | `Table.proj('field1', 'field2')` |

### Fetch Patterns
```python
# fetch1() - Exactly one row, returns tuple or dict
timestamps, qpos = (KinematicReconstruction.Trial & key).fetch1('timestamps', 'qpos')

# fetch() - Multiple rows, returns arrays
all_keys = (Session & filter).fetch('KEY')
keypoints = (TopDownPerson & key).fetch('keypoints')

# With ordering (critical for multi-camera consistency)
kp, names = (Table & key).fetch('keypoints', 'camera_name', order_by='camera_name')
```

---

## Filtering by Project and Participant

### video_project Field

`video_project` is a categorical field (varchar(50)) that identifies the study/cohort. It lives in `MultiCameraRecording` and `Video` tables.

**Common projects:**
| Project | Description |
|---------|-------------|
| `GAIT_CONTROLS` | Healthy control gait data |
| `PROSTHETIC_GAIT` | Prosthetic gait subjects |
| `CM_GAIT` | Cervical myelopathy gait |
| `CLINIC_GAIT` | Clinical gait assessment |
| `PEDIATRIC_GAIT` | Pediatric subjects |
| `ASB2024` | ASB conference dataset |

### Query Patterns by Project

```python
# List all unique projects
projects = np.unique((MultiCameraRecording).fetch("video_project"))

# Find all participants in a project
participants = (Session & (Recording & (MultiCameraRecording & 'video_project="GAIT_CONTROLS"'))).fetch("participant_id")

# Filter trials by project
trials = KinematicReconstruction.Trial & (Recording & (MultiCameraRecording & f"video_project='{project}'"))

# Multiple projects with IN clause
filt = 'video_project in ("CLINIC_GAIT", "GAIT_CONTROLS", "PROSTHETIC_GAIT")'
sessions = Session & (Recording * MultiCameraRecording & filt)
```

### Participant Naming Conventions

| Project Type | Format | Examples |
|--------------|--------|----------|
| ASB studies | `ASB_###` | ASB_001, ASB_022 |
| Numeric IDs | integers | 72, 504, 127 |
| Special codes | mapped | TF01, TF02, TF47 |

### Session → Video Path (via video_project)
```
Session (participant_id, session_date)
    → Recording → MultiCameraRecording (video_project)
        → SingleCameraVideo → Video (video_project, filename)
```

---

## Key Output Fields Reference

| Field | Table | Shape | Description |
|-------|-------|-------|-------------|
| **qpos** | KinematicReconstruction.Trial | (T, 41) | Joint angles in generalized coordinates (radians) |
| **qvel** | KinematicReconstruction.Trial | (T, 41) | Joint velocities (rad/s) |
| **joints** | KinematicReconstruction.Trial | (T, N_joints, 3) | 3D joint positions (mm) |
| **sites** | KinematicReconstruction.Trial | (T, N_sites, 3) | 3D anatomical markers (mm) |
| **keypoints** | TopDownPerson | (T, N_kpts, 3) | 2D keypoints [x, y, conf] |
| **keypoints3d** | PersonKeypointReconstruction | (T, N_kpts, 4) | 3D keypoints [x, y, z, conf] (mm) |
| **keypoints_3d** | LiftingPerson | (T, N_kpts, 4) | Lifted 3D from monocular [x, y, z, conf] |
| **timestamps** | VideoInfo | list[datetime] | Absolute frame times |
| **delta_time** | VideoInfo | (T,) | Seconds from first frame |
| **fps** | VideoInfo | float | Frames per second |

### Common Access Patterns
```python
# Get 2D keypoints with video info
timestamps, keypoints = (TopDownPerson * VideoInfo & key).fetch1('timestamps', 'keypoints')

# Get kinematic reconstruction (ALWAYS specify method!)
qpos, sites = (KinematicReconstruction.Trial & key &
               {'kinematic_reconstruction_settings_num': 137}).fetch1('qpos', 'sites')

# Get 3D triangulated keypoints
kp3d = (PersonKeypointReconstruction & key).fetch1('keypoints3d')
```

---

## Two Data Collection Approaches

### 1. Multi-Camera (MMC) → KinematicReconstruction

**Key space:** `(participant_id, session_date)` bridged to `(recording_timestamps, camera_config_hash)`

```
Session → Recording → MultiCameraRecording → SingleCameraVideo → Video
                   ↘ SessionCalibration.Grouping → Calibration
                                     ↓
Video → TopDownPerson → PersonKeypointReconstruction (3D triangulation)
                                     ↓
                   KinematicReconstruction.Trial (qpos, qvel, joints, sites)
```

**Bridge Tables:**
- `Recording` - Links Session → MultiCameraRecording
- `SingleCameraVideo` - Links MultiCameraRecording → Video
- `SessionCalibration.Grouping` - Links Session → Calibration (required for KinematicReconstruction)

**Use when:** Lab-based data, multiple synchronized cameras, highest accuracy needed.

### 2. Portable/Monocular (PBL) → MonocularReconstruction

**Key space:** `(subject_id, session_start_time)` via Firebase

```
Subject → Session → Session.FirebaseSessionInfo
                              ↓
                    FirebaseSession (Computed)
                              ↓
            ┌─────────────────┼─────────────────┐
       AppVideo           Attitude/Gyro      PhoneAttitude
     (→ Video)            (IMU sensors)      (phone quaternion)
            ↓
    TopDownPerson → LiftingPerson (3D lifting)
                              ↓
            MonocularReconstruction.Trial (qpos, qvel, joints, sites, rnc)
```

**Additional output:** `rnc` (T, 3) - camera rotation vector from phone attitude

**Use when:** Smartphone videos, remote/home monitoring, wearable IMU/EMG data.

### Comparison

| Aspect | Multi-Camera | Monocular |
|--------|--------------|-----------|
| Input | Multiple synced cameras | Single smartphone camera |
| 3D Method | Triangulation | 2D→3D lifting |
| Accuracy | ~10-15mm, ~2-5° | ~15-20mm, ~5-10° |
| qpos DOF | 41 | 40 |
| Extra data | updated_calibration | rnc (phone rotation), IMU/EMG |
| Schema | `kinematic_dj.py` | `monocular_dj.py` |

---

## Method Numbers by Pipeline

**CRITICAL:** Always specify the method number in queries to avoid duplicates.

| Pipeline | Table | Method Field | Default Method |
|----------|-------|--------------|----------------|
| Multi-Camera | KinematicReconstruction | `kinematic_reconstruction_settings_num` | **137** |
| Monocular | MonocularReconstruction | `monocular_reconstruction_settings_num` | **1** |

### Multi-Camera: Method 137
```python
# CORRECT - Always specify method for KinematicReconstruction
key = {'participant_id': '102', 'session_date': date(2023, 7, 21),
       'kinematic_reconstruction_settings_num': 137}  # CRITICAL!

# WRONG - Returns BOTH 130 and 137 for dual-processed participants
key = {'participant_id': '102', 'session_date': date(2023, 7, 21)}
```

**Dual-processed participants (have both 130 and 137):**
ASB_022, ASB_007, ASB_008, ASB_020, ASB_041, ASB_071, ASB_081, ASB_083, ASB_085, ASB_095, ASB_125, ASB_130

**Method 137 config:** humanoid_torque_rl.xml, floor leveling enabled, 40k iterations

### Monocular: Method 1
```python
# For MonocularReconstruction queries
key = {'subject_id': 123, 'session_start_time': ...,
       'monocular_reconstruction_settings_num': 1}
```

---

## Bridging Algorithm

Bottom-up MeTRAbs detection inserted into top-down tables:

```
MeTRAbs (580 keypoints) → BottomUpBridging → BottomUpBridgingPerson
    ↓ filter_skeleton("bml_movi_87") → indices 264-350
TopDownPerson (method="Bridging_bml_movi_87")
    ↓ re-fetch from BottomUpBridging (not TopDownPerson!)
LiftingPerson (method="Bridging_bml_movi_87")
```

**Why "weird":** LiftingPerson normally uses TopDownPerson, but for bridging it re-fetches directly from BottomUpBridging.

---

## Quick Reference: Key Files

| Task | File |
|------|------|
| Video/VideoInfo/TopDownPerson | `PosePipeline/pose_pipeline/pipeline.py` |
| Bridging algorithm | `PosePipeline/pose_pipeline/wrappers/bridging.py` |
| MultiCameraRecording/SingleCameraVideo | `MultiCameraTracking/multi_camera/datajoint/multi_camera_dj.py` |
| Session/Recording (MMC) | `MultiCameraTracking/multi_camera/datajoint/sessions.py` |
| SessionCalibration | `MultiCameraTracking/multi_camera/datajoint/session_calibrations.py` |
| PersonKeypointReconstruction | `MultiCameraTracking/multi_camera/datajoint/multi_camera_dj.py` |
| KinematicReconstruction | `BodyModels/body_models/datajoint/kinematic_dj.py` |
| MonocularReconstruction | `BodyModels/body_models/datajoint/monocular_dj.py` |
| FirebaseSession/AppVideo (PBL) | `PortableBiomechanicsSessions/portable_biomechanics_sessions/emgimu_session.py` |
| PBL↔MMC linkage | `PortableBiomechanicsSessions/portable_biomechanics_sessions/mmc_linkage.py` |
| DataJoint principles | `PipelineOrchestrator/docs/datajoint_principles.md` |

---

## Common Mistakes

1. **Missing method number** - Queries without `kinematic_reconstruction_settings_num=137` return duplicates
2. **Wrong key space** - Using `(video_project, filename)` when you need `(participant_id, session_date)`
3. **Assuming LiftingPerson uses TopDownPerson** - For bridging methods, it re-fetches from BottomUpBridging
4. **Missing SessionCalibration.Grouping** - KinematicReconstruction requires this bridge
5. **Forgetting order_by** - Multi-camera queries need `order_by='camera_name'` for consistent ordering
6. **Confusing MonocularReconstruction vs KinematicReconstruction** - Monocular uses FirebaseSession.AppVideo, Kinematic uses SessionCalibration.Recordings
7. **Not filtering by video_project** - Queries across all projects mix different populations; always filter to your target cohort
