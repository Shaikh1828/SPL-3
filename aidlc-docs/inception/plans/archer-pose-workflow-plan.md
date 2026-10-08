# Workflow Plan: Archer Pose Biomechanics Analysis & Score Prediction

## Units of Work Breakdown

We structure the construction phase into 4 focused units of work:

```
               [Unit 1: Kinematic Video Generator]
                                |
                                v
               [Unit 2: Pose CV & ML Prediction Service]
                                |
                                v
               [Unit 3: FastAPI Backend API Layer]
                                |
                                v
               [Unit 4: React Biomechanics Hub UI]
                                |
                                v
               [Unit 5: Integration & E2E Testing]
```

### Unit 1: Programmatic Kinematic Video Synthesis
- **Deliverables**:
  - `src/services/kinematic_video_generator.py`: Generates 3 realistic MP4 video clips (`gold_form_10.mp4`, `bow_arm_drop_7.mp4`, `unstable_anchor_5.mp4`) simulating an archer in side profile executing the 4 shot phases with bow, arrow, and body kinematics.
  - CLI script `scripts/generate_sample_videos.py` to pre-generate and store assets in `storage/sample_videos/`.
  - Verification: Generated videos playable and contain detectable human pose keypoints.

### Unit 2: Biomechanical Pose Extraction & Score Prediction Model
- **Deliverables**:
  - `src/services/pose_analysis_service.py`: Uses MediaPipe Pose to extract 33 landmarks per frame, segment temporal shot phases, and extract key biomechanical stability features.
  - `src/services/pose_score_model.py`: Trains and runs ML regressor/classifier predicting target ring score (1-10 / X), form percentage (0-100%), and coaching diagnostics.
  - Dataset generation calibrated against World Archery 10-ring score distributions.
  - Serialization and persistence of trained model artifact.

### Unit 3: FastAPI Backend API Layer & Routers
- **Deliverables**:
  - `src/api/pose.py`:
    - `GET /api/pose/sample-videos`: List sample videos with metadata.
    - `GET /api/pose/sample-videos/{video_id}/stream`: Stream video bytes (supports HTTP 206 partial content).
    - `POST /api/pose/analyze-video`: Upload video file or pass `video_id`, returns frame landmarks, phases, metrics, and predicted score.
    - `POST /api/pose/predict-metrics`: Direct feature vector evaluation.
  - Registration in `src/main.py`.
  - Rate limiting, file validation, security safeguards.

### Unit 4: Frontend Biomechanics Hub (`/pose-analysis`)
- **Deliverables**:
  - New page `frontend/src/pages/PoseAnalysisPage.tsx`.
  - Navigation link in `frontend/src/components/Navbar.tsx` (or header).
  - Video Player + interactive HTML5 Canvas skeleton & angle overlay.
  - Sample video 1-click quick selector cards.
  - Shot Phase Timeline bar (Stance → Draw → Anchor → Release).
  - Olympic Target Ring Impact Radar & Predicted Score gauge (1-10 / X).
  - Biomechanics Metric Cards & Diagnostic Coach Badges.
  - API client `frontend/src/api/pose.ts` & TypeScript types in `frontend/src/types/index.ts`.

### Unit 5: Verification & Automated E2E Testing
- **Deliverables**:
  - Backend tests: `tests/test_pose_service.py` and `tests/test_pose_api.py`.
  - Frontend production build check (`npm run build`).
  - End-to-end browser verification of `/pose-analysis` via browser testing subagent.
