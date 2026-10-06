"""
Chapter 9: User Interface & User Manual Module for Bull's Eye SPL-3 Final Technical Report.
Covers Screen-by-Screen Walkthrough of 8 Core UI Views, Installation and Deployment Manual
(Docker Compose & Bare-Metal), and Operational Troubleshooting & Error Handling.
"""

def get_chapter_9():
    return r"""---

# CHAPTER 9: USER INTERFACE & USER MANUAL

## 9.1 User Interface Design & Screen-by-Screen Walkthrough

The Bull's Eye frontend was designed with an emphasis on visual clarity, real-time interactivity, and rapid judicial decision-making. The user interface conforms to modern responsive web standards, utilizing Tailwind CSS dark-slate themes, high-contrast target ring visualization, and accessible typographic hierarchies.

### 9.1.1 Authentication & Role-Based Access Control Screen
- **Visual Design**: Minimalist centered login card with dark blue brand gradient accents, password visibility toggles, and instant validation indicators.
- **Workflow**: Users authenticate with their registered email and password. Upon successful JWT issuance, the application automatically redirects the user to their permitted landing page:
  - *Administrator*: Redirects to `/tournaments` and `/system-status`.
  - *Scorer / Line Judge*: Redirects to `/scoring` and `/cameras`.
  - *Archer / Public*: Redirects to `/dashboard` and `/reports`.

### 9.1.2 Executive Dashboard & Tournament Overview Screen
- **Visual Design**: High-density analytics summary displaying four primary KPI cards: Active Competitions, Online Target Cameras, Total Arrows Scored Today, and System Average Scoring Latency ($182\text{ ms}$).
- **Interactive Elements**:
  - Live Lane Grid: Real-time visual cards for every competition lane showing assigned archers, current end index, and running score totals.
  - Recent Alerts Panel: Highlights disconnected camera streams or pending judicial reviews requiring official sign-off.

### 9.1.3 Live Scoring & Target Calibration Screen
The core operational view where archers and judges monitor incoming shots:

```
+----------------------------------------------------------------------------------------------------+
|                         LIVE TARGET SCORING AND CALIBRATION INTERACTIVE UI                         |
|                                                                                                    |
|  [Session: National Recurve Finals | Lane 3: Nafisa (Rank 1)]                                      |
|  +---------------------------------------------+  +---------------------------------------------+  |
|  |           INTERACTIVE SVG TARGET            |  |             END SCOREBOARD                  |  |
|  |                                             |  | End 3 of 12 (6 Arrows per End)              |  |
|  |                 . - ~ - .                   |  |---------------------------------------------|  |
|  |             . '   ( 8 )   ' .               |  | Arrow 1: 10 (X)  [x: 12.4mm, y: -8.1mm]     |  |
|  |           /     . - ~ - .     \             |  | Arrow 2: 10      [x: -24.1mm, y: 31.0mm]    |  |
|  |          /    /   ( 9 )   \    \            |  | Arrow 3:  9      [x: 82.5mm, y: 15.2mm]     |  |
|  |         |    |   . - - .   |    |           |  | Arrow 4: 10 (X)  [x: -5.0mm, y: 11.2mm]     |  |
|  |         |    |  | (10)  |  |    |           |  | Arrow 5:  9      [x: 65.3mm, y: -45.1mm]    |  |
|  |         |    |   ' - - '   |    |           |  | Arrow 6: -- (Awaiting Shot...)              |  |
|  |          \    \     *     /    /            |  |---------------------------------------------|  |
|  |           \     ' - ~ - '     /             |  | End Subtotal: 48 / 50                       |  |
|  |             . '   Arrow 5 ' .               |  | Running Total: 168 / 180 (Rank 1st)         |  |
|  |                 ' - ~ - '                   |  |---------------------------------------------|  |
|  +---------------------------------------------+  | [ Override Selected ]  [ Finalize End ]     |  |
|  | [ Zoom 2x ]  [ Calibrate ]  [ Reset View ]  |  +---------------------------------------------+  |
+----------------------------------------------------------------------------------------------------+
```
*Figure 9.1: Live Target Scoring and Calibration Interactive Canvas UI*

- **Interactive Target Canvas**: Scalable Vector Graphics (SVG) representation of the official World Archery 10-ring target. Incoming arrow impacts trigger animated pulse markers color-coded to the hit zone.
- **Micro-Adjustment & Zoom**: Clicking any arrow marker opens a 4x magnified crop displaying the physical camera frame, the computed shaft radius circle ($\delta = 2.5\text{ mm}$), and the dividing line boundary.
- **Judge Override Modal**: Certified line judges can click "Override Selected", adjust the point value from 0 to 10, toggle the X-ring flag, and submit a mandatory justification note, instantaneously updating all connected clients.

### 9.1.4 Tournament & Session Management Screen
```
+----------------------------------------------------------------------------------------------------+
|                         TOURNAMENT AND LANE MANAGEMENT DASHBOARD UI                                |
|                                                                                                    |
|  [ + Create Tournament ]  [ Bulk Import Archers (CSV) ]  [ Generate Elimination Brackets ]         |
|                                                                                                    |
|  ACTIVE TOURNAMENTS:                                                                               |
|  +----------------------------------------------------------------------------------------------+  |
|  | Tournament Name       | Type     | Face Size | Lanes | Status    | Actions                    |  |
|  |-----------------------|----------|-----------|-------|-----------|----------------------------|  |
|  | National Recurve 2026 | Recurve  | WA 122cm  | 8     | ACTIVE    | [Manage] [Export PDF] [Del]|  |
|  | University Cup 2026   | Compound | WA 80cm   | 4     | SCHEDULED | [Manage] [Configure]  [Del]|  |
|  +----------------------------------------------------------------------------------------------+  |
|                                                                                                    |
|  LANE ALLOCATION MATRIX (National Recurve 2026):                                                   |
|  +--------+--------------------------+------------------------------+---------------------------+  |
|  | Lane   | Assigned Archer          | Assigned Camera              | Stream Health / Ping      |  |
|  |--------|--------------------------|------------------------------|---------------------------|  |
|  | Lane 1 | Md. Shaikhul Islam (DU)  | RTSP://192.168.1.101/lane1   | ONLINE (24 ms)            |  |
|  | Lane 2 | Farhan Tanvir (BKSP)     | RTSP://192.168.1.102/lane2   | ONLINE (18 ms)            |  |
|  | Lane 3 | Nafisa Tabassum (Ansar)  | RTSP://192.168.1.103/lane3   | ONLINE (22 ms)            |  |
|  +--------+--------------------------+------------------------------+---------------------------+  |
+----------------------------------------------------------------------------------------------------+
```
*Figure 9.2: Tournament Management and Multi-Lane Dashboard UI*

- **Tournament Builder**: Form enabling administrators to specify total ends, arrows per end, target face type, and scoring rules.
- **Lane Assignment Grid**: Drag-and-drop or dropdown assignment of archers and cameras to target lanes with automated camera stream ping checks.

### 9.1.5 Camera Feed & Multi-Lane Surveillance Screen
- Displays low-latency live preview tiles for all registered target cameras.
- Provides an interactive 4-point calibration tool: users click four outer-ring target markers on the live frame; the system calculates the homography matrix $H$ and renders a warped circular overlay to confirm alignment.

### 9.1.6 Comprehensive Reports, Leaderboards & PDF Export Screen
```
+----------------------------------------------------------------------------------------------------+
|                         REAL-TIME LEADERBOARD AND ANALYTICS DASHBOARD UI                           |
|                                                                                                    |
|  OFFICIAL LEADERBOARD: World Archery 70m Recurve Qualification                                      |
|  +------+-------------------------+-------+-------+------+--------+---------+-------------------+  |
|  | Rank | Archer Name             | Total | Tens  | Xs   | Arrows | Average | Scorecard PDF     |  |
|  |------|-------------------------|-------|-------|------|--------|---------|-------------------|  |
|  | 1    | Nafisa Tabassum (Ansar) | 674   | 34    | 12   | 72     | 9.36    | [ Download PDF ]  |  |
|  | 2    | Md. Shaikhul Islam (DU) | 668   | 31    | 9    | 72     | 9.28    | [ Download PDF ]  |  |
|  | 3    | Farhan Tanvir (BKSP)    | 661   | 28    | 8    | 72     | 9.18    | [ Download PDF ]  |  |
|  +------+-------------------------+-------+-------+------+--------+---------+-------------------+  |
|                                                                                                    |
|  ARROW GROUPING DISPERSION (Nafisa Tabassum):                                                      |
|  +---------------------------------------------+  +---------------------------------------------+  |
|  | (Recharts Scatter Plot: 72 Arrow Hits)      |  | (Recharts Line Chart: End-by-End Scoring)   |  |
|  | Concentric rings: Yellow, Red, Blue, Black  |  | End 1: 56, End 2: 58, End 3: 55, ...        |  |
|  | 95% Confidence Ellipse Radius: 42.1 mm      |  | Average Arrow Score Trend: Upward (+0.4)    |  |
|  +---------------------------------------------+  +---------------------------------------------+  |
+----------------------------------------------------------------------------------------------------+
```
*Figure 9.3: Real-Time Leaderboard and Arrow Distribution Analytics UI*

- **Live Leaderboard**: Real-time sorted table applying World Archery tie-breaking criteria (`total_score DESC`, `num_tens DESC`, `num_xs DESC`).
- **Performance Analytics**: Visualized via Recharts, including arrow dispersion scatter plots and end-by-end consistency curves.
- **One-Click PDF Export**: Direct download of official World Archery-compliant PDF match scorecards.

### 9.1.7 Batch Testing & Evaluation Suite Screen
- Designed for computer vision validation and model benchmarking.
- Allows administrators to upload a ZIP archive of annotated target frames; executes the full multi-tier detection pipeline; renders confusion matrices, Mean Radial Error curves, and zone classification metrics.

### 9.1.8 System Health & Administration Screen
- Real-time telemetry dashboard querying `/api/v1/health`.
- Visualizes status indicators and response latency for PostgreSQL, Redis, OpenCV/PyTorch workers, and active camera connections.

## 9.2 Installation and Deployment Manual

### 9.2.1 System Requirements
- **Host Hardware**: Quad-core x86_64 or ARM64 CPU (Intel i5/i7, AMD Ryzen, or Apple Silicon), 8 GB RAM (16 GB recommended for multi-lane YOLO inference), 20 GB available SSD storage.
- **Operating System**: Linux (Ubuntu 22.04 LTS recommended), Windows 10/11 with WSL2, or macOS.
- **Software Dependencies**: Docker Engine 24.0+, Docker Compose 2.24+, Git, Python 3.11+ (for local bare-metal execution), Node.js 18+ (for local frontend development).

### 9.2.2 Docker Compose Single-Command Deployment
The recommended deployment method encapsulates all four services inside isolated containers:

```bash
# Step 1: Clone the repository
git clone https://github.com/Shaikh1828/SPL-3.git
cd SPL-3

# Step 2: Configure Environment Variables
cp .env.example .env
# Edit .env to set secure JWT secrets and database passwords:
# POSTGRES_PASSWORD=your_secure_password
# SECRET_KEY=your_cryptographic_secret_key

# Step 3: Build and Launch Multi-Container Stack
docker compose up --build -d

# Step 4: Verify Container Execution
docker compose ps
```

Once launched, services are accessible at:
- **Web Frontend**: `http://localhost:3000` (or `http://localhost:5173`)
- **FastAPI REST API & Swagger UI**: `http://localhost:8000/docs`
- **PostgreSQL Database**: `localhost:5432` (`archery_db`)
- **Redis Cache**: `localhost:6379`

### 9.2.3 Bare-Metal Local Development Setup

For developers modifying service code directly:

```bash
# 1. Backend Setup
cd SPL-3
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt
python setup_db.py  # Initializes database tables and seed data
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# 2. Frontend Setup (in a separate terminal)
cd SPL-3/frontend
npm install
npm run dev
```

## 9.3 Operational Troubleshooting & Failure Modes

*Table 9.1: Operational Troubleshooting Matrix*

| Symptom / Failure Mode | Root Cause Analysis | Remediation & Recovery Procedure |
| :--- | :--- | :--- |
| **Camera Feed Marked Offline** | RTSP stream dropped due to WiFi jitter or camera power loss. | The system automatically initiates reconnect with exponential backoff (1s, 2s, 4s, 8s). Ensure camera IP is static and reachable via `ping <camera_ip>`. |
| **Database Connection Refused** | PostgreSQL container still initializing during cold startup. | Ensure `db` container healthcheck passes. Docker Compose includes `depends_on: db: condition: service_healthy` to prevent premature API startup. |
| **Warped Rectification Distorted** | 4-point calibration points were clicked out of order or collinear. | Open Camera Management $\to$ Lane Settings $\to$ "Recalibrate". Reselect reference points strictly in order: Top-Left $\to$ Top-Right $\to$ Bottom-Right $\to$ Bottom-Left. |
| **Line Judge Score Override Rejected**| Judicial override submitted without mandatory justification text. | The system strictly enforces audit compliance. Enter an explanatory note in the text area before submitting. |
| **YOLO11 Model Inference Error** | Missing PyTorch dependencies or CUDA driver mismatch. | Bull's Eye automatically falls back to CPU inference (`torch.device('cpu')`) and morphological difference detection if GPU drivers are unavailable. |
"""
