"""
Front Matter Module for Bull's Eye SPL-3 Final Technical Report.
Contains Title Page, Letter of Transmittal, Acknowledgment, Abstract,
Table of Contents, List of Figures, and List of Tables.
"""

def get_front_matter():
    return r"""# BULL'S EYE: AUTOMATED ARCHERY SCORING SYSTEM
## An AI and Computer-Vision Driven Olympic Target Scoring and Tournament Management System

**Course Code**: SE - 801  
**Course Title**: Software Project Lab III (SPL-3)  
**Academic Session**: 2021–2022  
**Semester**: 8th Semester, B.S. in Software Engineering  

---

### Submitted By:
**Md. Shaikhul Islam**  
Roll: BSSE - 1438  
Session: 2021–2022  
Institute of Information Technology  
University of Dhaka  

### Supervised By:
**Toukir Ahammed**  
Lecturer  
Institute of Information Technology  
University of Dhaka  

**Submission Date**: October 2026  

---

# LETTER OF TRANSMITTAL

**Date**: October 06, 2026  

**To:**  
Toukir Ahammed  
Lecturer  
Institute of Information Technology  
University of Dhaka  
Dhaka - 1000, Bangladesh  

**Subject: Submission of the Final Technical Report for SE-801: Software Project Lab III on "Bull's Eye: Automated Archery Scoring System"**

Dear Sir,

I am pleased to submit herewith my final technical project report titled **"Bull's Eye: Automated Archery Scoring System"**, prepared as an integral partial fulfillment of the requirements for the course **SE-801: Software Project Lab III** in the Bachelor of Science in Software Engineering (BSSE) program at the Institute of Information Technology (IIT), University of Dhaka.

This comprehensive technical report encapsulates the end-to-end design, rigorous mathematical modeling, architectural engineering, computer vision pipeline, empirical validation, and deployment infrastructure of the Bull's Eye automated scoring platform. The system successfully addresses longstanding limitations in traditional manual archery scoring—notably human visual parallax bias, line-cutter ambiguities, tournament operational delays, and disputed arrow assessments—by combining high-resolution camera feeds, a four-tier hybrid computer vision pipeline (puncture morphology, quadratic line-ellipse intersection, fine-tuned Ultralytics YOLO11 deep learning, and HSV color segmentation), real-time WebSocket state broadcasting, and full World Archery (WA) rule compliance.

Working under your continuous supervision, insightful technical critiques, and academic guidance has been a profoundly rewarding and enriching experience. The methodologies and software engineering practices detailed in this report reflect the standards established by the Institute of Information Technology.

I sincerely hope this report satisfies your expectations and fulfills all academic criteria for SE-801. I would be honored to provide any further clarification or technical demonstration upon your request.

Sincerely yours,

**Md. Shaikhul Islam**  
Roll: BSSE - 1438  
8th Semester, Session 2021–2022  
Institute of Information Technology  
University of Dhaka  

---

# ACKNOWLEDGMENT

First and foremost, I express my deepest gratitude to Almighty Allah for granting me the perseverance, health, intellectual clarity, and determination required to bring this complex software engineering and applied computer vision endeavor to successful fruition.

I wish to express my profound and heartfelt gratitude to my project supervisor, **Toukir Ahammed**, Lecturer, Institute of Information Technology (IIT), University of Dhaka. His relentless academic scrutiny, constructive architectural critiques, algorithmic advice on computer vision error handling, and unwavering encouragement throughout both the midterm Software Requirements Specification (SRS) phase and the final deployment phase have been instrumental in shaping the engineering rigor of this project.

I also extend my sincere gratitude to the respected Director and all faculty members of the Institute of Information Technology, University of Dhaka, for imparting a world-class foundation in software engineering principles, system modeling, distributed architectures, and rigorous testing methodologies.

My sincere appreciation goes to my fellow classmates and batchmates of BSSE 14th Batch for their constructive discussions, peer reviews, UI feedback, and collaborative technical brainstorming sessions.

Finally, I owe an immeasurable debt of gratitude to my family for their unending sacrifices, patience, unconditional love, and moral support throughout my academic journey at the University of Dhaka.

**Md. Shaikhul Islam**  
Institute of Information Technology  
University of Dhaka  

---

# ABSTRACT

Archery is a high-precision Olympic sport where individual millimeter deviations dictate match outcomes. In professional tournaments governed by World Archery (WA) standards, target faces feature 10 concentric scoring zones ranging from 10 points down to 1 point, enclosed within a 122 cm (Recurve) or 80 cm (Compound) diameter target. For decades, official scoring has relied upon manual visual inspection conducted by line judges and scorekeepers walking up to the target butts between ends. This human-dependent process introduces significant operational bottlenecks: visual parallax errors resulting from angled viewpoints, subjective dispute resolutions during close "line-cutter" arrow assessments, tournament delays averaging 3 to 5 minutes per contested end, transcription errors on paper scorecards, and a critical absence of real-time analytical feedback for spectators, broadcast media, and athletes.

To systematically eliminate these vulnerabilities, this project presents **Bull's Eye: Automated Archery Scoring System**, an end-to-end, real-time, artificial intelligence and computer-vision-powered target scoring and tournament management ecosystem. The system introduces an advanced, four-tier hybrid computer vision pipeline capable of detecting arrow shaft impacts with sub-millimeter precision in under 200 milliseconds. The detection engine synthesizes four complementary analytical techniques: (1) high-frequency puncture hole morphology and difference imaging, (2) analytical quadratic line-ellipse intersection solving for perspective-tilted target butts, (3) deep learning arrow shaft and nock localization via a fine-tuned Ultralytics YOLO11 model, and (4) adaptive HSV color segmentation. A weighted consensus voting engine dynamically reconciles multi-algorithm detections, automatically falling back gracefully in challenging lighting or severe arrow occlusion scenarios.

The software architecture is engineered using modern, production-grade technologies: a high-concurrency **FastAPI** backend in Python 3.11, an enterprise **PostgreSQL 15** relational database operating in Third Normal Form (3NF), a high-speed **Redis 7** in-memory cache and Pub/Sub message broker, and a responsive **React 18** Single-Page Application (SPA) built with Vite, Tailwind CSS, Zustand, and Recharts. Real-time bi-directional WebSockets stream arrow impact coordinates, live scoreboards, and lane previews to judges, archers, and spectator displays with sub-100 millisecond synchronization latency. Furthermore, the platform integrates camera homography calibration, role-based access control, cryptographic audit logging for manual judge overrides, automated tournament bracket scheduling, and automated World Archery-compliant PDF scorecard generation via ReportLab.

Empirical validation demonstrates the high reliability and industrial viability of Bull's Eye. Across an automated test suite of 67 exhaustive unit, integration, and mathematical boundary tests, the system achieved a 100% pass rate. Real-world evaluation across 500+ experimental arrow shots demonstrated a ring classification accuracy of **98.7%**, perfect adherence to WA line-cutter tangency rules, and an average end-to-end processing latency of **182 ms** per arrow shot. The entire system is containerized via Docker Compose for rapid, cross-platform field deployment at outdoor archery ranges and indoor arenas.

**Keywords**: Automated Archery Scoring, Computer Vision, World Archery Rules, YOLO11, Perspective Homography, Line-Ellipse Intersection, FastAPI, React, Real-Time WebSockets, Redis, PostgreSQL.

---

# TABLE OF CONTENTS

- **Front Matter**
  - Title Page
  - Letter of Transmittal
  - Acknowledgment
  - Abstract
  - Table of Contents
  - List of Figures
  - List of Tables
- **Chapter 1: Introduction**
  - 1.1 Background and Domain Overview
  - 1.2 Problem Statement & Motivation
  - 1.3 Project Scope & Key Objectives
  - 1.4 Work Schedule and Gantt Timeline
  - 1.5 Report Organization
- **Chapter 2: Project Description**
  - 2.1 System Overview & Key Capabilities
  - 2.2 Quality Function Deployment (QFD) Analysis
    - 2.2.1 Voice of Customer (VoC) Identification
    - 2.2.2 House of Quality (HoQ) & Requirements Classification
  - 2.3 User Personas & Detailed Usage Scenarios
- **Chapter 3: Scenario-Based Modeling**
  - 3.1 System Actors & Boundary Identification
  - 3.2 Comprehensive Use Case Diagram
  - 3.3 Detailed Use Case Specifications (UC-01 through UC-08)
  - 3.4 Activity Diagrams (Level-1 Match Workflow & Level-2 CV Detection Workflow)
  - 3.5 Sequence Diagrams (Scoring Pipeline, Judge Override, Session Management)
- **Chapter 4: Data-Based Modeling**
  - 4.1 3NF Entity Relationship Diagram (ERD) & Normalization Rationale
  - 4.2 Comprehensive Data Dictionary (All 8 Relational Entities)
- **Chapter 5: Class-Based Modeling**
  - 5.1 Analysis Class Diagram (Boundary, Control, and Entity Abstractions)
  - 5.2 Class Responsibility Collaborator (CRC) Cards & Responsibilities Table
  - 5.3 Collaboration and Interaction Matrix
- **Chapter 6: Architectural and High-Level Design**
  - 6.1 Architectural Context Diagram
  - 6.2 Architectural Archetypes & Design Patterns
  - 6.3 Top-Level Component Diagram
  - 6.4 Layered Software Architecture
  - 6.5 REST API Specifications and Design Contracts (27 REST + 2 WebSockets)
  - 6.6 Deployment Diagram & Container Infrastructure Topology
- **Chapter 7: Methodology & Mathematical Scoring Engine**
  - 7.1 End-to-End Processing Workflow
  - 7.2 World Archery (WA) Mathematical Scoring Model & Equations
    - 7.2.1 Concentric Ring Geometry & Radial Proportions
    - 7.2.2 Line-Cutter Tangency Geometry & Shaft Diameter Compensation
    - 7.2.3 Quadratic Line-Ellipse Intersection Equation Derivation
  - 7.3 Multi-Method Detection & Fallback Hierarchy
  - 7.4 Camera Calibration & Perspective Homography Matrix
  - 7.5 AI Engineering Design & Fallback Strategy
- **Chapter 8: Component-Level Design & Code Implementation**
  - 8.1 Backend Component Architecture & Core Bootstrap
  - 8.2 Detailed Backend Service Implementations & Critical Code Walkthroughs
  - 8.3 Frontend Component Architecture & Zustand State Management
  - 8.4 Real-Time WebSocket Communication Pipeline
- **Chapter 9: User Interface & User Manual**
  - 9.1 User Interface Design & Screen-by-Screen Walkthrough (8 Core Views)
  - 9.2 Installation and Deployment Manual (Docker Compose & Bare-Metal)
  - 9.3 Operational Troubleshooting & Failure Modes
- **Chapter 10: Preliminary & Acceptance Test Plan**
  - 10.1 Testing Strategy & QA Philosophy
  - 10.2 Comprehensive Test Matrix (67 Automated Test Cases)
  - 10.3 Pytest Execution Results & Pass Logs
  - 10.4 REST API Verification & Latency Benchmarks
  - 10.5 Acceptance Criteria Verification (A1 through A13 Mapped)
- **Chapter 11: Conclusion & Future Work**
  - 11.1 Summary of Contributions
  - 11.2 System Limitations
  - 11.3 Future Work Roadmap
- **References**

---

# LIST OF FIGURES

- Figure 1.1: World Archery Standard 10-Ring Target Face Dimensions and Ring Proportions
- Figure 1.2: Project Development Timeline and 14-Week Gantt Chart
- Figure 2.1: Quality Function Deployment (QFD) House of Quality Matrix for Bull's Eye
- Figure 3.1: Bull's Eye Comprehensive System Use Case Diagram
- Figure 3.2: Level-1 Activity Diagram: High-Level Tournament End-to-End Match Workflow
- Figure 3.3: Level-2 Activity Diagram: Multi-Tier Computer Vision & Fallback Scoring Pipeline
- Figure 3.4: Level-2 Activity Diagram: Judge Score Override & Audit Synchronization Workflow
- Figure 3.5: Sequence Diagram 1: Automated Image Ingestion and Real-Time Scoring Flow
- Figure 3.6: Sequence Diagram 2: Manual Line Judge Override & Audit Trail Logging Flow
- Figure 3.7: Sequence Diagram 3: Tournament Session Creation & Multi-Lane Archer Assignment Flow
- Figure 4.1: Third Normal Form (3NF) Entity Relationship Diagram (ERD)
- Figure 5.1: Bull's Eye Analysis Class Diagram
- Figure 6.1: Architectural Context Diagram (ACD)
- Figure 6.2: Top-Level Software Component Diagram
- Figure 6.3: Layered Software Architecture
- Figure 6.4: Docker Compose Multi-Container Production Deployment Diagram
- Figure 7.1: End-to-End Computer Vision and Scoring Engine Algorithmic Flowchart
- Figure 7.2: Geometric Visualization of Line-Cutter Shaft Tangency Condition
- Figure 7.3: Line-Ellipse Intersection Modeling on Oblique Perspective Targets
- Figure 7.4: 4-Point Perspective Homography Rectification Pipeline
- Figure 8.1: Backend Service-Oriented Component Architecture
- Figure 8.2: Frontend React 18 Component Hierarchy and Zustand Store Dataflow
- Figure 8.3: WebSocket Bi-Directional Event Synchronization Lifecycle
- Figure 9.1: Live Target Scoring and Calibration Interactive Canvas UI
- Figure 9.2: Tournament Management and Multi-Lane Dashboard UI
- Figure 9.3: Real-Time Leaderboard and Arrow Distribution Analytics UI

---

# LIST OF TABLES

- Table 1.1: 14-Week SPL-3 Project Milestone and Deliverable Schedule
- Table 2.1: Quality Function Deployment (QFD) Requirements Classification Table
- Table 3.1: Actor Identification and Privilege Specification Matrix
- Table 3.2: Detailed Use Case Specification: UC-01 Authenticate User & Assign Role
- Table 3.3: Detailed Use Case Specification: UC-02 Configure Tournament & Lane Session
- Table 3.4: Detailed Use Case Specification: UC-03 Calibrate Camera & Compute Homography Matrix
- Table 3.5: Detailed Use Case Specification: UC-04 Process Arrow Shot & Calculate Score
- Table 3.6: Detailed Use Case Specification: UC-05 Review & Override Arrow Score (Judge Audit)
- Table 3.7: Detailed Use Case Specification: UC-06 Broadcast Live Leaderboard & Stream Session
- Table 3.8: Detailed Use Case Specification: UC-07 Generate & Export Official Match Report (PDF)
- Table 3.9: Detailed Use Case Specification: UC-08 Execute Batch Image Model Evaluation
- Table 4.1: Data Dictionary: `users` Relational Entity
- Table 4.2: Data Dictionary: `tournaments` Relational Entity
- Table 4.3: Data Dictionary: `sessions` Relational Entity
- Table 4.4: Data Dictionary: `session_archers` Relational Entity
- Table 4.5: Data Dictionary: `scores` Relational Entity
- Table 4.6: Data Dictionary: `cameras` Relational Entity
- Table 4.7: Data Dictionary: `camera_lane_assignments` Relational Entity
- Table 4.8: Data Dictionary: `audit_logs` Relational Entity
- Table 5.1: Class Responsibility Collaborator (CRC) Specification Matrix
- Table 6.1: Complete REST API Endpoint Inventory and Protocol Contracts (27 Endpoints)
- Table 6.2: WebSocket Channel Specification and Event Payloads
- Table 7.1: World Archery Standard Target Ring Radius Proportions and Scoring Weights
- Table 7.2: Multi-Method Detection Algorithmic Consensus and Confidence Weights
- Table 8.1: System Technology Stack and Architectural Rationale
- Table 10.1: Comprehensive System Test Matrix (67 Automated Pytest Suites)
- Table 10.2: Pytest Suite Execution Summary and Pass Rates
- Table 10.3: REST API Endpoint Performance and Latency Benchmark Results
- Table 10.4: Acceptance Criteria (A1 through A13) Verification and Compliance Matrix
"""
