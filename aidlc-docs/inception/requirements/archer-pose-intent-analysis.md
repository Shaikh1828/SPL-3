# Intent Analysis: Archer Full-Body Pose Analysis & Score Prediction

## User Request Summary
> "get the full context of my project. ekta new repo banao. ekhane ekta large new feature add korte hobe. archer shoot korar somoy tar full bodyr image capture korbe, etar jonno umi 2-3ta video generate koro. oi video theke archer er haat and body r bivinno point analysis kore ekta prediction dibe tar score koto hote pare. apatoto jei data ase oi datar upor vitti kore ekta model daar korao. at first interface ta a-z thik koro. sath backend eo ja ja lagbe ta add koro. Sob kisu aidlc use kore valovabe plan kore implement koro. then e2e test korba."

## Request Breakdown & Core Objectives
1. **Full Project Context Acquisition**: Complete analysis of `SPL-3` (FastAPI + React 18 + OpenCV WA target scoring + SQLite/Postgres + Redis).
2. **Repository Topology**: Resolve user intent for "ekta new repo banao" (branch vs standalone sub-repo vs integrated module).
3. **Archer Shooting Video Generation**: Programmatically generate 2-3 test videos depicting archers shooting across 4 shot phases (Stance, Draw, Anchor, Release) with different biomechanical execution forms (Gold 10/X vs Fault 7-8 vs Flinch 4-6).
4. **Computer Vision Pose & Landmark Analysis**: Extract full-body keypoints (hands, elbows, shoulders, anchor point, torso) using MediaPipe Pose.
5. **Score Prediction Model**: Build an ML model predicting shot score (1-10 points / X-ring) and execution stability based on existing target scoring rules/data and extracted biomechanics.
6. **End-to-End User Interface ("a-z thik koro")**: Build a rich, modern, dynamic web UI with video loading/playback, real-time skeleton overlays, shot-phase timeline, predicted score gauge, and coach feedback cards.
7. **Backend Infrastructure**: Implement FastAPI routes (`/api/pose/*`), service logic, and model inference.
8. **AIDLC Governance**: Execute Inception, Construction, and Testing phases with comprehensive documentation in `aidlc-docs/` and audit logging in `aidlc-docs/audit.md`.
9. **E2E Testing**: Automated unit, integration, and browser/system e2e tests.

## Initial Scope & Complexity Estimate
- **Scope Level**: System-wide feature addition (ML Pipeline + Backend APIs + Frontend UI Module + Synthetic Media Generation + Automated Tests).
- **Complexity**: High / Moderate-High (Kinematic video synthesis, MediaPipe integration, ML score regression/classification, interactive HTML5 Canvas skeleton overlay).
- **Requirements Depth**: Comprehensive.
