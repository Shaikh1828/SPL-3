# User Stories — Archery Scoring System

**Project**: Automated Archery Scoring System  
**Date**: 2026-05-23  
**Format**: Gherkin (Given/When/Then)  
**Organization**: Feature-Based  
**Total Stories**: 21 Feature Stories  

---

## Story Dependencies Graph

```
USER AUTHENTICATION
    ↓
TOURNAMENT/SESSION SETUP
    ↓
ARCHER REGISTRATION → CAMERA ASSIGNMENT
    ↓
LIVE PREVIEW ← CAMERA CONFIG
    ↓
TRIGGER SCORING → SCORE DETECTION
    ↓
LOW CONFIDENCE CHECK → OVERRIDE STORIES
    ↓
REPORTS
    ↓
ARCHIVE/RETENTION
```

---

# FEATURE 1: USER AUTHENTICATION & MANAGEMENT

## Story USR-001: User Logs In with Credentials

**Phase**: Phase 1 (Essential)  
**Personas**: All (System Admin, Tournament Admin, Scorer, Archer)  
**Depends On**: None  
**Blocking**: All other stories

```gherkin
Feature: User Authentication
  Scenario: Authorized User Logs In
    Given a user with valid credentials exists in the system
    When the user enters username and password
    And clicks [Login]
    Then the user receives a JWT token
    And the token is valid for 8 hours
    And the user is redirected to the appropriate dashboard
    
  Scenario: Unauthorized User Cannot Log In
    Given a user enters incorrect password
    When the system validates credentials
    Then authentication fails
    And an error message appears: "Invalid credentials"
    And no token is issued
    
  Scenario: Expired Session Logs Out User
    Given a user is logged in with a valid token
    When 8 hours pass without activity
    Then the token expires
    And the user is redirected to login page
    And a message appears: "Your session has expired"
```

**Acceptance Criteria**:
- ✅ JWT token issued on successful login with 8-hour expiration
- ✅ Invalid credentials rejected immediately
- ✅ Token stored securely (httpOnly cookie)
- ✅ Token validated on every API request

---

## Story USR-002: System Admin Creates New User Accounts

**Phase**: Phase 1 (Essential)  
**Personas**: System Admin → creates; others → use accounts  
**Depends On**: USR-001 (admin must be logged in)  

```gherkin
Feature: User Account Management
  Scenario: Admin Creates New Tournament Admin
    Given System Admin is logged in
    When Admin navigates to User Management
    And fills form: username, email, role: "TOURNAMENT_ADMIN"
    And clicks [Create User]
    Then new user account is created
    And a temporary password is generated
    And user receives email with credentials
    
  Scenario: Admin Creates Multiple Users
    Given System Admin wants to add 10 Scorers for an event
    When Admin uses bulk import: CSV with username, email, role
    And validates the import
    And clicks [Import Users]
    Then all users are created in batch
    And import report shows: X created, Y errors, Z warnings
    
  Scenario: Attempt to Create Duplicate User Fails
    Given a user "john_scorer" already exists
    When Admin tries to create another "john_scorer"
    Then the system rejects the creation
    And displays: "Username already exists"
```

**Acceptance Criteria**:
- ✅ Admin can create users with role assignment
- ✅ Temporary password generated and emailed
- ✅ Duplicate usernames prevented
- ✅ Bulk import supported with error reporting

---

## Story USR-003: Archer Can Only View Own Data (Permission Boundary)

**Phase**: Phase 1 (Essential)  
**Personas**: Archer, System Admin  
**Depends On**: USR-001, USR-002  

```gherkin
Feature: Role-Based Permission Enforcement
  Scenario: Archer Cannot Access Admin Features
    Given an Archer is logged in
    When Archer navigates to URL: /admin/users
    Then access is denied
    And error message appears: "You do not have permission to access this resource"
    
  Scenario: Archer Can Only See Own Scores
    Given an Archer is logged in
    When Archer views the leaderboard
    Then Archer sees their own scores and ranking
    And Archer cannot see other archers' individual arrows
    And Archer cannot access other users' annotated images
    
  Scenario: Scorer Cannot Create Tournaments
    Given a Scorer is logged in
    When Scorer navigates to Tournament Management
    Then the [Create Tournament] button is hidden/disabled
    And a message states: "This action requires TOURNAMENT_ADMIN role"
```

**Acceptance Criteria**:
- ✅ Unauthorized endpoints return 403 Forbidden
- ✅ UI hides/disables features user cannot access
- ✅ Archer data isolation enforced at API level (object-level authz)
- ✅ All permission checks logged for audit trail

---

# FEATURE 2: CAMERA MANAGEMENT

## Story CAM-001: System Enumerates Available USB Cameras

**Phase**: Phase 1 (Essential)  
**Personas**: System Admin  
**Depends On**: None  

```gherkin
Feature: Camera Discovery
  Scenario: System Auto-Detects USB Cameras on Startup
    Given backend server is starting up
    When system initializes camera manager
    Then system probes USB indices 0-9 with cv2.VideoCapture()
    And identifies all connected USB cameras
    And stores camera status: connected/disconnected
    And broadcasts camera list to connected clients via WebSocket
    
  Scenario: Camera Connection Status Updates
    Given a USB camera is connected
    When user unplugs the camera
    Then within 30 seconds, system detects disconnection
    And camera status changes to "disconnected" (red badge)
    And WebSocket notifies all clients of status change
    
  Scenario: Reconnection Auto-Recovery
    Given a camera was disconnected
    When camera is reconnected (or system re-probes)
    Then status changes to "connected" (green badge)
    And camera is ready for use immediately
```

**Acceptance Criteria**:
- ✅ Camera enumeration runs on startup
- ✅ Camera list broadcasted to all clients via WebSocket
- ✅ Status updates propagate in < 1 second
- ✅ Auto-reconnect probes every 30 seconds

---

## Story CAM-002: Admin Configures Camera Settings

**Phase**: Phase 1 (Essential)  
**Personas**: System Admin  
**Depends On**: CAM-001  

```gherkin
Feature: Camera Configuration
  Scenario: Admin Updates Camera Resolution and FPS
    Given System Admin is on Camera Management page
    When Admin clicks [Edit] on a camera card
    And modifies: resolution: 1920×1080, FPS: 30, brightness: 60
    And clicks [Save]
    Then settings are persisted to database
    And settings take effect on next camera access
    And camera preview updates with new settings
    
  Scenario: Admin Assigns Camera to Lane
    Given a camera exists in the system
    When Admin navigates to a Session
    And drags camera to "Lane 1" with archer "John Doe"
    Then camera is bound to Lane 1 → John Doe
    And binding persists for session duration
    And Scorer can trigger scoring on this camera
    
  Scenario: Admin Tests Camera Connection
    Given Admin is configuring a new RTSP camera
    When Admin enters stream URL and clicks [Test Connection]
    Then system attempts to open the stream
    And either confirms "✓ Connected" or shows error "Failed to connect"
    And provides diagnostic info if connection fails
```

**Acceptance Criteria**:
- ✅ Camera settings persist to database
- ✅ Camera-to-lane assignment enforced during session
- ✅ Test connection validates stream accessibility
- ✅ Error messages are diagnostic (URL issue, auth issue, timeout, etc.)

---

## Story CAM-003: Scorer Views Live Camera Preview

**Phase**: Phase 1 (Essential)  
**Personas**: Scorer  
**Depends On**: CAM-001, USR-001  

```gherkin
Feature: Live Camera Preview Streaming
  Scenario: Scorer Opens Scoring Page and Sees Live Preview
    Given a Scorer is logged in
    When Scorer navigates to Scoring page
    And session is active with cameras assigned
    Then each lane shows a live camera preview
    And preview updates at 15 fps (1280×720 resolution)
    And a circular targeting overlay helps align the target
    And a [● LIVE] indicator shows stream is active
    
  Scenario: Low Bandwidth Preview Quality
    Given preview is streaming at 15 fps
    When network conditions degrade (high latency)
    Then system gracefully maintains stream
    And preview may drop to 10 fps temporarily
    And connection status remains visible
    And user is informed if preview disconnects
    
  Scenario: Scorer Can Zoom and Pan Preview
    Given live preview is displayed on mobile/tablet
    When Scorer uses pinch-zoom gesture
    Then preview zooms client-side (no server load)
    And panning is smooth and responsive
    And zoom level resets on next [Calculate]
```

**Acceptance Criteria**:
- ✅ Preview streams at 15 fps via WebSocket
- ✅ Circular targeting overlay rendered in frontend
- ✅ Stream handles network degradation gracefully
- ✅ Client-side zoom/pan (no server impact)

---

# FEATURE 3: TOURNAMENT & SESSION MANAGEMENT

## Story SES-001: Tournament Admin Creates Tournament

**Phase**: Phase 1 (Essential)  
**Personas**: Tournament Admin  
**Depends On**: USR-001 (admin logged in)  

```gherkin
Feature: Tournament Creation
  Scenario: Tournament Admin Creates New Tournament
    Given Tournament Admin is logged in
    When Admin navigates to Tournaments
    And clicks [+ Create Tournament]
    And fills form: name, date, location, target_type
    And clicks [Create]
    Then tournament is created with status: "pending"
    And a unique tournament ID is generated
    And Admin is redirected to tournament detail page
    
  Scenario: Tournament Created with Default Settings
    Given a tournament is created
    Then default settings are: scoring_method: "WA standard", max_archers: 100
    And Admin can edit these on the tournament page
```

**Acceptance Criteria**:
- ✅ Tournament creation is atomic (all-or-nothing)
- ✅ Unique tournament ID generated
- ✅ Created-at timestamp recorded
- ✅ Tournament defaults to "pending" status

---

## Story SES-002: Tournament Admin Creates Session

**Phase**: Phase 1 (Essential)  
**Personas**: Tournament Admin  
**Depends On**: SES-001  

```gherkin
Feature: Session Setup
  Scenario: Admin Creates Session (End/Arrows Configuration)
    Given a tournament exists
    When Admin clicks [+ New Session] in tournament
    And fills form: session_name: "70m Round", distance: 70, end_count: 6, arrows_per_end: 3, target_face_cm: 80
    And clicks [Create Session]
    Then session is created with status: "pending"
    And session accepts exactly 3 arrows per end, 6 ends total
    And Admin can add archers to this session
    
  Scenario: Session Configuration Prevents Invalid Values
    Given the New Session form is open
    When Admin tries to set: arrows_per_end: -1 or 100
    Then validation rejects invalid values
    And error message explains: "Valid values: 1-12"
```

**Acceptance Criteria**:
- ✅ Session creation validates all fields
- ✅ End count and arrows per end locked once session starts
- ✅ Session ID generated uniquely
- ✅ Initial status is "pending" (not active until started)

---

## Story SES-003: Tournament Admin Registers Archers

**Phase**: Phase 1 (Essential)  
**Personas**: Tournament Admin  
**Depends On**: SES-002  

```gherkin
Feature: Archer Registration
  Scenario: Admin Registers Single Archer in Session
    Given a session exists with status: "pending"
    When Admin clicks [+ Add Archer] in session
    And selects/creates archer: name: "John Doe", club: "Bay Area Archers"
    And clicks [Add]
    Then archer is registered in session
    And a unique session-archer ID is generated
    
  Scenario: Admin Bulk Imports Archers via CSV
    Given a session exists
    When Admin clicks [Bulk Import Archers]
    And uploads CSV: name, club, division
    And validates preview
    And clicks [Import]
    Then all archers are registered
    And import report shows: X added, Y skipped (duplicates)
    
  Scenario: Cannot Register Same Archer Twice in Session
    Given archer "John Doe" is registered in a session
    When Admin tries to add "John Doe" again
    Then registration is rejected
    And message appears: "Archer already registered in this session"
```

**Acceptance Criteria**:
- ✅ Single archer registration supported
- ✅ Bulk CSV import supported
- ✅ Duplicate prevention enforced
- ✅ Archer list is searchable and sortable

---

## Story SES-004: Tournament Admin Starts Session

**Phase**: Phase 1 (Essential)  
**Personas**: Tournament Admin, Scorer  
**Depends On**: SES-003, CAM-002  

```gherkin
Feature: Session Initialization
  Scenario: Admin Starts Session and Activates Scoring
    Given a session has status: "pending"
    And archers are registered
    And cameras are configured and assigned
    When Admin clicks [Start Session] on session detail
    Then session status changes to "active"
    And all scorers receive notification: "Session is now active"
    And Scorers can begin scoring
    And session start time is recorded
    
  Scenario: Cannot Start Session Without Cameras Assigned
    Given a session is pending
    When no cameras are assigned to any lane
    Then [Start Session] button is disabled
    And message states: "Assign at least 1 camera before starting"
    
  Scenario: Scorers Cannot Start Session
    Given a Scorer is logged in
    When Scorer tries to access [Start Session] button
    Then button is hidden/disabled
    And message: "Only TOURNAMENT_ADMIN can start sessions"
```

**Acceptance Criteria**:
- ✅ Status transition from pending → active persisted immediately
- ✅ Real-time notification sent to scorers
- ✅ Cannot start without cameras assigned (validation)
- ✅ Start timestamp recorded in database

---

# FEATURE 4: LIVE SCORING

## Story SCORE-001: Scorer Triggers Scoring with [Calculate] Button

**Phase**: Phase 1 (Essential)  
**Personas**: Scorer  
**Depends On**: SES-004 (session active), CAM-003 (live preview)  

```gherkin
Feature: Scoring Trigger
  Scenario: Scorer Presses [Calculate] Button
    Given a session is active
    And live camera preview is showing
    And an archer has shot arrows at target
    When Scorer clicks [Calculate] button
    Then button changes to [⏳ Analyzing...] with spinner
    And UI remains responsive (async processing)
    And system captures frame from camera
    And frame is processed through image pipeline (< 1 second)
    Then results appear: annotated image + score table
    And [Calculate] button returns to normal state
    
  Scenario: Low Network Bandwidth
    Given scoring is triggered
    When network is slow but connected
    Then processing continues
    And timeout is set to 5 seconds max
    If processing exceeds 5 seconds, error: "Image processing timed out"
    
  Scenario: Camera Disconnect During Scoring
    Given [Calculate] is pressed
    When camera disconnects during capture
    Then processing fails gracefully
    And error message: "Camera connection lost"
    And suggestion: "Reconnect camera and retry"
```

**Acceptance Criteria**:
- ✅ Capture triggers on camera assigned to lane
- ✅ Burst mode: 3 frames captured, sharpest selected
- ✅ Results display in < 1 second
- ✅ Error handling prevents UI hang

**Blocking**: SCORE-002 depends on this

---

## Story SCORE-002: Scorer Reviews Automatically Detected Score

**Phase**: Phase 1 (Essential)  
**Personas**: Scorer  
**Depends On**: SCORE-001  

```gherkin
Feature: Score Detection & Display
  Scenario: Score Detection Results Display
    Given [Calculate] button was pressed
    When processing completes
    Then results appear in modal:
    - Annotated image (zoomable, pannable)
    - Table: Arrow #, Zone, Score, Confidence
    - End Total
    - Visual indicators: green checkmark (high conf), yellow warning (medium), red X (low)
    
  Scenario: Scorer Views Annotated Image Details
    Given score results are displayed
    When Scorer clicks on annotated image
    Then image zooms/pans in detail view
    And clicking an arrow highlights: score, zone, confidence, distance
    
  Scenario: Low Confidence Triggers Visual Warning
    Given a score has confidence < 0.60
    When results display
    Then yellow warning banner appears: "⚠ Review Recommended"
    And confidence percentage shown in red
    And Scorer is prompted to confirm or override
```

**Acceptance Criteria**:
- ✅ Annotated image generated and displayed
- ✅ Per-arrow confidence displayed
- ✅ Low confidence (<0.60) visually flagged
- ✅ Results include end total and running total

**Blocking**: SCORE-003, SCORE-OVERRIDE stories depend on this

---

## Story SCORE-003: Scorer Confirms Score and Moves to Next Arrow

**Phase**: Phase 1 (Essential)  
**Personas**: Scorer  
**Depends On**: SCORE-002  

```gherkin
Feature: Score Confirmation
  Scenario: Scorer Confirms Detected Score
    Given score results are displayed
    When Scorer clicks [Confirm Score]
    Then score is saved to database
    And annotated image is stored
    And arrow record created: {archer_id, end_number, arrow_number, zone, score, confidence, timestamp}
    And running total updates
    And UI shows: "Score saved ✓"
    
  Scenario: Confirm Button Disabled if Critical Error
    Given image processing failed or no arrows detected
    When results display with error state
    Then [Confirm Score] button is disabled/hidden
    And error message explains: "Cannot confirm: [specific reason]"
    And [Retake] button is available instead
    
  Scenario: Multiple Arrows in Single End
    Given an end has 3 arrows
    When Scorer confirms arrow 1 score
    Then UI shows: "Arrow 1/3 ✓"
    And prompts: "Ready for arrow 2?"
    And Scorer can trigger scoring for next arrow
```

**Acceptance Criteria**:
- ✅ Score persisted atomically
- ✅ Annotated image stored with path reference
- ✅ Running total recalculated and displayed
- ✅ UI indicates progress (arrow X of Y)

---

## Story SCORE-OVERRIDE-001: System Detects Low Confidence Score

**Phase**: Phase 1 (Essential)  
**Personas**: Scorer, Archer (views flag)  
**Depends On**: SCORE-002  

```gherkin
Feature: Low Confidence Detection
  Scenario: Automatic Flagging of Low Confidence
    Given scoring completes with confidence < 0.60
    When results display
    Then visual flag appears: yellow warning banner with "⚠ Review Recommended"
    And score is marked: "LOW_CONFIDENCE" in database
    And flag appears in reports as ⚠ indicator
    
  Scenario: Edge Case Scoring (Arrow on Ring Boundary)
    Given an arrow is detected very close to ring boundary
    When confidence for that arrow is marginal
    Then visual flag appears: "⚠ Boundary Detection - Verify Visually"
    And Scorer can view detailed detection info
    
  Scenario: Multiple Low Confidence Arrows in End
    Given an end has 2 arrows with confidence > 0.85 and 1 arrow with confidence 0.55
    When results display
    Then only the low confidence arrow is flagged
    And end total shows confidence: "MIXED (2 high, 1 low)"
```

**Acceptance Criteria**:
- ✅ Confidence values calculated for each arrow
- ✅ Scores with confidence < 0.60 flagged automatically
- ✅ Flag persisted in database for reporting
- ✅ Visual indication clear and unambiguous

---

## Story SCORE-OVERRIDE-002: Scorer Overrides Single Arrow Score

**Phase**: Phase 1 (Essential)  
**Personas**: Scorer  
**Depends On**: SCORE-OVERRIDE-001  

```gherkin
Feature: Score Override - Single Arrow
  Scenario: Scorer Overrides Single Arrow with Reason
    Given score results show low confidence arrow
    When Scorer clicks [✏ Override] on that arrow
    Then override modal opens with fields:
    - new_zone: dropdown [X, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, M]
    - reason: dropdown ["Detection error", "Arrow touched line", "System error", "Other"]
    - note: text field (optional)
    When Scorer selects: zone=9, reason="Arrow touched line", note="Clear visual in line"
    And clicks [Save Override]
    Then new zone replaces old zone
    And score recalculated
    And override logged: {old_zone, new_zone, reason, note, scorer_id, timestamp}
    And running total updates
    
  Scenario: Override Audit Trail Visible
    Given an arrow has been overridden
    When Scorer hovers over override icon
    Then tooltip shows: "⚠ Overridden: 10→9 (Arrow touched line) by Marcus T. at 10:30"
```

**Acceptance Criteria**:
- ✅ Override modal pre-fills with detection result
- ✅ New zone must be valid (0-10, M)
- ✅ Reason required (mandatory dropdown)
- ✅ Override persisted with audit trail (immutable)
- ✅ Running totals recalculated post-override

---

## Story SCORE-OVERRIDE-003: Scorer Overrides Full End Score

**Phase**: Phase 2 (Desirable)  
**Personas**: Scorer  
**Depends On**: SCORE-OVERRIDE-002  

```gherkin
Feature: Score Override - Full End
  Scenario: Scorer Overrides Entire End If System Failed
    Given an end was scored but all 3 arrows had detection errors
    When Scorer clicks [Override Full End]
    Then form appears asking: scores for arrow 1, 2, 3 (manual input)
    When Scorer enters: 9, 10, 8
    And clicks [Save Override]
    Then all 3 arrows are replaced with new scores
    And override log entries created for each arrow
    And end total recalculated: 27 (9+10+8)
    
  Scenario: Cannot Override Individual Arrows After Full Override
    Given an end has been fully overridden
    When Scorer tries to override a single arrow
    Then warning appears: "This end is fully overridden. Override full end instead."
    And single arrow override is blocked
```

**Acceptance Criteria**:
- ✅ Full end override requires all 3 scores
- ✅ Each arrow creates separate audit log entry
- ✅ End total recalculated automatically
- ✅ UI prevents conflicting override types

---

## Story SCORE-OVERRIDE-004: Scorer Views Override History Log

**Phase**: Phase 2 (Desirable)  
**Personas**: Scorer, Tournament Admin  
**Depends On**: SCORE-OVERRIDE-002, SCORE-OVERRIDE-003  

```gherkin
Feature: Override Audit Log
  Scenario: Session Report Shows Override Summary
    Given a session has completed with overrides
    When generating session report or viewing session detail
    Then "Override Log" section shows:
    - Archer name, End #, Arrow #
    - Original score, Overridden score, Reason
    - Scorer who made override, Timestamp
    - Optional note
    
  Scenario: Filter Overrides by Archer or Scorer
    Given override log is displayed
    When Tournament Admin clicks [Filter by Archer: "John Doe"]
    Then log shows only overrides affecting John Doe
    And count displayed: "3 overrides for John Doe"
    
  Scenario: Export Override Log to CSV
    Given override log is displayed
    When Admin clicks [Export Override Log]
    Then CSV file generated with all override details
    And file includes: timestamp, archer, end, reason, scorer
```

**Acceptance Criteria**:
- ✅ Override log queried from database
- ✅ Filtering supported by archer, scorer, date range
- ✅ CSV export includes all override details
- ✅ Log is immutable (only view, not edit)

---

# FEATURE 5: PERMISSION-BASED FEATURES

## Story PERM-001: Admin Restricts Archer Access to Own Data

**Phase**: Phase 1 (Essential)  
**Personas**: Archer, System Admin  
**Depends On**: USR-003  

```gherkin
Feature: Archer Data Isolation
  Scenario: Archer Can Only View Own Session Scores
    Given an Archer is logged in
    When Archer navigates to Reports or Leaderboard
    Then Archer sees only:
    - Own scores for current session
    - Own end totals and running totals
    - Own arrow details and confidence values
    - Cannot see other archers' individual arrow data
    
  Scenario: Archer Cannot Access Admin or Scorer Views
    Given an Archer is logged in
    When Archer tries direct API call: GET /api/v1/sessions/{id}/all_scores
    Then endpoint returns 403 Forbidden
    And error: "You do not have permission to view all archer data"
    
  Scenario: Archer Receives Personal Data in API Responses
    Given Archer calls API: GET /api/v1/my_scores
    Then response includes only own scores
    And other archer data is completely absent
    And response never includes archer names or identities of others
```

**Acceptance Criteria**:
- ✅ Archer API endpoints filter by logged-in user
- ✅ Database queries include WHERE archer_id = current_user_id
- ✅ UI hides all multi-archer views when logged in as Archer
- ✅ Unauthorized access attempts logged for audit

---

## Story PERM-002: Scorer Cannot Modify Tournament Settings

**Phase**: Phase 1 (Essential)  
**Personas**: Scorer, Tournament Admin  
**Depends On**: USR-001  

```gherkin
Feature: Role-Based Feature Access
  Scenario: Scorer Cannot Access Tournament Admin Features
    Given a Scorer is logged in
    When Scorer navigates to tournament settings
    Then the page either shows 403 Forbidden
    Or shows read-only view with no edit buttons
    And buttons [Edit], [Delete], [Manage Archers] are hidden
    
  Scenario: Scorer Can Only Operate During Active Session
    Given a Scorer is logged in
    And session status is "pending" (not yet started)
    When Scorer navigates to scoring page
    Then [Calculate] button is disabled
    And message: "Scoring unavailable. Waiting for session to start."
    
  Scenario: API Enforces Role Checks
    Given a Scorer attempts POST /api/v1/sessions with new session data
    Then endpoint returns 403 Forbidden
    And error: "Only TOURNAMENT_ADMIN can create sessions"
```

**Acceptance Criteria**:
- ✅ Role-based middleware checks on all protected endpoints
- ✅ 403 Forbidden returned for unauthorized role
- ✅ UI dynamically hides/disables features based on role
- ✅ No "try to hide" security (authorization at API layer)

---

# FEATURE 6: REPORTS

## Story RPT-001: Tournament Admin Accesses Comprehensive Reports

**Phase**: Phase 1 (Essential)  
**Personas**: Tournament Admin, Archer  
**Depends On**: SCORE-003 (scores exist)  

```gherkin
Feature: Report Access
  Scenario: Admin Views Session Report
    Given a session has completed (or in progress)
    When Admin clicks [View Report] on session
    Then report displays:
    - Session details (name, date, distance, archers, ends)
    - Score table: End × Arrow grid with scores, running totals
    - Charts: score distribution (bar), trend (line)
    - Statistics: avg/end, best end, X count, consistency rating
    - Thumbnail grid of all end images (click to enlarge)
    
  Scenario: Admin Exports Report as PDF
    Given session report is displayed
    When Admin clicks [⬇ Export PDF]
    Then PDF generated with:
    - All session data and images
    - Charts rendered
    - Override log if applicable
    - Professional formatting suitable for official records
    And file downloaded: session_name_report.pdf
    
  Scenario: Admin Exports Report as CSV
    Given session report is displayed
    When Admin clicks [⬇ Export CSV]
    Then CSV file generated:
    - Columns: End, Arrow1_Zone, Arrow1_Conf, Arrow2_Zone, Arrow2_Conf, ..., EndTotal
    - One row per archer
    - Suitable for spreadsheet analysis
    
  Scenario: Archer Views Own Report
    Given session is completed
    When Archer logs in and views Reports
    Then Archer sees own session report:
    - Own scores table
    - Own end images (zoomed focus)
    - Own statistics
    Cannot see other archers' data
```

**Acceptance Criteria**:
- ✅ Report generated dynamically from database
- ✅ PDF includes images and charts
- ✅ CSV includes all score data with proper formatting
- ✅ JSON format also available for API consumers
- ✅ Archer isolation enforced in reports

---

## Story RPT-002: Tournament Leaderboard & Rankings

**Phase**: Phase 1 (Essential)  
**Personas**: Tournament Admin, Archer  
**Depends On**: SCORE-003 (session complete or in progress)  

```gherkin
Feature: Leaderboard & Rankings
  Scenario: Admin Views Live Leaderboard During Session
    Given session is active
    When Admin navigates to Leaderboard page
    Then live leaderboard displays:
    - Archer name, total score, X count, rank
    - Sorted by: total score (descending), then X count (descending)
    - Updates in real-time as scores are confirmed
    - Shows progress: "End 3/6" for all archers
    
  Scenario: Archer Sees Own Position on Leaderboard
    Given Archer is logged in during active session
    When Archer views leaderboard
    Then Archer sees:
    - Own name, score, rank highlighted
    - Other archers' names and scores (aggregate only)
    - Cannot see individual arrow details of others
    
  Scenario: Final Rankings After Session Complete
    Given session status is "completed"
    When viewing final rankings
    Then rankings are locked (no changes possible)
    And "Champion" badge shown to top 3
    And export as PDF available for official records
```

**Acceptance Criteria**:
- ✅ Leaderboard updates in real-time
- ✅ Sorting by score (primary), X count (tiebreaker)
- ✅ Archer sees aggregated data only
- ✅ Final rankings immutable post-completion

---

# FEATURE 7: REAL-TIME FEATURES (WebSocket)

## Story RT-001: WebSocket Server Handles Live Connections

**Phase**: Phase 1 (Essential)  
**Personas**: System Admin, Scorer  
**Depends On**: None (infrastructure)  

```gherkin
Feature: WebSocket Real-Time Communication
  Scenario: Multiple Clients Connect to WebSocket Server
    Given backend WebSocket server running on ws://host:8000/ws
    When 5 scorers connect simultaneously via browser
    Then all connections accepted and maintained
    And each connection assigned unique ID
    And connection data stored: client_id, connected_at, user_id
    
  Scenario: WebSocket Handles Disconnection Gracefully
    Given 5 clients connected
    When 1 client connection drops (network failure)
    Then server detects disconnect within 5 seconds
    And connection resources cleaned up
    And remaining 4 clients unaffected
    
  Scenario: WebSocket Server Scales to 4+ Concurrent Cameras
    Given each camera streams to one WebSocket channel
    When 4 cameras send MJPEG frames simultaneously
    Then server handles all streams without blocking
    And each client receives own camera stream
    And server CPU/memory utilization acceptable
```

**Acceptance Criteria**:
- ✅ WebSocket server handles 4+ concurrent connections
- ✅ Graceful disconnect handling
- ✅ Message delivery reliable (no lost frames)
- ✅ Server resources monitored

---

## Story RT-002: Live Score Updates Broadcast to Connected Clients

**Phase**: Phase 1 (Essential)  
**Personas**: Scorer, Tournament Admin, Archer  
**Depends On**: RT-001, SCORE-003  

```gherkin
Feature: Real-Time Score Broadcasting
  Scenario: Score Confirmation Broadcasts to All Users
    Given Scorer confirms a score
    When score is saved to database
    Then WebSocket broadcast sent to all connected clients:
    - Event: "score_confirmed"
    - Data: {archer_id, end_number, new_score, total_score}
    And all browsers receive update within 100ms
    And leaderboard updates on all screens simultaneously
    
  Scenario: Tournament Admin Sees Live Score Updates
    Given Admin is viewing leaderboard
    When Scorer confirms scores on different cameras
    Then leaderboard rows update in real-time
    And rankings recalculate and refresh
    And visual highlight shows newly updated rows (brief animation)
    
  Scenario: Archer Sees Own Score Update
    Given Archer is viewing own scores page
    When Scorer confirms Archer's score
    Then Archer's score appears within 200ms
    And end total recalculates
    And visual confirmation: green checkmark appears briefly
```

**Acceptance Criteria**:
- ✅ Score broadcast within 100ms of database write
- ✅ All connected clients receive update
- ✅ Update includes sufficient data for UI refresh
- ✅ No polling required (push-based)

---

# FEATURE 8: ERROR RECOVERY

## Story ERR-001: System Handles Camera Disconnect During Scoring

**Phase**: Phase 1 (Essential)  
**Personas**: Scorer  
**Depends On**: SCORE-001  

```gherkin
Feature: Camera Disconnect Recovery
  Scenario: Camera Disconnects During Image Capture
    Given [Calculate] button pressed on a camera
    When camera connection drops mid-capture
    Then processing fails gracefully
    And error modal appears: "Camera disconnected during capture"
    And suggestions provided:
    - "Reconnect camera and press [Retake]"
    - "Or press [Skip] to move to next archer"
    
  Scenario: Auto-Reconnect Mechanism
    Given camera disconnects
    When system detects disconnection
    Then camera status changes to "reconnecting" (amber)
    And system re-probes connection every 5 seconds
    When camera reconnects
    Then status changes to "connected" (green)
    And UI message: "Camera reconnected successfully"
    
  Scenario: Scorer Can Retake Score After Recovery
    Given camera was disconnected and is now reconnected
    When Scorer clicks [Retake] button
    Then camera triggers new capture immediately
    And previous failed attempt is discarded
    And new scoring result displayed
```

**Acceptance Criteria**:
- ✅ Disconnect detected within 5 seconds
- ✅ Error message clear and actionable
- ✅ [Retake] button available to re-attempt
- ✅ No data loss or corruption

---

## Story ERR-002: Session Recovery After Network Outage

**Phase**: Phase 2 (Desirable)  
**Personas**: Scorer, Tournament Admin  
**Depends On**: ERR-001  

```gherkin
Feature: Network Outage Recovery
  Scenario: Scorer Connection Drops and Reconnects
    Given Scorer is actively scoring
    When network connection drops
    Then [Calculate] button becomes disabled
    And message: "Connection lost. Reconnecting..."
    When network is restored
    Then connection re-established
    And [Calculate] button becomes enabled again
    And message: "Connection restored"
    And no scores are lost
    
  Scenario: Confirm Score While Offline (Future Enhancement)
    Given Scorer presses [Calculate] during offline period
    When result is calculated locally (some browsers)
    Then score queued for upload
    When network is restored
    Then queued score is uploaded atomically
    And server processes as normal score
    
  Scenario: Session State Consistency
    Given network outage occurred mid-end
    When connection restored
    Then session re-syncs:
    - Latest scores from server
    - Current end number
    - Leaderboard state
    And Scorer's view matches server state
```

**Acceptance Criteria**:
- ✅ Offline/online state clearly displayed
- ✅ Graceful re-sync on reconnection
- ✅ No duplicate scores created
- ✅ Session state consistent between server and clients

---

# FEATURE 9: PERFORMANCE & OPTIMIZATION

## Story PERF-001: Scoring Completes in Under 1 Second

**Phase**: Phase 1 (Essential)  
**Personas**: Scorer  
**Depends On**: SCORE-001 (image processing pipeline)  

```gherkin
Feature: Performance - Scoring Speed
  Scenario: Capture to Result Display < 1 Second
    Given [Calculate] is pressed
    When image capture, processing, and result generation completes
    Then total elapsed time is < 1 second
    Breakdown:
    - Capture: ~200ms
    - Image preprocessing: ~300ms
    - Ring detection: ~200ms
    - Arrow detection: ~150ms
    - Score calculation: ~50ms
    
  Scenario: Performance Targets Under Load
    Given 4 cameras scoring simultaneously
    When each triggers [Calculate] within 100ms of each other
    Then each completes within 1 second
    And no queuing delays
    
  Scenario: Performance Monitoring
    Given scoring is complete
    Then processing time recorded: {capture_time, preprocess_time, detect_time, score_time}
    And if any stage exceeds threshold, logged as performance warning
```

**Acceptance Criteria**:
- ✅ Total scoring < 1 second (p95 latency)
- ✅ No image processing bottlenecks
- ✅ Performance telemetry logged
- ✅ Monitoring alerts if targets missed

---

## Story PERF-002: System Supports 4+ Concurrent Cameras

**Phase**: Phase 1 (Essential)  
**Personas**: System Admin  
**Depends On**: SCORE-001  

```gherkin
Feature: Performance - Concurrent Cameras
  Scenario: 4 Cameras Scoring Simultaneously
    Given 4 cameras with live previews streaming
    When each camera [Calculate] pressed in rapid succession
    Then processing parallelized (asyncio or threading)
    And all 4 results returned within 1-2 seconds
    And no camera blocks another
    And server CPU/memory utilization acceptable
    
  Scenario: Live Preview Quality with 4 Cameras
    Given 4 live previews streaming at 15 fps each
    Then combined bandwidth: ~2 Mbps
    And all previews remain smooth (no frame drops)
    And client browser handles rendering efficiently
    
  Scenario: Database Write Concurrency
    Given 4 scores being saved simultaneously
    Then all writes succeed atomically
    And no race conditions (duplicate records, etc.)
    And transaction isolation prevents conflicts
```

**Acceptance Criteria**:
- ✅ 4+ concurrent captures processed without serialization
- ✅ Each camera has < 1 second response time
- ✅ Live previews maintain 15 fps quality
- ✅ Database transactions handle concurrent writes

---

# FEATURE 10: DATA RETENTION & ARCHIVAL

## Story DATA-001: Auto-Retention Policy Enforced

**Phase**: Phase 2 (Desirable)  
**Personas**: System Admin  
**Depends On**: DATA storage  

```gherkin
Feature: Data Retention & Auto-Archival
  Scenario: Raw Images Retained for 90 Days
    Given raw images stored in storage/raw/
    When 90 days pass since image captured
    Then automatic archival job runs:
    - Raw image moved to storage/archive/
    - Annotated image kept in storage/annotated/
    - Database record updated with archive path
    
  Scenario: Storage Quota Monitoring
    Given system has 10 GB storage quota
    When storage usage reaches 80% (8 GB)
    Then admin notification sent: "Storage at 80% capacity"
    When storage reaches 90% (9 GB)
    Then auto-archival accelerates: older images moved sooner
    And admin notification: "Storage at 90% — auto-archiving active"
    
  Scenario: Operator Cannot Delete Scores
    Given a score exists
    When Operator tries to delete score
    Then deletion is prevented
    And message: "Scores cannot be deleted (immutable audit trail)"
    And only System Admin can manually archive data
```

**Acceptance Criteria**:
- ✅ Retention policy enforced by background job
- ✅ Storage quota monitored automatically
- ✅ Alerts sent at 80% and 90%
- ✅ Immutable audit trail (no deletions)

---

## Story Data Summary Checklist

**Phase 1 (Essential - Must Complete First Release)**: 18 stories
- USR-001 through USR-003
- CAM-001 through CAM-003
- SES-001 through SES-004
- SCORE-001 through SCORE-003
- SCORE-OVERRIDE-001, 002
- PERM-001, 002
- RPT-001, 002
- RT-001, 002
- ERR-001
- PERF-001, 002

**Phase 2 (Desirable - Can Defer)**: 3 stories
- SCORE-OVERRIDE-003, 004
- ERR-002
- DATA-001

**Total Stories**: 21 Feature Stories across 10 feature areas

---

## Story Dependencies Summary

```
USR-001 (Login)
    ├→ USR-002 (Create Users)
    │    └→ USR-003 (Permission Enforcement)
    │
    ├→ CAM-001 (Camera Discovery)
    │    ├→ CAM-002 (Camera Config)
    │    └→ CAM-003 (Live Preview)
    │
    ├→ SES-001 (Create Tournament)
    │    ├→ SES-002 (Create Session)
    │    │    ├→ SES-003 (Register Archers)
    │    │    │    └→ SES-004 (Start Session)
    │    │
    ├→ SCORE-001 (Trigger Scoring)
    │    ├→ SCORE-002 (Review Results)
    │    │    ├→ SCORE-003 (Confirm Score)
    │    │    ├→ SCORE-OVERRIDE-001 (Low Conf Detection)
    │    │    │    ├→ SCORE-OVERRIDE-002 (Override Arrow)
    │    │    │    │    └→ SCORE-OVERRIDE-003 (Override End)
    │    │    │    │         └→ SCORE-OVERRIDE-004 (View Log)
    │
    ├→ RPT-001 (View Reports)
    │    └→ RPT-002 (Leaderboard)
    │
    ├→ RT-001 (WebSocket Server)
    │    └→ RT-002 (Score Broadcast)
    │
    ├→ ERR-001 (Camera Disconnect)
    │    └→ ERR-002 (Network Outage)
    │
    ├→ PERF-001 (Scoring < 1s)
    └→ PERF-002 (4+ Cameras)
```

---

## Traceability Matrix: Stories ↔ Personas ↔ Features

| Story ID | Persona(s) | Feature Area | Phase | Dependencies |
|---|---|---|---|---|
| USR-001 | All | Authentication | 1 | None |
| USR-002 | Admin → All | User Management | 1 | USR-001 |
| USR-003 | Archer, Admin | Access Control | 1 | USR-002 |
| CAM-001 | Admin | Camera Discovery | 1 | None |
| CAM-002 | Admin | Camera Config | 1 | CAM-001 |
| CAM-003 | Scorer | Live Preview | 1 | CAM-001, USR-001 |
| SES-001 | Tournament Admin | Tournament Setup | 1 | USR-001 |
| SES-002 | Tournament Admin | Session Setup | 1 | SES-001 |
| SES-003 | Tournament Admin | Archer Registration | 1 | SES-002 |
| SES-004 | Tournament Admin, Scorer | Session Start | 1 | SES-003, CAM-002 |
| SCORE-001 | Scorer | Scoring Trigger | 1 | SES-004, CAM-003 |
| SCORE-002 | Scorer | Score Display | 1 | SCORE-001 |
| SCORE-003 | Scorer | Score Confirmation | 1 | SCORE-002 |
| SCORE-OV-001 | Scorer | Low Conf Flag | 1 | SCORE-002 |
| SCORE-OV-002 | Scorer | Override Arrow | 1 | SCORE-OV-001 |
| SCORE-OV-003 | Scorer | Override End | 2 | SCORE-OV-002 |
| SCORE-OV-004 | Admin, Scorer | Override Log | 2 | SCORE-OV-003 |
| PERM-001 | Archer, Admin | Archer Isolation | 1 | USR-003 |
| PERM-002 | Scorer, Admin | Role-Based Features | 1 | USR-001 |
| RPT-001 | Admin, Archer | Report Access | 1 | SCORE-003 |
| RPT-002 | Admin, Archer | Leaderboard | 1 | SCORE-003 |
| RT-001 | Admin, Scorer | WebSocket Infrastructure | 1 | None |
| RT-002 | Scorer, Admin, Archer | Live Broadcast | 1 | RT-001, SCORE-003 |
| ERR-001 | Scorer | Camera Disconnect | 1 | SCORE-001 |
| ERR-002 | Scorer, Admin | Network Recovery | 2 | ERR-001 |
| PERF-001 | Scorer | Scoring Speed | 1 | SCORE-001 |
| PERF-002 | Admin | Concurrent Cameras | 1 | SCORE-001 |
| DATA-001 | Admin | Retention Policy | 2 | Storage system |

---

## Story Acceptance Criteria Summary

**Total Acceptance Criteria**: 84 across 21 stories (~4 per story)

**High-Priority Stories for Development** (Phase 1, blocking multiple others):
1. USR-001 (blocks all features requiring login)
2. SCORE-001 (core feature)
3. SES-004 (enables scoring operations)
4. RT-001 (enables real-time features)

**Quality Gates for Stories**:
- ✅ Each story has 3-4 acceptance criteria (not 1-2)
- ✅ Each story includes error/edge case scenarios
- ✅ Concurrency handled in criteria (not deferred)
- ✅ Performance targets embedded (not separate doc)
- ✅ Security/permission checks explicit (not assumed)

---

## Next Steps for Development Teams

**For Backend Agent**:
- API design based on story "When Scorer" actions (POST /score/calculate, etc.)
- Database schema designed to support all stories
- Image processing pipeline implements all acceptance criteria
- Error handling covers all story failure scenarios
- Permission checks implemented per PERM stories

**For Frontend Agent**:
- UI pages designed from story flows (scoring page, reports page, etc.)
- Real-time updates via WebSocket per RT stories
- Error states and recovery flows per ERR stories
- Performance optimizations per PERF stories
- Permission-based UI hiding per PERM stories

**For Testing**:
- E2E test cases generated from story Given/When/Then
- Acceptance criteria become test assertions
- Security tests from permission stories
- Performance tests from PERF stories
- Concurrency tests from concurrent story scenarios
