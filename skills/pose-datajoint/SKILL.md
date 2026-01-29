---
name: pose-datajoint
description: Use when writing Python code to query biomechanics DataJoint tables - counting videos/sessions, filtering by video_project or participant_id, fetching keypoints or kinematic reconstructions, understanding Session-Video relationships, or debugging query errors like missing method numbers
---

# Pose DataJoint Query Reference

## Overview

The biomechanics pipeline uses DataJoint across multiple packages. **Always import tables directly from their modules** - never use `create_virtual_module`. The key insight: videos and sessions live in different key spaces connected by bridge tables.

## Quick Reference: Package Imports

```python
# Video and 2D/3D pose estimation
from pose_pipeline.pipeline import Video, VideoInfo, TopDownPerson, LiftingPerson

# Multi-camera sessions and calibration
from multi_camera.datajoint.sessions import Session, Recording, Subject
from multi_camera.datajoint.multi_camera_dj import MultiCameraRecording, SingleCameraVideo, PersonKeypointReconstruction

# Kinematic reconstruction (ALWAYS specify method!)
from body_models.datajoint.kinematic_dj import KinematicReconstruction, KinematicReconstructionSettingsLookup

# Portable biomechanics (phone-based)
from portable_biomechanics_sessions.emgimu_session import FirebaseSession, Subject as PBLSubject
```

## DataJoint Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `&` | Restrict (filter) | `Video & 'video_project="CLINIC_GAIT"'` |
| `*` | Join tables | `Session * Recording * MultiCameraRecording` |
| `-` | Set difference | `Video - TopDownPerson` (videos without poses) |
| `.proj()` | Select attributes | `Table.proj('field1', 'field2')` |

## Fetching Data

```python
# fetch1() - Exactly ONE row (raises error if 0 or >1)
timestamps, qpos = (KinematicReconstruction.Trial & key).fetch1('timestamps', 'qpos')

# fetch() - Multiple rows as arrays
all_keys = (Session & restriction).fetch('KEY')  # List of dicts
values = (Table & key).fetch('field_name')       # Numpy array

# fetch(as_dict=True) - Multiple rows as list of dicts
records = (Table & key).fetch(as_dict=True)

# With ordering (critical for multi-camera consistency)
kp = (TopDownPerson & key).fetch('keypoints', order_by='camera_name')
```

## Key Spaces (CRITICAL)

**Video key space:** `(video_project, filename)`
```python
video_key = {'video_project': 'CLINIC_GAIT', 'filename': 'trial_001.mp4'}
```

**Session key space:** `(participant_id, session_date)`
```python
from datetime import date
session_key = {'participant_id': '104', 'session_date': date(2023, 7, 21)}
```

**TopDownPerson key space:** `(video_project, filename, video_subject_id, top_down_method)`
```python
pose_key = {**video_key, 'video_subject_id': 0, 'top_down_method': 0}
```

## Common Queries

### Count Videos
```python
from pose_pipeline.pipeline import Video

# Total videos
total = len(Video)

# Videos in a project
count = len(Video & 'video_project="CLINIC_GAIT"')

# Multiple projects
count = len(Video & 'video_project IN ("CLINIC_GAIT", "GAIT_CONTROLS")')
```

### Count Sessions for a Participant
```python
from multi_camera.datajoint.sessions import Session

# Session uses participant_id (NOT subject_id)
count = len(Session & {'participant_id': '104'})

# With date filter
from datetime import date
count = len(Session & {'participant_id': '104'} & f'session_date > "{date(2023,1,1)}"')
```

### Find Participants with a video_project
```python
from multi_camera.datajoint.sessions import Session, Recording
from multi_camera.datajoint.multi_camera_dj import MultiCameraRecording
import numpy as np

# Navigate: Session -> Recording -> MultiCameraRecording (has video_project)
participants = np.unique(
    (Session & (Recording & (MultiCameraRecording & 'video_project="CLINIC_GAIT"'))).fetch('participant_id')
)
```

### Get 2D Keypoints
```python
from pose_pipeline.pipeline import TopDownPerson, Video

# TopDownPerson contains 2D keypoints (NOT Keypoints2D!)
key = {
    'video_project': 'CLINIC_GAIT',
    'filename': 'trial_001.mp4',
    'video_subject_id': 0,    # Person index in video
    'top_down_method': 0      # 0=MMPose, see TopDownMethodLookup
}
keypoints = (TopDownPerson & key).fetch1('keypoints')  # Shape: (T, N_joints, 3)
```

### Get 3D Lifted Keypoints (Monocular)
```python
from pose_pipeline.pipeline import LiftingPerson

key = {**pose_key, 'lifting_method': 1}  # 1=VideoPose3D
keypoints_3d = (LiftingPerson & key).fetch1('keypoints_3d')  # Shape: (T, N_joints, 4)
```

### Get 3D Triangulated Keypoints (Multi-Camera)
```python
from multi_camera.datajoint.multi_camera_dj import PersonKeypointReconstruction

# PersonKeypointReconstruction = triangulated 3D from multiple cameras
# LiftingPerson = lifted 3D from single camera (less accurate)
key = {
    'video_project': 'CLINIC_GAIT',
    'video_base_filename': 'trial_20231215_143022',
    'reconstruction_method': 0  # 0=Robust Triangulation
}
keypoints3d = (PersonKeypointReconstruction & key).fetch1('keypoints3d')
# Shape: (T, N_joints, 4) - last dim is [x, y, z, confidence], units: mm
```

### Get Kinematic Reconstruction (MUST SPECIFY METHOD!)
```python
from body_models.datajoint.kinematic_dj import KinematicReconstruction
from datetime import date

# CRITICAL: Always include kinematic_reconstruction_settings_num
key = {
    'participant_id': '102',
    'session_date': date(2023, 7, 21),
    'kinematic_reconstruction_settings_num': 137  # REQUIRED!
}

# Get from Trial part table
timestamps, qpos, joints, sites = (KinematicReconstruction.Trial & key).fetch1(
    'timestamps', 'qpos', 'joints', 'sites'
)
# qpos: (T, 41) joint angles in radians
# joints: (T, N_bodies, 3) body positions in meters
# sites: (T, N_sites, 3) marker positions in meters
```

### List Available video_projects
```python
from multi_camera.datajoint.multi_camera_dj import MultiCameraRecording
import numpy as np

projects = np.unique(MultiCameraRecording.fetch('video_project'))
```

### Get ALL Trials in a Session (Batch Query)
```python
from body_models.datajoint.kinematic_dj import KinematicReconstruction
from datetime import date

session_key = {
    'participant_id': '102',
    'session_date': date(2023, 7, 21),
    'kinematic_reconstruction_settings_num': 137
}

# Get all trial keys for this session
trial_keys = (KinematicReconstruction.Trial & session_key).fetch('KEY')

# Iterate over trials
for trial_key in trial_keys:
    qpos = (KinematicReconstruction.Trial & trial_key).fetch1('qpos')
    print(f"Trial: {trial_key}, qpos shape: {qpos.shape}")
```

### Count Videos per Project (Aggregation)
```python
from pose_pipeline.pipeline import Video
import numpy as np
from collections import Counter

projects = Video.fetch('video_project')
counts = Counter(projects)
for project, count in counts.items():
    print(f"{project}: {count} videos")
```

### Find Videos Missing Processing
```python
from pose_pipeline.pipeline import Video, TopDownPerson

# Videos without 2D pose estimation
missing_poses = Video - TopDownPerson
print(f"Videos needing pose estimation: {len(missing_poses)}")

# Get their keys
missing_keys = missing_poses.fetch('KEY')
```

## Table Relationships

```
Session (participant_id, session_date)
    -> Recording -> MultiCameraRecording (video_project, video_base_filename)
                        -> SingleCameraVideo -> Video (video_project, filename)
                        |                          -> VideoInfo (fps, timestamps)
                        |                          -> TopDownPerson (2D keypoints)
                        |                              -> LiftingPerson (lifted 3D)
                        |
                        -> CalibratedRecording -> Calibration
                        -> PersonKeypointReconstruction (triangulated 3D keypoints)

    -> SessionCalibration.Grouping
        -> KinematicReconstruction (body_scale, calibration)
            -> KinematicReconstruction.Trial (qpos, joints, sites)
```

**Two paths to 3D keypoints:**
- `LiftingPerson` - 2D→3D lifting from single camera (monocular)
- `PersonKeypointReconstruction` - Triangulation from multiple cameras (more accurate)

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| `{'subject_id': 104}` | Use `{'participant_id': '104'}` (string!) |
| `Keypoints2D` table | Use `TopDownPerson` for 2D keypoints |
| Missing method for KinematicReconstruction | Add `'kinematic_reconstruction_settings_num': 137` |
| `fetch(unique=True)` | Use `np.unique(table.fetch('field'))` |
| `fetch(as_pandas=True)` | Use `fetch(as_dict=True)` or `pd.DataFrame(fetch())` |
| `create_virtual_module()` | Direct import: `from pose_pipeline.pipeline import Video` |
| Getting subject from Video | Video has no subject; join through Session -> Recording -> MultiCameraRecording |

## Method Numbers Reference

| Pipeline | Table | Method Field | Default |
|----------|-------|--------------|---------|
| 2D Pose | TopDownPerson | `top_down_method` | 0 (MMPose) |
| 3D Lifting | LiftingPerson | `lifting_method` | 1 (VideoPose3D) |
| 3D Triangulation | PersonKeypointReconstruction | `reconstruction_method` | 0 (Robust Triangulation) |
| Multi-Camera Kinematic | KinematicReconstruction | `kinematic_reconstruction_settings_num` | **137** |
| Monocular Kinematic | MonocularReconstruction | `monocular_reconstruction_settings_num` | 1 |

## Files to Explore for More Details

| Task | File |
|------|------|
| Video/TopDownPerson schemas | `PosePipeline/pose_pipeline/pipeline.py` |
| Session/Recording schemas | `MultiCameraTracking/multi_camera/datajoint/sessions.py` |
| MultiCameraRecording schemas | `MultiCameraTracking/multi_camera/datajoint/multi_camera_dj.py` |
| KinematicReconstruction | `BodyModels/body_models/datajoint/kinematic_dj.py` |
| DataJoint principles | `PipelineOrchestrator/docs/datajoint_principles.md` |
