# Requirements Clarification Questions: Archer Pose Analysis & Score Prediction

Please review and answer the following questions to finalize the requirements and architecture for this feature. Fill in your preferred choice after each `[Answer]:` tag (e.g., `[Answer]: A` or custom notes).

---

## Question 1: Repository & Code Organization ("ekta new repo banao")
Regarding the repository setup for this feature:

A) **(Recommended)** Integrated into current repo on a dedicated Git branch (e.g. `feature/archer-pose-analysis`) — keeps the existing FastAPI backend and React frontend cohesive, allows direct linking between target scores and archer pose data, while keeping `main` safe.
B) Integrated directly into current repo on `main` branch with dedicated backend module (`src/services/pose_analysis_service.py`, `src/api/pose.py`) and frontend route (`/pose-analysis`).
C) Standalone sub-directory / standalone repository within the workspace (e.g., `archer-pose-service/`) running as an independent microservice.
D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 2: Video Generation Approach (2-3 Sample Shooting Videos)
For generating the 2-3 test videos of archers shooting:

A) **(Recommended)** Programmatic CV & Kinematic Video Generator — creates 2-3 realistic MP4 video clips with an archer executing the 4 shot phases (Stance → Draw → Anchor → Release) with distinct biomechanical variations:
   - Video 1: "Olympic Gold Form" (steady anchor, 180° arm alignment, clean release → Predicted Score: 10 / X)
   - Video 2: "Bow Arm Drop Fault" (arm dips during release → Predicted Score: 7-8)
   - Video 3: "Unstable Anchor / Premature Release" (shaky draw elbow, flinched release → Predicted Score: 4-6)
B) Rendered high-framerate animated silhouette / avatar videos with overlaid target trajectory.
C) Bundle curated real-world archery footage alongside programmatic kinematic test videos.
D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 3: Biomechanical Pose Analysis & Keypoints
Which biomechanical metrics should the AI pipeline extract and analyze from the archer's body?

A) **(Recommended)** Comprehensive Olympic Biomechanics Suite (MediaPipe Pose 33 3D landmarks):
   - Bow arm stability & horizontal alignment angle (Shoulder - Elbow - Wrist)
   - Draw elbow elevation angle relative to arrow line
   - Anchor point position & hold duration / tremor variance
   - Torso posture & center-of-mass balance
   - Post-release follow-through deflection velocity
B) Hand and Arm focused only (wrist stability, draw fingers, draw elbow angle).
C) Dual-object tracking (body pose keypoints + bow riser vertical tilt).
D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 4: Score Prediction Model
How should the score prediction model be constructed based on existing data and biomechanics?

A) **(Recommended)** Multi-Output Supervised ML Model (Trained Gradient Boosting / Random Forest + Neural Regressor):
   - Predicts exact arrow ring score (1 to 10 points / X-ring)
   - Predicts confidence interval and hit zone category (Gold / Red / Blue / Black / White)
   - Produces a Biomechanical Execution Score (0-100%) and actionable coaching recommendations
B) PyTorch Temporal Sequence Model (LSTM / 1D-CNN) processing landmark coordinates across consecutive video frames.
C) Heuristic rule-based physics engine calibrated against World Archery target dimensions.
D) Other (please describe after [Answer]: tag below)

[Answer]:  A

---

## Question 5: User Interface Scope & Design ("at first interface ta a-z thik koro")
How should the user interface be organized and presented?

A) **(Recommended)** Premium Dedicated Biomechanics Hub (`/pose-analysis`):
   - Modern dark-mode interface with live webcam feed or video file drag-and-drop
   - 1-Click quick load buttons for the 2-3 generated sample videos
   - Canvas with real-time skeleton overlay, color-coded joints, and angle arcs
   - Shot Phase Timeline bar (Stance → Draw → Anchor → Release)
   - Olympic Target Radar & Score Prediction Gauge (Predicted Score: 1-10 / X)
   - Biomechanical Flaw & Coach Feedback Cards (e.g., "Bow Arm dropped 5.2° at T+2.1s")
   - Session comparison and exportable PDF/JSON biomechanics report
B) Integrated directly into the existing Scoring page (`/scoring`) as a split-screen camera mode.
C) Standalone coach-only popout telemetry viewer.
D) Other (please describe after [Answer]: tag below)

[Answer]: A
