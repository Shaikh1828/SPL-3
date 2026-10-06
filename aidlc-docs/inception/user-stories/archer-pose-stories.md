# User Stories: Archer Pose Analysis & Score Prediction

## Persona Definitions
- **Coach / Scorer (Alex)**: Professional archery coach evaluating shooter biomechanics and providing form corrections.
- **Archer / Athlete (Sarah)**: Competitive archer reviewing her shooting cycle to improve consistency and score.
- **Tournament Admin (David)**: Administrator verifying scoring telemetry and AI models.

---

## User Stories

### Epic 1: Kinematic Video Generation & Sample Library
- **US-1.1**: As a Coach or Athlete, I want 1-click access to pre-generated realistic shooting videos (Gold Form 10, Bow Arm Drop 7, Unstable Anchor 5) so that I can immediately test and understand the biomechanical analysis system without needing external video files.
- **US-1.2**: As a Developer/Tester, I want programmatically generated kinematic videos with ground-truth biomechanical parameters so that unit and integration tests can run deterministically in CI.

### Epic 2: Computer Vision Pose Extraction & Phase Segmentation
- **US-2.1**: As a Coach, I want the system to automatically segment my shot into 4 phases (Stance, Draw, Anchor, Release) so that I can see exactly when each phase begins and ends.
- **US-2.2**: As an Archer, I want to see my joint angles (bow arm angle, draw elbow elevation, anchor stability) overlaid on the video with color indicators so that I can immediately identify my form flaws.

### Epic 3: Machine Learning Score Prediction
- **US-3.1**: As an Archer, I want the AI to predict my expected target score (1-10 points / X) from my body posture before or at the moment of release so that I understand how my body mechanics affect my score.
- **US-3.2**: As a Coach, I want specific diagnostic feedback cards (e.g., "Bow arm dropped by 6.2°", "Anchor tremor: high") with a Form Score (0-100%) so that I can give immediate actionable training advice.

### Epic 4: Dedicated Biomechanics Hub UI
- **US-4.1**: As a User, I want a dedicated "Biomechanics" page in the navigation bar with a video player, step-frame playback, canvas skeleton overlay, and target radar.
- **US-4.2**: As a User, I want to drag-and-drop my own video or record from a webcam so that I can analyze any archer in real-time.
- **US-4.3**: As a Scorer, I want to optionally record the predicted score into the tournament round scorecard with one click.
