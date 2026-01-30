---
name: pose-datajoint
description: Use when writing Python code to query biomechanics DataJoint tables - counting videos/sessions, filtering by video_project or participant_id/subject_id, fetching keypoints or kinematic reconstructions, understanding Session-Video relationships for both multi-camera and monocular pipelines
---

# Pose DataJoint Query Reference

## Overview

The biomechanics pipeline has **two parallel systems**:
1. **Multi-Camera (MMC)** - Lab-based, multiple synchronized cameras, uses `participant_id` (string)
2. **Monocular (PBL)** - Phone-based portable recordings, uses `subject_id` (integer)

Both produce kinematic outputs (qpos, joints, sites) but have different table hierarchies.

## Quick Reference: Package Imports

```python
# Shared: Video and 2D/3D pose estimation
from pose_pipeline.pipeline import Video, VideoInfo, TopDownPerson, LiftingPerson

# === MULTI-CAMERA (MMC) ===
from multi_camera.datajoint.sessions import Session, Recording, Subject
from multi_camera.datajoint.multi_camera_dj import (
    MultiCameraRecording, SingleCameraVideo, PersonKeypointReconstruction
)
from body_models.datajoint.kinematic_dj import KinematicReconstruction

# === MONOCULAR (PBL) ===
from portable_biomechanics_sessions.emgimu_session import (
    Subject as PBLSubject,      # Note: different from MMC Subject!
    Session as PBLSession,      # Note: different from MMC Session!
    FirebaseSession
)
from body_models.datajoint.monocular_dj import MonocularReconstruction
```

## Key Spaces (CRITICAL - Different Per Pipeline!)

### Multi-Camera Key Space
```python
# Session: participant_id is STRING
session_key = {'participant_id': '104', 'session_date': date(2023, 7, 21)}

# Video: video_project + filename
video_key = {'video_project': 'CLINIC_GAIT', 'filename': 'trial_001.27.mp4'}
```

### Monocular Key Space
```python
# Subject/Session: subject_id is INTEGER, project is part of key
subject_key = {'subject_id': 301, 'project': 'HLL'}

# Session adds timestamp
session_key = {'subject_id': 301, 'project': 'HLL',
               'session_start_time': datetime(2024, 1, 15, 10, 30, 0)}

# AppVideo links to Video table
app_video_key = {**session_key, 'app_start_time': ...,
                 'video_project': 'HLL', 'filename': '0301_gait.mp4'}
```

## DataJoint Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `&` | Restrict (filter) | `Video & 'video_project="HLL"'` |
| `*` | Join tables | `Session * Recording * MultiCameraRecording` |
| `-` | Set difference | `Video - TopDownPerson` (videos without poses) |
| `.proj()` | Select attributes | `Table.proj('field1', 'field2')` |

## Fetching Data

```python
# fetch1() - Exactly ONE row (raises error if 0 or >1)
timestamps, qpos = (Table & key).fetch1('timestamps', 'qpos')

# fetch() - Multiple rows as arrays
all_keys = (Table & restriction).fetch('KEY')  # List of dicts
values = (Table & key).fetch('field_name')     # Numpy array

# fetch(as_dict=True) - Multiple rows as list of dicts
records = (Table & key).fetch(as_dict=True)
```

---

## Multi-Camera (MMC) Queries

### Count Videos in MMC Project
```python
from pose_pipeline.pipeline import Video
from multi_camera.datajoint.multi_camera_dj import MultiCameraRecording, SingleCameraVideo

# Videos linked to multi-camera recordings
count = len(Video & SingleCameraVideo & (MultiCameraRecording & 'video_project="CLINIC_GAIT"'))
```

### Count Sessions/Participants in MMC
```python
from multi_camera.datajoint.sessions import Session, Recording
from multi_camera.datajoint.multi_camera_dj import MultiCameraRecording
import numpy as np

# Sessions for a participant (participant_id is STRING!)
count = len(Session & {'participant_id': '104'})

# Unique participants in a project
participants = np.unique(
    (Session & (Recording & (MultiCameraRecording & 'video_project="CLINIC_GAIT"'))).fetch('participant_id')
)
print(f"Participants: {len(participants)}")
```

### Get MMC Kinematic Reconstruction
```python
from body_models.datajoint.kinematic_dj import KinematicReconstruction
from datetime import date

# CRITICAL: Always specify kinematic_reconstruction_settings_num!
key = {
    'participant_id': '102',
    'session_date': date(2023, 7, 21),
    'kinematic_reconstruction_settings_num': 137  # REQUIRED!
}

timestamps, qpos, joints, sites = (KinematicReconstruction.Trial & key).fetch1(
    'timestamps', 'qpos', 'joints', 'sites'
)
# qpos: (T, 41) joint angles in radians
# joints: (T, N_bodies, 3) body positions in meters
# sites: (T, N_sites, 3) marker positions in meters
```

### Get 3D Triangulated Keypoints (MMC)
```python
from multi_camera.datajoint.multi_camera_dj import PersonKeypointReconstruction

key = {
    'video_project': 'CLINIC_GAIT',
    'video_base_filename': 'trial_20231215_143022',
    'reconstruction_method': 0  # 0=Robust Triangulation
}
keypoints3d = (PersonKeypointReconstruction & key).fetch1('keypoints3d')
# Shape: (T, N_joints, 4) - [x, y, z, confidence], units: mm
```

---

## Monocular (PBL) Queries

### Count Videos in Monocular Project
```python
from portable_biomechanics_sessions.emgimu_session import FirebaseSession

# AppVideo is a Part table of FirebaseSession
count = len(FirebaseSession.AppVideo & {'video_project': 'HLL'})
print(f"HLL monocular videos: {count}")
```

### Count Subjects in Monocular Project
```python
from portable_biomechanics_sessions.emgimu_session import FirebaseSession
import numpy as np

# Get unique subject_ids for a project
subject_ids = np.unique(
    (FirebaseSession.AppVideo & {'video_project': 'HLL'}).fetch('subject_id')
)
print(f"Subjects with HLL videos: {len(subject_ids)}")
```

### Count Monocular Videos Processed with Kinematic Reconstruction
```python
from portable_biomechanics_sessions.emgimu_session import FirebaseSession
from body_models.datajoint.monocular_dj import MonocularReconstruction

# Videos that have monocular reconstruction
processed = len(
    FirebaseSession.AppVideo
    & (MonocularReconstruction.Trial & {'video_project': 'HLL'})
)
print(f"HLL videos with monocular reconstruction: {processed}")

# Videos NOT yet processed
all_videos = FirebaseSession.AppVideo & {'video_project': 'HLL'}
unprocessed = len(all_videos - MonocularReconstruction.Trial)
print(f"HLL videos needing processing: {unprocessed}")
```

### Get Monocular Kinematic Reconstruction
```python
from body_models.datajoint.monocular_dj import MonocularReconstruction
from datetime import datetime

# Monocular uses subject_id (INTEGER) and project
key = {
    'subject_id': 301,
    'project': 'HLL',
    'session_start_time': datetime(2024, 1, 15, 10, 30, 0),
    'monocular_reconstruction_settings_num': 1  # Specify method
}

# Get all trials for this session
trial_keys = (MonocularReconstruction.Trial & key).fetch('KEY')

for trial_key in trial_keys:
    timestamps, qpos, joints, sites, rnc = (MonocularReconstruction.Trial & trial_key).fetch1(
        'timestamps', 'qpos', 'joints', 'sites', 'rnc'
    )
    # qpos: (T, 40) joint angles - monocular has 40 DOF (vs 41 for MMC)
    # rnc: (T, 3) camera rotation vector from phone attitude
    print(f"Video: {trial_key['filename']}, frames: {len(timestamps)}")
```

### List Monocular Projects
```python
from portable_biomechanics_sessions.emgimu_session import FirebaseSession
import numpy as np

projects = np.unique(FirebaseSession.AppVideo.fetch('video_project'))
print(f"Monocular projects: {projects}")
```

---

## Shared Queries (Work for Both Pipelines)

### Get 2D Keypoints
```python
from pose_pipeline.pipeline import TopDownPerson

key = {
    'video_project': 'HLL',  # Works for any project
    'filename': 'trial_001.mp4',
    'video_subject_id': 0,
    'top_down_method': 0  # 0=MMPose
}
keypoints = (TopDownPerson & key).fetch1('keypoints')  # Shape: (T, N_joints, 3)
```

### Get 3D Lifted Keypoints
```python
from pose_pipeline.pipeline import LiftingPerson

key = {**video_key, 'video_subject_id': 0, 'top_down_method': 0, 'lifting_method': 1}
keypoints_3d = (LiftingPerson & key).fetch1('keypoints_3d')  # Shape: (T, N_joints, 4)
```

### Count All Videos by Project
```python
from pose_pipeline.pipeline import Video
from collections import Counter

projects = Video.fetch('video_project')
for project, count in Counter(projects).items():
    print(f"{project}: {count} videos")
```

---

## Table Relationships

### Multi-Camera Hierarchy
```
Subject (participant_id)  ← STRING
    -> Session (participant_id, session_date)
        -> Recording -> MultiCameraRecording (video_project)
                            -> SingleCameraVideo -> Video
                            -> PersonKeypointReconstruction (3D triangulated)
        -> SessionCalibration.Grouping
            -> KinematicReconstruction (method 137)
                -> KinematicReconstruction.Trial (qpos, joints, sites)
```

### Monocular Hierarchy
```
Subject (subject_id, project)  ← INTEGER + project
    -> Session (subject_id, project, session_start_time)
        -> FirebaseSession
            -> FirebaseSession.AppVideo -> Video
            -> FirebaseSession.PhoneAttitude (phone orientation)
            -> FirebaseSession.Gyro/Accel/Mag (IMU data)

MonocularReconstruction (subject_id, project, session_start_time, method)
    -> MonocularReconstruction.Trial (qpos, joints, sites, rnc)
        -> FirebaseSession.AppVideo (links video)
```

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| MMC: `{'subject_id': 104}` | Use `{'participant_id': '104'}` (string!) |
| PBL: `{'participant_id': '301'}` | Use `{'subject_id': 301}` (integer!) |
| `Keypoints2D` table | Use `TopDownPerson` for 2D keypoints |
| Missing method for KinematicReconstruction | Add `'kinematic_reconstruction_settings_num': 137` |
| Missing method for MonocularReconstruction | Add `'monocular_reconstruction_settings_num': 1` |
| `fetch(unique=True)` | Use `np.unique(table.fetch('field'))` |
| `create_virtual_module()` | Direct import from modules |
| Mixing MMC Session with PBL Session | Import with alias: `Session as PBLSession` |

---

## Method Numbers Reference

| Pipeline | Table | Method Field | Default |
|----------|-------|--------------|---------|
| 2D Pose | TopDownPerson | `top_down_method` | 0 (MMPose) |
| 3D Lifting | LiftingPerson | `lifting_method` | 1 (VideoPose3D) |
| 3D Triangulation (MMC) | PersonKeypointReconstruction | `reconstruction_method` | 0 |
| Multi-Camera Kinematic | KinematicReconstruction | `kinematic_reconstruction_settings_num` | **137** |
| Monocular Kinematic | MonocularReconstruction | `monocular_reconstruction_settings_num` | **1** |

---

## DataJoint Schema Names

Each repository stores tables in named MySQL schemas. Use these to connect directly or create virtual modules with `dj.VirtualModule('alias', 'schema_name')`.

| Schema Name | Repository | Key Tables |
|-------------|-----------|------------|
| `pose_pipeline` | PosePipeline | Video, VideoInfo, TopDownPerson, LiftingPerson |
| `mocap_sessions` | MultiCameraTracking | Subject, Session, Recording |
| `multicamera_tracking` | MultiCameraTracking | MultiCameraRecording, SingleCameraVideo, PersonKeypointReconstruction, Calibration |
| `multicamera_tracking_annotation` | MultiCameraTracking | VideoActivity (walking/standing labels) |
| `project_body_models` | BodyModels | KinematicReconstruction, KinematicReconstruction.Trial, ProbabilisticReconstruction |
| `project_monocular_testing` | BodyModels | MonocularReconstruction, MonocularReconstruction.Trial |
| `project_body_models_gait_cycles` | BodyModels | GaitTransformer, GaitTransformer.WalkingSegment, GaitTransformer.Steps, GaitTransformerMonocular |
| `project_gdi` | BodyModels | GDICycles, GDICyclesMonocular, GDIJointsLookup |
| `emgimu_sessions` | PortableBiomechanicsSessions | Subject, Session, FirebaseSession, FirebaseSession.AppVideo |
| `openpbl_session_annotations` | PortableBiomechanicsSessions | VideoActivity (PBL), WalkingType |

### Connecting Without Code Access

```python
import datajoint as dj

# Create virtual modules to access tables without installing the package
kinematic = dj.VirtualModule('kinematic', 'project_body_models')
gait = dj.VirtualModule('gait', 'project_body_models_gait_cycles')
sessions = dj.VirtualModule('sessions', 'mocap_sessions')
pose = dj.VirtualModule('pose', 'pose_pipeline')
mmc = dj.VirtualModule('mmc', 'multicamera_tracking')

# Then query as usual
keys = kinematic.KinematicReconstruction.fetch('KEY')
```

### Gait-Specific Tables

For gait analysis (walking segments, step metrics, GDI), see the `/gait-metrics` skill which documents:
- Walking segment detection and validation
- Spatiotemporal gait metrics (step length, cadence, velocity)
- Gait Deviation Index (GDI) computation
- Joint ROM analysis per gait cycle/phase

---

## Files to Explore

| Task | File |
|------|------|
| Video/TopDownPerson | `PosePipeline/pose_pipeline/pipeline.py` |
| MMC Session/Recording | `MultiCameraTracking/multi_camera/datajoint/sessions.py` |
| MMC MultiCameraRecording | `MultiCameraTracking/multi_camera/datajoint/multi_camera_dj.py` |
| MMC KinematicReconstruction | `BodyModels/body_models/datajoint/kinematic_dj.py` |
| PBL Subject/Session/FirebaseSession | `PortableBiomechanicsSessions/portable_biomechanics_sessions/emgimu_session.py` |
| PBL MonocularReconstruction | `BodyModels/body_models/datajoint/monocular_dj.py` |
| Gait Cycles/Walking Segments | `BodyModels/body_models/datajoint/gait/gait_cycles_dj.py` |
| GDI (Gait Deviation Index) | `BodyModels/body_models/datajoint/gait/gdi_dj.py` |
| Gait Step/Phase Metrics | `BodyModels/body_models/datajoint/gait/gait_analysis.py` |
| Gait Event Detection | `BodyModels/body_models/biomechanics_mjx/gait/gait_transformer_cycles.py` |
| Gait Metrics (standalone) | `BodyModels/body_models/biomechanics_mjx/gait/gait_metrics.py` |
| VideoActivity (MMC walking labels) | `MultiCameraTracking/multi_camera/datajoint/annotation.py` |
| VideoActivity (PBL walking labels) | `PortableBiomechanicsSessions/portable_biomechanics_sessions/session_annotations.py` |
