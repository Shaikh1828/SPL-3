# Backend Unit — Functional Design Plan

**Project**: Automated Archery Scoring System  
**Unit**: Backend (Python/FastAPI)  
**Date**: 2026-05-23  
**Phase**: CONSTRUCTION - Functional Design (Part 1: Planning)  

---

## Context

The Backend Unit implements all server-side logic including:
- Authentication & authorization (4-role RBAC)
- Camera management (USB/RTSP enumeration)
- Tournament & session orchestration
- **Image processing pipeline** (scoring algorithm — PRIMARY FOCUS)
- Reporting and data queries
- Real-time event publishing
- Data persistence

### Primary Business Value
**Scoring Pipeline**: Transform camera images into archer scores with high accuracy and performance (< 1 second).

---

## Functional Design Focus

This plan focuses on detailed business logic, domain models, and validation rules that will guide code generation.

---

## Planning Checklist

- [ ] Understand scoring algorithm requirements
- [ ] Define domain entities and relationships
- [ ] Specify business rules and validation logic
- [ ] Model image processing pipeline stages
- [ ] Define error handling scenarios
- [ ] Specify authentication/authorization rules
- [ ] Define data transformations and persistence
- [ ] Ensure 60-70% test coverage approach is clear

---

## Questions for Backend Functional Design

### Category 1: Scoring Algorithm & Business Logic

**Q1: Ring Detection Method**

The application supports detecting target rings on archery targets. The scoring algorithm maps detected ring zones to point values.

Which ring detection method should be the **primary implementation**?

*Options*:
- **Option A**: Hough Circle Transform (detects concentric circles; robust to noise)
- **Option B**: Contour Analysis (finds ring boundaries via edge detection)
- **Option C**: Template Matching (compares against known target template)
- **Option D**: Machine Learning (CNN or trained detector; highest accuracy but slowest)
- **Option E**: Hybrid (Hough Circles as primary; fall back to Contour if fails)

[Answer]:A

---

**Q2: Arrow Detection Method**

After rings are detected, arrows must be localized within the target. Which arrow detection method should be **primary**?

*Options*:
- **Option A**: Color-based thresholding (detect arrow color; simple but fragile to lighting)
- **Option B**: Edge detection (find arrow shaft edges via Canny/Sobel)
- **Option C**: Contour analysis (detect arrow-shaped contours)
- **Option D**: Moment-based (find arrow center of mass)
- **Option E**: Hybrid (Multiple methods, vote on final position)

[Answer]:E

---

**Q3: Zone Scoring Mapping**

After detecting arrow position within target rings, the system maps position to point values. How many scoring zones should be defined?

*Options*:
- **Option A**: 3 zones (outer=4 pts, middle=6 pts, inner=10 pts)
- **Option B**: 5 zones (standard Olympic rings plus center)
- **Option C**: 10 zones (detailed scoring; finer granularity)
- **Option D**: 11 zones (per-ring including center separations)
- **Option E**: Configurable per tournament (admin defines at tournament creation)

[Answer]:D

---

**Q4: Confidence Scoring**

The scoring pipeline generates a confidence score (0-100%) indicating detection quality. How should confidence affect the scoring result?

*Options*:
- **Option A**: Always return result; confidence is informational only
- **Option B**: Flag results with confidence < 80% for manual review (but auto-accept)
- **Option C**: Auto-reject results with confidence < 60% (require retry)
- **Option D**: Confidence affects point calculation (e.g., 50% confidence = half points)
- **Option E**: Different thresholds per zone (inner zones stricter than outer)

[Answer]:B

---

**Q5: Burst Mode Image Selection**

The system captures **3 burst images** from camera when scoring triggered. Which image should be used for scoring?

*Options*:
- **Option A**: Always use first image (fastest)
- **Option B**: Always use middle image (potentially sharpest)
- **Option C**: Select sharpest via focus blur metric (slow, most accurate)
- **Option D**: Process all 3, take highest confidence result
- **Option E**: User selects from 3 preview images (manual selection)

[Answer]:C

---

### Category 2: Domain Entities & Relationships

**Q6: Score Entity Relationships**

In the database, a Score record represents one arrow. How should 3-arrow ends be stored?

*Options*:
- **Option A**: Three separate Score records with end_num tracking (arrow 1, arrow 2, arrow 3 within end)
- **Option B**: Single ScoreEnd record with array of 3 zone values
- **Option C**: Single Score record with all 3 zones in one JSON column
- **Option D**: Separate ArrowScore table for each arrow with foreign key to End

[Answer]:B

---

**Q7: Session State Machine**

Sessions transition through states as archers progress. What states should be tracked?

*Options*:
- **Option A**: CREATED → STARTED → COMPLETED (3 states)
- **Option B**: CREATED → STARTED → IN_PROGRESS → COMPLETED (4 states)
- **Option C**: CREATED → STARTED → PAUSED → RESUMED → COMPLETED (5 states)
- **Option D**: Allow arbitrary status strings (no predefined states)
- **Option E**: CREATED → STARTED → COMPLETED + separate per-archer status (ready, scoring, scored)

[Answer]:B

---

**Q8: User Roles Permissions Matrix**

The system has 4 roles with different permissions. Should permissions be:

*Options*:
- **Option A**: Hardcoded in decorators (@require_role(SYSTEM_ADMIN))
- **Option B**: Database-driven lookup (role → permissions from table)
- **Option C**: Configuration file (roles.yaml with permissions)
- **Option D**: Hybrid (predefined roles, but custom permissions assignable to roles)
- **Option E**: Role-less: individual user has list of capabilities

[Answer]:D

---

### Category 3: Business Rules & Validation

**Q9: Archer Score Override Validation**

Scorers can manually override calculated scores (if detection failed). What validation should apply?

*Options*:
- **Option A**: Allow any zone override (0-10 points) without restriction
- **Option B**: Only allow override if confidence < 50% (low confidence only)
- **Option C**: Allow override, but log reason and flag for audit
- **Option D**: Override requires TOURNAMENT_ADMIN approval (2-step process)
- **Option E**: Allow override, but revert to auto-detected if next arrow detects that zone reliably

[Answer]:B

---

**Q10: Camera Lane Assignment**

When cameras are assigned to lanes in a session, what constraints apply?

*Options*:
- **Option A**: No constraints; multiple cameras can view same lane
- **Option B**: Each lane must have exactly one camera (exclusive assignment)
- **Option C**: Cameras can share lanes if they have different angles
- **Option D**: Lane assignment is optional; cameras can be generic (not tied to lanes)
- **Option E**: Cameras assigned dynamically (each archer selects camera when scoring)

[Answer]:B

---

**Q11: Database Transaction Atomicity**

When scoring is calculated and stored, what should be atomic?

*Options*:
- **Option A**: Just the 3 score inserts (all-or-nothing for one end)
- **Option B**: Score inserts + camera status update (if disconnect during scoring)
- **Option C**: Score inserts + session state update + event publish
- **Option D**: Everything including WebSocket broadcast (all-or-nothing)
- **Option E**: No atomicity needed; eventual consistency acceptable

[Answer]:C

---

### Category 4: Image Processing & Data Flow

**Q12: Image Storage**

Captured images are stored on disk for audit trail. Where should raw images be stored?

*Options*:
- **Option A**: Never store (discard after scoring) — saves space
- **Option B**: Store all raw images `/storage/raw/` — audit trail
- **Option C**: Store only failed/low-confidence images (debug)
- **Option D**: Store all images in database as BLOB — simplifies migration
- **Option E**: Configurable retention (delete after N days)

[Answer]:B

---

**Q13: Annotated Image Generation**

The system optionally generates annotated images (rings and arrows marked). When should this happen?

*Options*:
- **Option A**: Always generate (for every score)
- **Option B**: Only on demand (when user views score detail)
- **Option C**: Never generate (too slow)
- **Option D**: Generate only for scores with confidence < 80% (debug lower confidence)
- **Option E**: Configurable per tournament (admin decides)

[Answer]:A

---

**Q14: Performance Profile — Scoring Breakdown**

The < 1 second target breaks down as: Capture 200ms + Preprocess 300ms + Ring Detect 200ms + Arrow Detect 150ms + Calc 50ms.

If a stage exceeds its budget, what should happen?

*Options*:
- **Option A**: Timeout and return error (fail immediately)
- **Option B**: Use faster but less accurate fallback method
- **Option C**: Return partial results (skip later stages)
- **Option D**: Accept latency if accuracy is preserved (ignore timing if needed)
- **Option E**: Warn but continue; log performance issues for later optimization

[Answer]:D

---

### Category 5: Error Handling & Recovery

**Q15: Image Processing Failure Scenarios**

If ring detection fails (no rings detected), how should the system respond?

*Options*:
- **Option A**: Return error immediately (fail fast)
- **Option B**: Retry with adjusted parameters (e.g., different Hough thresholds)
- **Option C**: Return generic score (middle zone, lower confidence)
- **Option D**: Request user override (UI shows captured image, user selects zone)
- **Option E**: Return null result; UI shows image for manual scoring

[Answer]:B

---

**Q16: Concurrent Scoring — Multi-Camera Conflict**

If 2+ archers score simultaneously on different cameras, could race conditions occur?

*Options*:
- **Option A**: Not a concern; each image processing thread independent
- **Option B**: Potential database race (both threads update same session record)
- **Option C**: Potential race in camera status tracking
- **Option D**: All potential races are acceptable (eventual consistency)
- **Option E**: Use database row locks to serialize scoring within session

[Answer]:E

---

### Category 6: Authentication & Authorization

**Q17: Token Scope & Permissions**

JWT token should include which information?

*Options*:
- **Option A**: user_id only (minimal; permissions fetched from DB on each request)
- **Option B**: user_id + role (role-based decisions made locally)
- **Option C**: user_id + role + specific_permissions (full authorization in token)
- **Option D**: user_id + tournament_id + session_id (session-scoped token)
- **Option E**: user_id + role + expiration only (refresh frequently)

[Answer]:D

---

**Q18: Archer Permissions Model**

An ARCHER user should see only their own scores. How should this be enforced?

*Options*:
- **Option A**: Repository query filter: `WHERE archer_id = current_user_id`
- **Option B**: Service layer check: verify archer_id matches before returning data
- **Option C**: API endpoint filter: transform response to exclude unauthorized scores
- **Option D**: Multiple layers (all three above — defense in depth)
- **Option E**: No enforcement (UI hides data, but API returns all if authenticated)

[Answer]:C

---

### Category 7: Data Persistence & Migrations

**Q19: Database Versioning & Migrations**

How should database schema changes be managed across deployments?

*Options*:
- **Option A**: Manual SQL scripts; run before deployment
- **Option B**: Alembic auto-migrations; run on startup
- **Option C**: No migrations; schema is static after first deploy
- **Option D**: Rollback-safe migrations (each migration has up/down)
- **Option E**: Immutable schema version; no schema evolution

[Answer]:A

---

**Q20: Testing Database**

For unit tests, should the Backend use:

*Options*:
- **Option A**: SQLite in-memory (fast, isolated)
- **Option B**: PostgreSQL test container (closest to prod)
- **Option C**: Mocked repository (no database)
- **Option D**: Hybrid (unit tests use mock, integration tests use real DB)
- **Option E**: Shared test database (one DB for all tests)

[Answer]:B

---

## Summary Table

| Category | Decision Point | Status |
|---|---|---|
| **Scoring Algorithm** | Primary ring detection method | Pending |
| **Arrow Detection** | Primary arrow detection method | Pending |
| **Zone Mapping** | Number of scoring zones | Pending |
| **Confidence Handling** | How confidence affects result | Pending |
| **Image Selection** | Which burst image to use | Pending |
| **Score Storage** | Entity relationship structure | Pending |
| **Session States** | State machine definition | Pending |
| **Role Permissions** | Hardcoded vs Database | Pending |
| **Override Validation** | Constraints on manual overrides | Pending |
| **Camera Assignment** | Lane mapping rules | Pending |
| **Atomicity** | Transaction scope | Pending |
| **Image Storage** | Raw image persistence | Pending |
| **Annotations** | Annotated image generation | Pending |
| **Performance** | Handling stage timeouts | Pending |
| **Failure Handling** | Ring detection failures | Pending |
| **Concurrency** | Race condition handling | Pending |
| **Token Scope** | JWT content | Pending |
| **Archer Permissions** | Enforcement layers | Pending |
| **Migrations** | Schema versioning | Pending |
| **Test Database** | Testing database strategy | Pending |

---

## Next Steps

1. **Review** the questions above
2. **Provide answers** to ALL [Answer]: tags
3. **Submit** completed plan for analysis
4. **Clarify** any ambiguous answers via follow-up questions
5. **Approve** functional design plan
6. **Proceed** to Part 2: Generation (create functional design artifacts)

