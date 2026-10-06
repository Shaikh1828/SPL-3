"""
Chapter 2: Project Description Module for Bull's Eye SPL-3 Final Technical Report.
Covers System Overview, Quality Function Deployment (QFD) with House of Quality,
Requirements Classification Table (Normal, Expected, Exciting), and User Personas & Usage Scenarios.
"""

def get_chapter_2():
    return r"""---

# CHAPTER 2: PROJECT DESCRIPTION

## 2.1 System Overview & Key Capabilities

**Bull's Eye: Automated Archery Scoring System** is an enterprise-grade, intelligent sports technology ecosystem designed to automate target scoring, dispute resolution, lane management, and spectator broadcasting in professional and amateur archery competitions.

The core operational paradigm centers on non-invasive visual tracking. High-definition cameras (either IP-based RTSP streaming cameras mounted on protective lateral scaffolding or USB/CSI optical sensors positioned beside the target buttress) continuously monitor each target face. When an archer releases an arrow, the system ingests the video feed or high-resolution capture frame, computes planar homography to eliminate perspective tilt, isolates the impact point via four complementary analytical engines, evaluates World Archery (WA) radial zone boundaries, applies line-cutter tangency rules, and instantly publishes the score.

```
+---------------------------------------------------------------------------------------------------+
|                                 BULL'S EYE SYSTEM CAPABILITIES                                    |
|                                                                                                   |
|  [Hardware Ingestion]      [Vision Engine]           [Scoring & Logic]      [Client Presentation] |
|   - RTSP 1080p Cameras      - Homography Warp         - 10-Ring Radial WA    - React 18 Canvas    |
|   - USB/CSI Sensors         - Puncture Difference     - Line-Cutter Tangent  - Live Leaderboards  |
|   - Edge Stream Capture     - YOLO11 Detection        - Tie-Breaking Rules   - Judge Overrides    |
|   - Auto-Reconnect Daemon   - Multi-Tier Consensus    - Audit Trail Engine   - ReportLab PDF Docs |
+---------------------------------------------------------------------------------------------------+
```

### Key Architectural Pillars:
1. **Four-Tier Hybrid Computer Vision Engine**: Combines low-level pixel differential morphological operations with high-level deep convolutional inference (YOLO11) and geometric conic section solving. This multi-layered approach ensures that even if sudden outdoor illumination changes degrade color segmentation, morphological difference detection or deep neural bounding boxes maintain millimeter-accurate localization.
2. **Sub-200ms End-to-End Processing**: The scoring pipeline executes concurrently across asynchronous worker threads in FastAPI, ensuring that arrow coordinates, score values, and updated leaderboards reach the firing line before the archer lowers their bow.
3. **Rigorous Compliance with World Archery Rules**: The software strictly encodes WA Book 3 rules, including dedicated X-ring qualification, diameter-compensated line-cutter awards, and official round formats (e.g., 720 ranking rounds, 15-arrow match play brackets).
4. **Transparent Governance and Auditability**: While automation eliminates human scoring bias, sports governance demands human oversight. Bull's Eye provides certified judges with a high-resolution magnification interface to inspect contested shots, override algorithmic scores when necessary, and record a mandatory audit trail detailing the modification rationale.
5. **Real-Time Distributed Synchronization**: Utilizes Redis 7 as an in-memory pub/sub broker and cache, broadcasting real-time WebSocket frames to multiple synchronized client interfaces: the archer's lane monitor, the judge's tablet, and the arena spectator video board.

## 2.2 Quality Function Deployment (QFD) Analysis

Quality Function Deployment (QFD) is an established systems engineering methodology used to translate subjective stakeholder expectations—termed the Voice of the Customer (VoC)—into explicit, measurable engineering specifications. For Bull's Eye, a rigorous QFD analysis was conducted across four distinct stakeholder groups: Competitive Athletes, Certified Line Judges, Tournament Directors, and Spectators / Media Producers.

### 2.2.1 Voice of Customer (VoC) Identification

Through interviews with national archery competitors and tournament organizers, customer desires were categorized into five core dimensions:
1. **Scoring Accuracy & Fairness**: Zero tolerance for missed line-cutters; elimination of human visual parallax errors; consistent scoring under varied natural lighting.
2. **Speed & Responsiveness**: Immediate feedback at the shooting line; elimination of tedious 10-minute walks between ends to manually tally score sheets.
3. **Transparency & Dispute Resolution**: Clear visual evidence for close calls; verifiable historical logs showing every score calculation and judicial override.
4. **System Reliability & Robustness**: Tolerance to camera vibration, outdoor weather fluctuations, network dropouts, and sudden hardware disconnects.
5. **Ease of Tournament Administration**: Rapid competition setup; automated lane assignments; real-time aggregated leaderboards; one-click generation of official PDF result books.

```
+-----------------------------------------------------------------------------------+
|                        HOUSE OF QUALITY (HoQ) MATRIX                              |
|                                                                                   |
|                                [TECHNICAL METRICS]                                |
|                           (1)   (2)   (3)   (4)   (5)   (6)   (7)                 |
|                            P     L     C     O     F     A     C                  |
|                            i     a     o     v     a     u     a                  |
|                            x     t     n     e     u     d     c                  |
|                            e     e     s     r     l     i     h                  |
|                            l     n     e     r     t     t     e                  |
|                            -     c     n     i     -     a     -                  |
|                            R     y     s     d     T     b     I                  |
|                            e           u     e     o     i     n                  |
|                            s     (     s     -     l     l     v                  |
|   [CUSTOMER NEEDS]         )    ms)    %    Lat    er    ty    al                 |
|-----------------------------------------------------------------------------------|
| 1. Objective Line-Cutters  ++     +    ++    ++     o    ++     +   (Imp: 5/5)    |
| 2. Instant Shot Feedback    +    ++     +     o     +     o    ++   (Imp: 5/5)    |
| 3. High Robustness/Light   ++     o    ++     o    ++     o     o   (Imp: 4/5)    |
| 4. Transparent Disputes     +     +    ++    ++     +    ++     o   (Imp: 5/5)    |
| 5. Fast Setup & Reporting   o     +     o     o     +     +    ++   (Imp: 4/5)    |
|-----------------------------------------------------------------------------------|
| Correlation Symbols: [++] Strong Positive, [+] Positive, [o] Neutral              |
+-----------------------------------------------------------------------------------+
```
*Figure 2.1: Quality Function Deployment (QFD) House of Quality Matrix for Bull's Eye*

### 2.2.2 Requirements Classification Table

The Kano Model integrated within QFD classifies system capabilities into three essential tiers:
- **Normal Requirements**: Explicitly stated features that directly satisfy user demands.
- **Expected Requirements**: Implicit baseline attributes that users assume exist by default; failure to deliver them results in complete system rejection.
- **Exciting Requirements (Delighters)**: Innovative capabilities that exceed user expectations and distinguish the system from conventional competitors.

*Table 2.1: Quality Function Deployment (QFD) Requirements Classification Table*

| Requirement Category | Requirement Description | Technical Metric / Feature | Target Value | Customer Importance (1–5) |
| :--- | :--- | :--- | :--- | :--- |
| **Normal Requirements** | Automated Arrow Impact Localization | Sub-pixel impact coordinate extraction | Error $\le 1.0\text{ mm}$ | 5 (Critical) |
| | World Archery 10-Ring Scoring | Zone calculation & X-ring qualification | 100% rule compliance | 5 (Critical) |
| | Tournament & Session Management | Multi-lane bracket scheduling & archer assignment | $\le 10\text{ sec}$ setup | 4 (High) |
| | Live Leaderboard Display | Real-time sorting with tie-breaking criteria | Sub-100 ms refresh | 4 (High) |
| | Official Scorecard Generation | ReportLab PDF export conforming to WA format | One-click export | 4 (High) |
| **Expected Requirements** | Sub-Second Processing Latency | Frame-to-score pipeline execution time | $< 500\text{ ms}$ (Actual: 182ms)| 5 (Critical) |
| | Data Persistence & Reliability | ACID-compliant transactional PostgreSQL storage | Zero data loss | 5 (Critical) |
| | System Availability & Health | Uptime and heartbeat monitoring of cameras | $\ge 99.9\%$ uptime | 5 (Critical) |
| | Role-Based Access Control | JWT authentication separating Admin, Judge, Archer | Strict privilege isolation | 4 (High) |
| | Camera Disconnect Recovery | Automated reconnection daemon with backoff | Reconnect $\le 3\text{ sec}$ | 5 (Critical) |
| **Exciting Requirements** | Multi-Method Consensus Voting | 4-tier parallel CV algorithms with confidence fusion | $\ge 98.0\%$ accuracy | 5 (Delighter) |
| | Line-Cutter Tangency Magnifier | Interactive SVG zoom with shaft tangency overlay | Instant visual verification | 5 (Delighter) |
| | Real-Time WebSocket Streaming | Live arrow trajectory & scoreboard push to clients | $< 50\text{ ms}$ broadcast latency | 5 (Delighter) |
| | Automated Perspective Rectification | 4-point homography calibration with visual feedback | Sub-millimeter planar mapping | 4 (Delighter) |
| | Cryptographic Audit Override Trail | Immutable logging of judge overrides with reasoning | 100% audit compliance | 4 (Delighter) |

## 2.3 User Personas & Detailed Usage Scenarios

To ensure user-centered architectural design, three representative personas were developed based on key stakeholders.

### Persona 1: Tournament Director Farhan
- **Role**: Chief Tournament Organizer, National Archery Federation.
- **Demographics**: Age 44, 15 years experience in sports administration.
- **Goals**: Successfully run a 32-archer qualification and elimination tournament across 8 parallel target lanes with zero schedule delays, minimal staff overhead, and immediate publication of verified brackets.
- **Pain Points**: Paper score sheets frequently get misplaced or damaged by rain; manual double-entry of scores leads to clerical mistakes; compilation of final elimination brackets takes over an hour after the ranking round concludes.

#### Usage Scenario: Tournament Creation & Execution
1. Farhan logs into the Bull's Eye web application using his Administrator credentials.
2. Navigates to the **Tournaments** view and clicks "Create Tournament", naming it *"National Recurve Championship 2026"*, setting the competition type to *World Archery 70m Recurve*, 72 arrows (12 ends of 6 arrows).
3. Assigns 8 target cameras to Lanes 1 through 8. The system executes automated RTSP ping healthchecks and displays green status indicators.
4. Registers the 32 participating archers and auto-allocates them to target lanes.
5. Initiates the tournament session. During competition, Farhan monitors the **Executive Dashboard**, which visualizes live lane progression, current end numbers, and system latency metrics.
6. Upon completion of the final end, Farhan clicks "Export Official Report". The system instantly generates a comprehensive, publication-ready PDF tournament book containing complete end-by-end scorecards, ranking tables, tie-break results, and audit histories.

---

### Persona 2: National Archer Nafisa
- **Role**: Competitive Recurve Archer, National Training Squad.
- **Demographics**: Age 22, aiming for Olympic qualification.
- **Goals**: Receive instantaneous, reliable visual confirmation of arrow groupings at the shooting line so she can adjust her sight pins in real time; track her historical scoring trends and end-by-end consistency.
- **Pain Points**: Straining through a spotting scope at 70 meters is physically fatiguing and often inconclusive in windy or overcast conditions; walking down the field after every end breaks mental concentration and creates muscle fatigue over 72 arrows.

#### Usage Scenario: Live Training & Match Feedback
1. Nafisa stands at Lane 3 with a tablet mounted beside her bow stand connected to Bull's Eye.
2. She draws, anchors, and releases Arrow 1.
3. Within 182 milliseconds of target impact, the Bull's Eye interactive canvas displays an animated pulse at the precise millimeter coordinates of the impact. The display updates: *"End 1, Arrow 1: 10 points (Inner-10 X)"*.
4. She shoots Arrows 2 through 6. The tablet overlays her grouping ellipse, displays her running end total (58/60), and calculates her cumulative average arrow score (9.67).
5. At the conclusion of the session, Nafisa reviews the **Analytics Dashboard**, analyzing her arrow dispersion scatter plot and historical performance graphs across all ends.

---

### Persona 3: Certified Line Judge Rashed
- **Role**: World Archery International Judge.
- **Demographics**: Age 51, certified for continental and World Cup competitions.
- **Goals**: Resolve contested arrow calls rapidly, objectively, and impartially while maintaining full procedural integrity and compliance with World Archery regulations.
- **Pain Points**: Walking down the range for every borderline arrow creates significant delays; physical inspection with a hand lens can be subjective and disputed by team coaches; paper dispute appeal forms create substantial administrative burden.

#### Usage Scenario: Disputed Arrow Inspection & Audit Override
1. During End 4 on Lane 2, an arrow impacts right on the border separating the 9-ring and the 10-ring.
2. The Bull's Eye vision engine identifies the impact and, applying the shaft tangency line-cutter algorithm, automatically awards a score of *10*.
3. The opposing archer requests a formal judicial review.
4. Judge Rashed opens the **Scoring & Review Console** on his official tablet. He navigates to Lane 2, End 4, Arrow 3.
5. The interface provides a 4x magnified, perspective-rectified crop of the impact zone, displaying the computed arrow center, shaft perimeter circle ($\delta = 2.5\text{ mm}$), and the dividing line coordinates.
6. Rashed verifies that the arrow shaft physically broke the dividing line. He confirms the score.
7. Had the shaft failed to touch the line, Rashed could click "Override Score", change the value to *9*, and enter a mandatory explanation (*"Physical shaft failed to touch 10-ring boundary line on microscopic review"*).
8. The system writes an immutable audit record to the `audit_logs` table, synchronizes the updated leaderboard via WebSockets, and notifies all connected clients with a visible judicial badge.
"""
