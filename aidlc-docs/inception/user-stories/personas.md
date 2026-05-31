# User Personas — Archery Scoring System

**Project**: Automated Archery Scoring System  
**Date**: 2026-05-23  
**Persona Depth**: Standard Detail (name, role, goals, pain points, workflows)  

---

## Persona 1: System Administrator

**Name**: Alex Chen  
**Role**: SYSTEM_ADMIN  
**Background**: IT operations professional with 8+ years managing tournament systems; responsible for infrastructure, deployments, and user management.

### Key Goals
- Ensure system uptime and reliability during tournament events
- Manage user accounts and permissions efficiently
- Monitor system health and camera connectivity
- Maintain data security and backup procedures
- Configure camera hardware and network settings

### Main Pain Points
- Complex camera setup and USB device management
- Users accidentally deleting important data
- System crashes during critical events
- Lack of visibility into system health
- Time-consuming manual user account creation

### Technical Proficiency
- High — comfortable with CLI, Docker, database administration
- Prefers automated solutions over manual processes
- Requires comprehensive logging and monitoring

### Typical Workflow
1. Deploy system before tournament event
2. Configure cameras and network settings
3. Create user accounts for tournament admin, scorers, archers
4. Monitor system during event (check cameras, storage, users online)
5. Troubleshoot connectivity issues when they arise
6. Perform daily backups post-event
7. Archive old data and manage storage quota

**Key Interaction Pattern**: Occasional interaction, but critical for system stability

---

## Persona 2: Tournament Administrator

**Name**: Patricia Rojas  
**Role**: TOURNAMENT_ADMIN  
**Background**: Experienced archery event organizer with 15+ years managing competitions; coordinates with venue, manages schedules, registers participants.

### Key Goals
- Create and manage tournament brackets and sessions
- Register archers and assign them to lanes/cameras
- View live leaderboard and final rankings
- Generate comprehensive tournament reports
- Export data for official records and media

### Main Pain Points
- Manual transcription of scores from paper forms (error-prone)
- Difficulty tracking scores across multiple lanes simultaneously
- Long delays in producing final rankings and reports
- Cannot verify scoring accuracy in real-time
- No audit trail if disputes arise

### Technical Proficiency
- Medium — comfortable with web interfaces and basic data management
- Prefers intuitive UI over command-line tools
- Needs clear reporting and export options

### Typical Workflow
1. Create new tournament in system
2. Define sessions (distance, end count, target size)
3. Register archers and assign to lanes
4. Start session and monitor live scoring
5. View live leaderboard throughout event
6. At session end: review final rankings and statistics
7. Generate PDF report for official records
8. Export CSV for media/publication

**Key Interaction Pattern**: Heavy interaction during tournament events (full day), light outside events

---

## Persona 3: Scorer / Operator

**Name**: Marcus Thompson  
**Role**: SCORER / OPERATOR  
**Background**: Certified archery range operator with 6+ years experience; operates scoring system during competitions; handles all scoring operations and manages cameras.

### Key Goals
- Score targets quickly and accurately
- Verify scoring accuracy before confirming
- Handle scoring corrections/overrides when needed
- Keep scoring process moving without delays
- Maintain clear audit trail of all scores and changes

### Main Pain Points
- Manual scoring is slow and error-prone (15% inconsistency)
- Disputes over whether arrows are in/out of ring
- Difficulty tracking scores across multiple ends
- No visual proof of scoring decision
- Manual override process is unclear

### Technical Proficiency
- Low-Medium — familiar with scoring process, but not highly technical
- Needs clear, intuitive UI with minimal learning curve
- Prefers visual feedback (images, confidence levels)

### Typical Workflow
1. Log in to system with credentials
2. Select active session and assigned camera/lane
3. Monitor live camera preview
4. When archer shoots: press [Calculate] button
5. Review automatically detected score and annotated image
6. If low confidence or disputed: review annotated image details
7. Optionally override score with reason
8. Confirm score and move to next arrow/end
9. View running totals and end summaries

**Key Interaction Pattern**: Continuous interaction during event (8+ hours), heavy button pressing and decision-making

---

## Persona 4: Archer

**Name**: Jennifer Wu  
**Role**: ARCHER  
**Background**: Competitive archer; participant in tournament events; interested in viewing own scores and performance data.

### Key Goals
- View own scores after each end
- See annotated images of own shots
- Access personal performance report
- Download personal statistics
- Understand scoring decisions (especially overrides)

### Main Pain Points
- Long wait for manual scoring results
- Lack of visibility into scoring process
- Cannot verify their own score accuracy
- No easy way to access personal data post-event
- Disputes over scoring decisions feel arbitrary

### Technical Proficiency
- Low — prefers simple, straightforward interfaces
- Doesn't care about technical details; wants results
- Needs clear visual feedback (score, images, explanations)

### Typical Workflow
1. Log in with archer account
2. View current session and own status
3. After shooting: see own scores appear in real-time
4. Click on score to view annotated image of target
5. At session end: download personal PDF report
6. Access personal leaderboard ranking

**Key Interaction Pattern**: Sporadic interaction (checking scores between rounds, mostly viewing/read-only)

---

## Persona Summary Table

| Attribute | System Admin | Tournament Admin | Scorer | Archer |
|---|---|---|---|---|
| **Primary Goal** | System stability | Manage tournament | Score accurately | View own results |
| **Tech Proficiency** | High | Medium | Low-Medium | Low |
| **Interaction Frequency** | Occasional (critical) | Heavy (event days) | Continuous (event) | Sporadic (results check) |
| **Feature Access** | System config, users, monitoring | Tournament/session mgmt, reports | Scoring, cameras, live data | View own scores only |
| **Key Frustration** | Downtime, complexity | Manual work, delays | Accuracy disputes | Wait times |
| **Success Metric** | Zero outages | Fast tournaments, clear records | Accurate, auditable scores | Quick access to results |

---

## Persona-Feature Interaction Map

| Feature | Admin | Tourn Admin | Scorer | Archer |
|---|---|---|---|---|
| **User Management** | ✅ Create/edit/delete | ❌ | ❌ | ❌ |
| **Tournament/Session Management** | ✅ Admin only | ✅ Full mgmt | ❌ Read-only | ❌ View only |
| **Camera Configuration** | ✅ Setup/manage | ❌ | ✅ Assign in session | ❌ |
| **Live Scoring** | ❌ | ❌ | ✅ Trigger/confirm | ❌ |
| **Score Override** | ✅ Override any | ✅ View history | ✅ Own scores only | ❌ |
| **Reports & Analytics** | ✅ All data | ✅ All tournament data | ✅ Session data | ✅ Own data only |
| **Camera Monitoring** | ✅ Full visibility | ✅ Status indicator | ✅ During scoring | ❌ |

---

## Persona Validation Notes

All 4 personas represent **real, distinct users** in the Archery Scoring System:
- Each has **unique access levels** based on role
- Each has **different primary workflows** (setup vs operate vs view)
- Each has **genuine pain points** the system addresses
- Each has **clear success criteria** that stories will validate

**Secondary Personas NOT Created** (sufficient value in primary roles):
- No "tech-savvy scorer vs technophobe scorer" variants (one UI works for both)
- No "spectator" persona (out of initial scope)
- No separate "IT admin" vs "SYSTEM_ADMIN" (same person)

**Stories will map to these 4 personas explicitly** in cross-reference matrix.
