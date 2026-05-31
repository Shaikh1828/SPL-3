# Application Design Plan

**Project**: Automated Archery Scoring System — Web Application  
**Phase**: INCEPTION - Application Design  
**Date**: 2026-05-23  
**Status**: Plan created, awaiting user decisions  

---

## Overview

This document guides the creation of application design artifacts. Based on your 21 user stories and comprehensive requirements, we'll design:

1. **Components** — Functional units (Domain Models, Services, API Handlers)
2. **Component Methods** — High-level method signatures and responsibilities
3. **Services** — Business logic orchestrators
4. **Component Dependencies** — How components communicate and coordinate

**Important**: Detailed business logic rules (scoring algorithm, validation logic, etc.) will be designed in Functional Design (per-unit, CONSTRUCTION phase). This phase focuses on architectural structure and interfaces.

---

## Design Plan with Checkboxes

### Step 1: Component Identification
- [ ] **1.1** Analyze domain (Tournaments, Sessions, Archers, Scores, Annotations, Audit Logs)
- [ ] **1.2** Identify service layer (Scoring Service, Auth Service, Reports Service, Session Manager, Camera Manager)
- [ ] **1.3** Identify API layer (REST endpoints, WebSocket handlers)
- [ ] **1.4** Determine domain models and their responsibilities

### Step 2: Component Structure & Responsibilities
- [ ] **2.1** Define core domain components and their boundaries
- [ ] **2.2** Define API handler components (route handlers for each endpoint)
- [ ] **2.3** Define service components (business logic orchestrators)
- [ ] **2.4** Establish component grouping strategy

### Step 3: Component Methods & Interfaces
- [ ] **3.1** Define methods for each component
- [ ] **3.2** Specify method signatures (inputs, outputs)
- [ ] **3.3** Document interface contracts

### Step 4: Service Layer Design
- [ ] **4.1** Define service responsibilities and boundaries
- [ ] **4.2** Determine service orchestration patterns
- [ ] **4.3** Define cross-service communication

### Step 5: Component Dependencies
- [ ] **5.1** Map component relationships
- [ ] **5.2** Identify communication patterns
- [ ] **5.3** Establish data flow

### Step 6: Validation & Consistency
- [ ] **6.1** Validate design completeness
- [ ] **6.2** Check for consistency across design
- [ ] **6.3** Confirm all stories are supported

---

## Design Decision Questions

**Answer each question below by replacing `[Answer]:` with your response. These decisions will guide the application architecture.**

### Question Group 1: Component Organization Strategy

---

**Q1.1: Component Grouping Approach**

How should we organize components? Consider these options:

- **A) Layered Architecture** — Components organized by technical layer (Models → Services → API Routes)
- **B) Domain-Driven Design** — Components organized by business domain (Tournament Subdomain, Scoring Subdomain, Reporting Subdomain, etc.)
- **C) Feature-Based Organization** — Components organized by feature (Camera Management, Session Management, Scoring, Reports, Auth, etc.)
- **D) Hybrid Approach** — Domain-driven domains with layered services inside each domain

[Answer]: C

---

**Q1.2: Service Layer Boundaries**

How many service layer components should exist? Consider these options:

- **A) Monolithic Service** — One large "Application Service" that orchestrates everything
- **B) Functional Services** — Multiple services by function (AuthService, ScoringService, ReportService, SessionService, CameraService, etc.) — ~6-8 services
- **C) Domain Services** — Services organized by business domain (TournamentService, ScoringService, ReportingService) — ~3-4 services
- **D) Microservice-style** — Each story/feature gets its own service (overly granular for greenfield)

[Answer]: B

---

**Q1.3: API Handler Organization**

How should REST API routes be organized? Consider these options:

- **A) Monolithic Routes** — All routes in single router module
- **B) Feature-Based Routers** — Each feature has its own router (auth.py, sessions.py, scoring.py, etc.)
- **C) Resource-Based Routers** — Each resource type (tournaments, archers, scores, reports) has its own router
- **D) Hybrid** — Feature routers with resource sub-organization

[Answer]: B

---

### Question Group 2: Key Components & Methods

---

**Q2.1: Authentication Component**

The system requires JWT authentication with 8-hour expiration and httpOnly cookies. Should auth be:

- **A) Integrated into each handler** — Auth logic copied into route handlers
- **B) Central AuthService** — Single service handling login, logout, token validation, refresh
- **C) Middleware Component** — Middleware component for auth checks, with separate service for token management
- **D) No separate component** — Use FastAPI's built-in dependency injection fully

[Answer]: B

---

**Q2.2: Scoring Pipeline Component**

Scoring requires: capture → preprocessing → detection → zone calculation → confidence evaluation → storage. Should this be:

- **A) Single ScoringService** — One service method `score_end(camera_id, archer_id, end_num)` that orchestrates entire pipeline
- **B) Pipeline Components** — Separate components: `ImageCaptureComponent`, `PreprocessComponent`, `DetectionComponent`, `ScoringComponent`, each with own responsibility
- **C) Hybrid** — ScoringService orchestrates, but delegates to focused components for each stage
- **D) Stateful Machine** — Scoring as a state machine component with state transitions

[Answer]: C

---

**Q2.3: Permission & Authorization Component**

System requires 4-role RBAC (SYSTEM_ADMIN, TOURNAMENT_ADMIN, SCORER, ARCHER) with object-level permissions (Archer can only see own data). Should this be:

- **A) Centralized Authorization Service** — `AuthorizationService.can_access(user, resource, action)` used everywhere
- **B) Role-Based Decorators** — FastAPI dependencies for role checking, object-level checks in handlers
- **C) Permission Matrix Component** — `PermissionComponent` with `has_permission(user, resource, action)` that returns boolean
- **D) Distributed Checks** — Each handler implements its own authorization checks

[Answer]: B

---

**Q2.4: Reporting Component**

Reports need PDF, CSV, JSON export. Should reporting be:

- **A) Single ReportService** — `generate_report(session_id, format)` handles all formats
- **B) Report Generators** — `PDFReportGenerator`, `CSVReportGenerator`, `JSONReportGenerator` as separate components
- **C) Template-Based** — Single template engine that adapts to different formats
- **D) Query-Based** — Reports as saved queries that can output in different formats

[Answer]: B

---

### Question Group 3: Service Layer Design

---

**Q3.1: WebSocket Architecture**

Live score broadcasting and camera preview require WebSocket. Should WebSocket be:

- **A) Part of Main Service** — Integrated into FastAPI main application
- **B) Separate WebSocket Service** — Dedicated WebSocket service component that main API calls
- **C) Event-Driven** — Event bus where services publish events (score confirmed, camera updated) and WebSocket subscribes
- **D) Direct Integration** — Each service directly notifies WebSocket handler of changes

[Answer]: C

---

**Q3.2: Database Access Layer**

Should database access be:

- **A) Direct Repository Pattern** — Each component has its own Repository (UserRepository, ScoreRepository, etc.)
- **B) ORM Only** — Use SQLAlchemy ORM directly in services, no separate data layer
- **C) Data Access Service** — Central DataService that all components use for database access
- **D) Query Objects** — Encapsulated Query objects that represent database operations

[Answer]: A

---

**Q3.3: Error Handling & Recovery**

How should error handling be structured? Consider:

- **A) Service Layer** — Services throw domain exceptions; handlers catch and convert to HTTP responses
- **B) Centralized Handler** — Global error handler that catches all exceptions and converts to responses
- **C) Component-Level** — Each component handles its own errors and returns success/failure status
- **D) Result Type** — Services return Result<T> (Success or Failure) instead of throwing exceptions

[Answer]: A

---

### Question Group 4: Component Dependencies & Communication

---

**Q4.1: Synchronous vs Asynchronous Communication**

Score processing and image analysis can be slow (200-1000ms). Should component communication be:

- **A) Synchronous** — Caller waits for response (traditional request/response)
- **B) Asynchronous** — Caller gets immediate acknowledgment; work happens in background (FastAPI Background Tasks)
- **C) Hybrid** — Synchronous for critical path (auth, validation); async for heavy work (image processing, reporting)
- **D) Queue-Based** — Services communicate via message queue (Celery, RabbitMQ) for loose coupling

[Answer]: A

---

**Q4.2: Data Sharing Between Components**

How should components share data (especially large data like images)? Consider:

- **A) Parameter Passing** — Pass data directly between components in memory
- **B) Database** — Components write data to database; other components query it
- **C) Cache Layer** — Use Redis/cache for temporary data sharing between components
- **D) File Storage** — Write to disk/object storage; components reference via path/URL

[Answer]: B

---

**Q4.3: Dependency Injection**

How should component dependencies be managed? Consider:

- **A) Constructor Injection** — Components receive dependencies in constructor
- **B) FastAPI Dependency Injection** — Use FastAPI's `Depends()` for dependency injection
- **C) Service Locator** — Central registry that components query for dependencies
- **D) Manual Wiring** — Each handler creates and wires components as needed

[Answer]: B

---

### Question Group 5: Design Patterns & Constraints

---

**Q5.1: State Management for Sessions**

Tournament sessions have complex state (pending → active → completed). Should state be:

- **A) Database-Backed** — Session state stored in database; read on each operation
- **B) In-Memory** — Session state in memory (Server object); query database for persistence
- **C) State Machine** — Explicit state machine component that validates state transitions
- **D) Event Sourcing** — Session state derived from events (session created, started, ended)

[Answer]: A

---

**Q5.2: Multi-Camera Coordination**

System must support 4+ cameras scoring simultaneously. Should coordination be:

- **A) Synchronous Processing** — Each camera request waits for response; no parallel processing
- **B) Async per Camera** — Each camera processed in background task independently
- **C) Thread Pool** — Use thread pool to process multiple cameras concurrently
- **D) Process Pool** — Use separate processes for each camera (for CPU-intensive image processing)

[Answer]: C

---

**Q5.3: Real-Time Live Preview**

Camera preview streams 15 fps via WebSocket. Should preview streaming be:

- **A) Push-Based** — Server continuously pushes frames to connected clients
- **B) Pull-Based** — Clients request frames on demand
- **C) Selective Push** — Server pushes only when frame changes significantly (motion detection)
- **D) Hybrid** — Initial push stream, clients can request specific frame if needed

[Answer]: D

---

**Q5.4: Component Coupling Tolerance**

How tight should component coupling be? Consider:

- **A) Loosely Coupled** — Components communicate via interfaces; minimal knowledge of internals
- **B) Moderately Coupled** — Components can depend on concrete implementations; some direct knowledge
- **C) Pragmatic** — Couple where it makes sense (auth everywhere), separate where needed (services from handlers)
- **D) Framework-Managed** — Use FastAPI framework to manage coupling; rely on dependency injection

[Answer]: B

---

## User Decision Summary

**Once you've answered all questions above:**

1. Replace each `[Answer]:` tag with your response (choose option A, B, C, or D, or provide custom answer)
2. Review your answers for consistency
3. Return this file to the AI with all answers filled in
4. The AI will:
   - Analyze your answers for ambiguities
   - Ask follow-up questions if needed
   - Generate detailed application design artifacts
   - Present for final approval

---

## Next Steps

**Please complete:**
1. Answer all 14 questions by replacing `[Answer]:` tags
2. Return this document with all answers filled in
3. The AI will review for consistency and generate design artifacts

**Ready to proceed? Fill in all [Answer]: tags above and respond when complete.**

