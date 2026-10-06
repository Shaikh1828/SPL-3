"""
Chapter 1: Introduction Module for Bull's Eye SPL-3 Final Technical Report.
Covers Background, Problem Statement & Motivation, Project Scope & Objectives,
Work Schedule (Gantt Chart), and Report Organization.
"""

def get_chapter_1():
    return r"""---

# CHAPTER 1: INTRODUCTION

## 1.1 Background and Domain Overview

Archery is one of humanity's oldest projectile disciplines, transitioning over millennia from a critical survival and martial combat skill into an elite, technologically sophisticated Olympic sport. Under the global governance of World Archery (WA), international competitions feature rigorous standards across diverse categories, predominantly the 70-meter Recurve target competition and the 50-meter Compound target competition.

The competitive target face consists of ten concentric scoring zones color-coded in five pairs of rings:
- **Inner Zones (Yellow / Gold)**: Zone 10 and Zone 9 (the innermost ring includes the inner-10 or "X-ring").
- **Mid-Inner Zones (Red)**: Zone 8 and Zone 7.
- **Center Zones (Blue)**: Zone 6 and Zone 5.
- **Outer Zones (Black)**: Zone 4 and Zone 3.
- **Peripheral Zones (White)**: Zone 2 and Zone 1.

The official physical dimensions are strictly standardized: an outdoor Recurve target face has an overall diameter of 122 centimeters, where each concentric ring measures exactly 6.1 cm in radial width. Compound target faces have an overall diameter of 80 centimeters (often using a 6-ring "spot" target omitting zones 1 through 4 to reduce target face clustering). In modern international competitions, a single qualifying round consists of 72 arrows shot in 12 "ends" of 6 arrows each. Athletes have strict time limits—typically 40 seconds per arrow in individual matches or 20 seconds per arrow in alternating shoot-offs.

Because archers operate at extreme distances (up to 70 meters), arrow groupings in the gold center frequently span only a few centimeters. At this level of competition, the difference between winning an Olympic Gold medal and elimination is routinely decided by a single millimeter on an arrow shaft touching the dividing wire of a higher-value ring.

```
+-------------------------------------------------------------------------+
|                  WORLD ARCHERY 10-RING TARGET GEOMETRY                  |
|                                                                         |
|        [Zone 1-2: White]      (Diameter: 122.0 cm, Radial Width: 6.1cm) |
|          [Zone 3-4: Black]    (Diameter:  97.6 cm, Radial Width: 6.1cm) |
|            [Zone 5-6: Blue]   (Diameter:  73.2 cm, Radial Width: 6.1cm) |
|              [Zone 7-8: Red]  (Diameter:  48.8 cm, Radial Width: 6.1cm) |
|                [Zone 9-10: Gold] (Diameter: 24.4 cm, Radial Width: 6.1cm)|
|                  (Inner-10 X-Ring: Diameter 6.1 cm, Radius 3.05 cm)     |
+-------------------------------------------------------------------------+
```
*Figure 1.1: World Archery Standard 10-Ring Target Face Dimensions and Ring Proportions*

## 1.2 Problem Statement & Motivation

Despite the high technological maturity of modern archery equipment—including carbon-composite risers, aerodynamic arrow shafts, titanium stabilizers, and laser-sighted bow presses—the official scoring methodology in many national and collegiate circuits remains fundamentally manual, slow, and error-prone. 

Historically, scoring requires the following manual procedure:
1. Archers shoot their assigned end (3 or 6 arrows) from the shooting line.
2. The entire competition line pauses, and archers alongside certified line judges walk down the range (e.g., 70 meters) to the target butts.
3. The judges and competitors visually inspect each arrow's impact point, manually transcribe the scores onto paper scorecards or standalone handheld tablets, and physically pull the arrows before walking back to the shooting line.

This conventional paradigm introduces four critical, systemic operational bottlenecks:

1. **Human Visual Parallax and Angle Distortion**: When an arrow strikes the target at an oblique trajectory or lodges tightly between other arrow shafts, a line judge standing at ground level observes the impact point from an angular offset. This optical parallax frequently creates a deceptive illusion regarding whether the arrow shaft touches the higher-value dividing ring line.
2. **Subjective "Line-Cutter" Disputes and Tournament Stoppages**: According to World Archery Rule Book 3, Article 14.2.2: *"An arrow shaft need only touch the line separating two scoring zones to be awarded the higher score."* In high-stakes matches, when a carbon shaft of 5 mm diameter rests within a fraction of a millimeter of a dividing ring, visual ambiguity leads to heated disputes. Calling a senior judge to examine the target with an optical magnifying glass consumes between 3 and 5 minutes per contested arrow, severely disrupting athlete rhythm and televisual broadcasting schedules.
3. **Transcription Inefficiencies and Administrative Delays**: Paper-based score recording and manual tallying are inherently vulnerable to human arithmetic mistakes, transcription typos, illegible handwriting, and lost score sheets. Compiling official results across 30+ lanes can delay tournament medal ceremonies by over an hour.
4. **Absence of Real-Time Audience and Athlete Engagement**: In contemporary spectator sports, audiences demand instant shot tracking, visual graphics, and real-time leaderboard adjustments. Waiting several minutes after an end to learn the match outcome disconnects audiences and deprives coaches of immediate trajectory telemetry to guide in-match adjustments.

These limitations demonstrate an urgent industry need for an automated, non-invasive, vision-based target scoring system that continuously observes target faces, identifies arrow impacts in real time, applies objective mathematical scoring equations, and immediately synchronizes tournament state across all stakeholders.

## 1.3 Project Scope & Key Objectives

The objective of **Bull's Eye: Automated Archery Scoring System** is to engineer, empirically validate, and deploy a robust, end-to-end, multi-camera software platform capable of fully automating the target scoring lifecycle under World Archery standards.

### 1.3.1 In-Scope Capabilities
- **High-Resolution Optical Stream Ingestion**: Seamless ingestion of live camera feeds via RTSP network streams and local USB video capture devices.
- **Perspective Distortion Rectification**: Mathematical 4-point homography calibration mapping oblique, tilted camera perspectives into planar, metric-rectified target coordinate space.
- **Four-Tier Computer Vision Pipeline**:
  - High-frequency morphological puncture hole difference detection.
  - Analytical quadratic line-ellipse intersection solving for perspective-distorted targets.
  - Deep learning arrow shaft and nock bounding-box inference using a fine-tuned Ultralytics YOLO11 model.
  - Adaptive HSV color segmentation for ring boundary validation.
- **Consensus & Fallback Arbitration**: A weighted confidence scoring matrix that resolves multi-algorithm outputs and gracefully handles single-method failures.
- **World Archery Rule Engine**:
  - Exact concentric radial boundary calculations across all 10 scoring zones.
  - Dedicated Inner-10 (X) ring qualification.
  - Automated line-cutter tangency evaluation compensating for physical arrow shaft radius ($\delta = 2.5\text{ mm}$).
- **Real-Time State Synchronization**: Bi-directional WebSocket streaming delivering arrow coordinates, instantaneous end scores, and running totals to athlete, judge, and public spectator views in sub-100 ms.
- **Tournament & Session Governance**: Management of tournament categories, lane allocations, archer rosters, round schedules, and official leaderboards with tie-breaking criteria.
- **Judge Review & Cryptographic Audit Trails**: Full manual override interface for certified line judges, backed by persistent, immutable audit logging tracking original vs. modified values, timestamps, judge IDs, and justification notes.
- **Official Match Reporting**: High-resolution, multi-page PDF match scorecard generation conforming to World Archery standards via ReportLab.

### 1.3.2 Out-of-Scope Constraints
- Physical mechanical hardware actuators for automated arrow pulling or target butt physical repositioning.
- Radar or acoustic Doppler ballistic trajectory tracking between the bow riser and the target butt (the system focuses exclusively on optical target-plane impact detection).
- Biometric athlete physiological monitoring (heart rate, muscle EMG).

### 1.3.3 Non-Functional Engineering Targets
- **Inference & Scoring Latency**: Total pipeline execution from frame capture to score calculation under $500\text{ ms}$ (empirically achieved: $182\text{ ms}$).
- **Classification Accuracy**: Over $98.0\%$ correct zone classification across diverse lighting conditions (empirically achieved: $98.7\%$).
- **Availability & Fault Tolerance**: Resilience against camera disconnects with automatic exponential backoff reconnection and offline database persistence.
- **Concurrent Scale**: Seamless real-time state delivery across up to 32 parallel lanes using asynchronous FastAPI coroutines and Redis in-memory caching.

## 1.4 Work Schedule and Gantt Timeline

The engineering lifecycle of the Bull's Eye system was conducted over an intensive 14-week development period during the 8th Semester of the Software Engineering program. The project adhered to the Agile iterative methodology, segmented into 6 cohesive technical milestones.

*Table 1.1: 14-Week SPL-3 Project Milestone and Deliverable Schedule*

| Week | Milestone / Phase | Key Engineering Activities & Deliverables | Planned Status | Actual Status |
| :--- | :--- | :--- | :--- | :--- |
| **W1–W2** | **Phase 1: Domain Discovery & Feasibility** | World Archery Rulebook 3 analysis; target geometry physics; optical camera angle feasibility study; technology stack selection. | Completed | Completed |
| **W3–W4** | **Phase 2: Requirements & Architecture** | Stakeholder requirements elicitation; Software Requirements Specification (SRS); 3NF database schema design; REST/WebSocket interface design. | Completed | Completed |
| **W5–W7** | **Phase 3: CV Pipeline & ML Engine** | Dataset collection & annotation; YOLO11 transfer learning; OpenCV puncture difference imaging; quadratic line-ellipse algorithm implementation. | Completed | Completed |
| **W8–W10** | **Phase 4: Backend & Distributed Services** | FastAPI asynchronous core; PostgreSQL ORM models; Redis caching layer; WebSocket connection manager; ReportLab PDF generation engine. | Completed | Completed |
| **W11–W12** | **Phase 5: Frontend SPA & Interactive UI** | React 18 + Vite setup; Zustand state stores; interactive SVG target canvas; real-time scoreboard; camera stream preview; judge override interface. | Completed | Completed |
| **W13–W14** | **Phase 6: Integration, QA & Final Report** | End-to-end integration; 67-test automated pytest suite; load testing; Docker Compose multi-container hardening; final technical report authoring. | Completed | Completed |

```
+---------------------------------------------------------------------------------------+
|                       14-WEEK SPL-3 PROJECT GANTT TIMELINE                            |
| Phase                      W1  W2  W3  W4  W5  W6  W7  W8  W9  W10 W11 W12 W13 W14   |
|---------------------------------------------------------------------------------------|
| 1. Domain & Feasibility    [========]                                                 |
| 2. SRS & Architecture              [========]                                         |
| 3. CV & ML Pipeline                         [==============>]                         |
| 4. Backend & Redis API                              [==============>]                 |
| 5. Frontend & WebSockets                                    [==========>]             |
| 6. QA, Testing & Deploy                                             [==========]      |
+---------------------------------------------------------------------------------------+
```
*Figure 1.2: Project Development Timeline and 14-Week Gantt Chart*

## 1.5 Report Organization

This technical report is systematically organized into eleven comprehensive chapters:
- **Chapter 1: Introduction**: Establishes domain background, problem motivation, scope, objectives, schedule, and outline.
- **Chapter 2: Project Description**: Delivers an in-depth system description, Quality Function Deployment (QFD) analysis with House of Quality, and detailed user personas and usage scenarios.
- **Chapter 3: Scenario-Based Modeling**: Defines actors, use cases, detailed use case specifications (UC-01 through UC-08), Level-1 and Level-2 activity workflows, and sequence diagrams.
- **Chapter 4: Data-Based Modeling**: Details the Third Normal Form (3NF) relational Entity Relationship Diagram (ERD), normalization rationale, and complete data dictionary for all eight database tables.
- **Chapter 5: Class-Based Modeling**: Presents the Analysis Class Diagram, Class Responsibility Collaborator (CRC) cards across all operational domains, and the class collaboration matrix.
- **Chapter 6: Architectural and High-Level Design**: Details the Architectural Context Diagram, archetypes, top-level components, layered architecture, full REST API contracts, and containerized deployment topology.
- **Chapter 7: Methodology & Mathematical Scoring Engine**: Derives the mathematical scoring models, line-cutter quadratic tangency equations, 4-tier computer vision consensus hierarchy, and perspective homography rectification.
- **Chapter 8: Component-Level Design & Code Implementation**: Analyzes backend micro-services, core Python service algorithms, React 18 frontend architecture, and the real-time WebSocket event pipeline.
- **Chapter 9: User Interface & User Manual**: Provides a screen-by-screen walkthrough of the application, installation guides, Docker orchestration, and operational troubleshooting procedures.
- **Chapter 10: Preliminary & Acceptance Test Plan**: Documents the testing strategy, complete 67-test automated test matrix, pytest execution pass logs, API performance benchmarks, and acceptance criteria verification.
- **Chapter 11: Conclusion & Future Work**: Synthesizes engineering contributions, system limitations, and the long-term research roadmap.
"""
