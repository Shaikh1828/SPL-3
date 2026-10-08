# Requirements Document: Archer Full-Body Pose Analysis & Score Prediction

## 1. Intent Analysis Summary
- **User Intent**: Add full-body video capture and pose biomechanics analysis for archers during the shooting cycle (Stance → Draw → Anchor → Release). Generate 2-3 sample shooting videos with differing form qualities. Analyze key biomechanical body points (hands, elbows, shoulders, anchor point, torso stability). Predict shot score (1-10 points / X-ring) using a trained ML model based on pose metrics and existing scoring rules. Build an end-to-end modern interface and backend API, verified by automated E2E tests under AIDLC.
- **Repository Strategy**: Developed on branch `feature/archer-pose-analysis`.
- **Scope**: Cross-system full-stack feature (Kinematic Video Generator, MediaPipe CV Pose Extraction, Biomechanics Score Prediction ML Model, FastAPI REST & Streaming APIs, React TypeScript Biomechanics Hub, Automated Tests).
- **Complexity**: High (biomechanical kinematics, multi-phase shot segmentation, computer vision landmark normalization, regression/classification inference, HTML5 canvas overlay).

---

## 2. Functional Requirements (FR)

### FR-1: Kinematic Video Generation Engine
- **FR-1.1**: Synthesize 3 realistic high-definition MP4 videos depicting an archer in side/quarter profile performing the archery shot cycle:
  - **Sample 1 (`gold_form_10.mp4`)**: Perfect Olympic form (stable stance, smooth 180° arm alignment, steady anchor at jawline for 2.2s, crisp rearward release with bow arm rock-solid → Expected Score: 10 / X).
  - **Sample 2 (`bow_arm_drop_7.mp4`)**: Form flaw — bow arm dips downward by ~6.5° upon release causing arrow drop (Expected Score: 7-8).
  - **Sample 3 (`unstable_anchor_5.mp4`)**: Form flaw — shaky anchor point, premature release, elbow out of line (Expected Score: 4-6).
- **FR-1.2**: Generate realistic human kinematics with bow riser, drawn bowstring, arrow shaft, and realistic release trajectory.
- **FR-1.3**: Store videos under `storage/sample_videos/` or `Data/pose_videos/` and serve them via backend static/API endpoints (`GET /api/pose/sample-videos`).

### FR-2: Biomechanical Pose & Landmark Extraction (MediaPipe Pose)
- **FR-2.1**: Process video frame-by-frame using MediaPipe Pose (33 3D landmarks, confidence threshold > 0.5).
- **FR-2.2**: Temporal Shot Phase Segmentation:
  - Phase 1: **Stance / Set-up** (drawing bow begins)
  - Phase 2: **Draw** (drawing hand pulls string back, bow arm extends)
  - Phase 3: **Anchor & Aim** (drawing hand anchors beneath chin/jaw, aiming hold, minimum motion)
  - Phase 4: **Release & Follow-Through** (string released, draw hand expands rearward, bow arm stability maintained)
- **FR-2.3**: Key Biomechanical Metrics Computation:
  - **Bow Arm Horizontal Alignment Angle**: Angle between bow shoulder, bow elbow, and bow wrist (ideal: ~178°-180°).
  - **Draw Elbow Elevation Angle**: Angle between bow shoulder, draw shoulder, and draw elbow (ideal: in-line with arrow axis).
  - **Anchor Hold Stability**: Standard deviation (jitter/tremor) of draw hand coordinates during anchor phase.
  - **Bow Arm Deflection at Release**: Angular drop/drift between anchor frame and +5 frames after release.
  - **Torso Verticality & Balance**: Hip-to-shoulder vertical inclination angle.

### FR-3: Machine Learning Score Prediction Model
- **FR-3.1**: Dataset Generation & Calibration:
  - Construct a dataset mapping biomechanical metric vectors to target face score distributions (1-10 points + X-ring) adhering to Olympic 10-ring target proportions.
- **FR-3.2**: Model Architecture:
  - Multi-output ML model (Gradient Boosting / Random Forest / Ridge Regression + Classifier) predicting:
    1. **Predicted Ring Score** (continuous 0.0 - 10.9 and discrete integer score 1 - 10 / X)
    2. **Score Ring Category** (Gold 10/9/X, Red 8/7, Blue 6/5, Black 4/3, White 2/1)
    3. **Biomechanical Form Score** (0 - 100%)
    4. **Prediction Confidence** (0.0 - 1.0)
    5. **Actionable Coaching Diagnostics** (e.g., "Stable anchor hold (2.1s)", "Bow arm dropped 5.8° at release", "Draw elbow elevated 4.2° too high").
- **FR-3.3**: Model Persistence:
  - Model pipeline serialized to `src/models/pose_score_model.joblib` or `models/pose_score_model.pkl` with runtime fallback heuristics.

### FR-4: Backend Service & API Layer
- **FR-4.1**: `POST /api/pose/analyze-video`: Accepts video file upload (or selected sample video identifier), runs frame-by-frame landmark extraction, segments shot phases, computes biomechanical metrics, runs ML prediction, and returns structured JSON analysis.
- **FR-4.2**: `GET /api/pose/sample-videos`: Returns metadata list and streaming URLs for the 3 generated sample videos.
- **FR-4.3**: `GET /api/pose/sample-videos/{video_id}/stream`: Streams video binary data with partial content HTTP 206 range support.
- **FR-4.4**: `POST /api/pose/predict-metrics`: Accepts manual or synthetic biomechanical feature vectors for instant score prediction.
- **FR-4.5**: Linkage with Archery Scoring: Option to record the predicted score directly into active tournament/session scorecards.

### FR-5: Modern React TypeScript Biomechanics Hub (`/pose-analysis`)
- **FR-5.1**: Dedicated Navigation item **Biomechanics** in header navigation bar.
- **FR-5.2**: Video Player & Analysis Canvas:
  - High-performance video player with overlay canvas rendering full-body skeleton landmarks, joint angle arcs, and draw line.
  - Controls: Play, pause, step frame forward/backward, playback speed (0.25x, 0.5x, 1x).
- **FR-5.3**: 1-Click Sample Video Loader:
  - Quick action buttons to load "Olympic Gold (Score 10)", "Bow Arm Drop (Score 7)", and "Unstable Anchor (Score 5)".
  - Drag-and-drop custom video upload with progress indicator.
- **FR-5.4**: Real-Time Shot Phase Timeline:
  - Interactive multi-segment progress bar showing Stance → Draw → Anchor → Release with timestamps.
- **FR-5.5**: Predicted Score & Target Radar:
  - Big Olympic Ring Score badge (e.g. `10 (Gold)`, `7 (Red)`) with animated SVG Olympic target diagram marking the predicted impact zone.
  - Overall Form Score meter (e.g. `94% Excellent Form`).
- **FR-5.6**: Biomechanical Telemetry & Coach Feedback:
  - Metric cards: Bow Arm Alignment, Draw Elbow Angle, Anchor Stability, Release Velocity.
  - Diagnostic Coach Badges (green checkmarks for good form, yellow/red alerts for detected flaws with tips).

---

## 3. Non-Functional Requirements (NFR)
- **NFR-1 (Performance)**: Video analysis for standard 5-10 second clip completes in < 4 seconds on CPU.
- **NFR-2 (Accuracy & Stability)**: Model predicts Olympic score aligned with biomechanical variance, achieving > 90% correlation on validated shot kinematics.
- **NFR-3 (UX & Aesthetics)**: Glassmorphic dark UI, micro-animations, responsive layout matching the existing high-density dashboard design system.
- **NFR-4 (Security & Safety)**: Input file validation (type check `.mp4`, `.mov`, `.avi`, size limit <= 50MB), path traversal prevention, CORS and rate-limiting compliant.
- **NFR-5 (Testability)**: 100% test pass rate with unit tests for kinematic generator, landmark extraction, ML model, and REST APIs, plus end-to-end browser verification.
