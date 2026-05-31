# Unit of Work Decomposition Plan

**Project**: Automated Archery Scoring System  
**Date**: 2026-05-23  
**Phase**: Units Generation - Part 1: Planning  

---

## System Decomposition Overview

Based on **Application Design** and **Execution Plan**, the system is being decomposed into manageable units of work. The execution plan identified **Backend and Frontend** as the primary decomposition strategy, with independent development teams.

### Initial Decomposition (From Execution Plan)
- **Backend Unit** — Python/FastAPI services, image processing, database, API
- **Frontend Unit** — React/TypeScript UI, state management, WebSocket client

### Decision: Confirm Decomposition Strategy

This plan will validate and refine this decomposition through structured questions.

---

## Part 1: Planning Checklist

- [ ] Confirm unit decomposition strategy (Backend + Frontend)
- [ ] Define unit responsibilities and boundaries
- [ ] Map stories to units
- [ ] Identify inter-unit dependencies
- [ ] Determine team alignment
- [ ] Define code organization strategy
- [ ] Validate shared resources and integration points
- [ ] Document deployment model

---

## Questions for Unit Decomposition

### Category 1: Unit Decomposition & Boundaries

**Q1: Backend-Frontend Decomposition Confirmation**

The execution plan proposes decomposing the system into two units:
- **Backend Unit** — FastAPI server, image processing, PostgreSQL, WebSocket server
- **Frontend Unit** — React browser app, Zustand state, WebSocket client

Does this two-unit decomposition align with your vision?

[Answer]: Yes

---

**Q2: Backend Unit Scope**

Should the Backend unit be further subdivided into smaller modules, or remain as a single monolithic FastAPI service?

*Examples*:
- **Option A**: Single monolithic FastAPI service (one `main.py`, all routes/services together)
- **Option B**: Modular FastAPI app (separate modules: `core/`, `services/`, `handlers/`, `components/`)
- **Option C**: Multi-service architecture (separate services: AuthService, ScoringService, ReportService as independent processes)

[Answer]: B

---

**Q3: Frontend Unit Scope**

Should the Frontend unit be further subdivided, or remain as a single cohesive React application?

*Examples*:
- **Option A**: Single monolithic React app (all features in one application)
- **Option B**: Feature-based module organization (features as separate directories with own routes)
- **Option C**: Multi-package monorepo (separate npm packages for core, features, UI components)

[Answer]: B

---

### Category 2: Story Grouping & Unit Assignment

**Q4: Story Assignment to Units**

The 21 user stories should be assigned to either Backend or Frontend. Some stories involve both (e.g., USR-001 Login requires both auth backend and login UI).

For stories that span both units, what approach should we use?

*Examples*:
- **Option A**: Assign the story to the unit with the critical path (e.g., USR-001 Login → Backend, since auth is backend-critical)
- **Option B**: Create "integration stories" that explicitly require both units (mark as cross-unit dependency)
- **Option C**: Split hybrid stories into separate backend and frontend stories with explicit link

[Answer]: A

---

**Q5: Story Grouping Strategy**

Should stories within each unit be grouped into smaller chunks for organization?

*Examples*:
- **Option A**: No sub-grouping; all stories in the unit treated as flat list
- **Option B**: Group by feature area (Camera stories together, Session stories together, etc.)
- **Option C**: Group by priority/phase (Phase 1 essential stories separate from Phase 2 desirable)
- **Option D**: Hybrid (group by feature area AND priority)

[Answer]: B

---

### Category 3: Inter-Unit Dependencies & Communication

**Q6: API Contract Approach**

The Backend exposes REST API endpoints and WebSocket connections. The Frontend consumes these APIs.

How should the Backend and Frontend units handle API contract definition?

*Examples*:
- **Option A**: Backend fully designs API; Frontend consumes what's provided
- **Option B**: API contract designed collaboratively; both teams review before coding
- **Option C**: Contract-first approach (OpenAPI schema defined first; Backend and Frontend code to schema)
- **Option D**: Informal agreement; API evolves as teams code

[Answer]: A

---

**Q7: WebSocket Event Schema**

The application uses WebSocket for real-time score broadcasts and camera preview streams. These events flow from Backend → Frontend.

Should the Backend and Frontend align on WebSocket event schemas before coding?

*Examples*:
- **Option A**: Backend defines event schema; Frontend adapts
- **Option B**: Schemas designed collaboratively before coding
- **Option C**: EventBus events automatically serialized to JSON; Frontend handles what Backend publishes
- **Option D**: Independent evolution; teams handle schema mismatches at runtime

[Answer]: A

---

**Q8: Shared Data Structures**

Certain data structures (Score, Archer, Session, Camera, etc.) appear in both Backend database and Frontend state.

How should shared types be handled between units?

*Examples*:
- **Option A**: Each unit defines its own models independently
- **Option B**: Shared TypeScript types exported from a common package
- **Option C**: Backend API response schemas define the contract; Frontend uses TypeScript auto-generation (from OpenAPI)
- **Option D**: Python Pydantic schemas as source of truth; Frontend generates types from Backend

[Answer]: A

---

### Category 4: Team Alignment & Ownership

**Q9: Team Structure**

From the execution plan:
- **Senior Backend Developer Agent** — Owns Backend unit
- **Senior Frontend Developer Agent** — Owns Frontend unit

Should there be:
- A single agent coordinating both units?
- Direct peer communication between agents?
- A formal API contract review gate between units?

[Answer]: Direct peer communication between agents

---

**Q10: Coordination Points**

At what milestones should Backend and Frontend agents sync to ensure integration?

*Examples*:
- **Option A**: Sync after API design (before coding)
- **Option B**: Sync after unit design complete (before code generation)
- **Option C**: Sync before each sprint/phase
- **Option D**: Continuous sync (independent agents, frequent check-ins)

[Answer]: B

---

### Category 5: Technical Considerations

**Q11: Deployment Model**

How should the system be deployed?

*Examples*:
- **Option A**: Single deployment (Backend + Frontend containers together via Docker Compose)
- **Option B**: Separate deployments (Backend containerized separately; Frontend served as static assets)
- **Option C**: Coupled (Frontend and Backend must deploy together)
- **Option D**: Independent (Backend and Frontend deployable independently)

[Answer]: D

---

**Q12: Database & Shared Resources**

Should Backend and Frontend units share:
- A single PostgreSQL database (Backend writes; Frontend reads via API)?
- A cache/session store (shared Redis)?
- A file storage system (shared `/storage/` directory)?

[Answer]: A single PostgreSQL database 

---

**Q13: Development & Testing Databases**

Should Backend and Frontend development environments:
- Share the same PostgreSQL instance for local development?
- Use separate test databases?
- Use database fixtures or seed data for integration testing?

[Answer]: Share the same PostgreSQL instance for local development

---

### Category 6: Code Organization (Greenfield)

**Q14: Backend Directory Structure**

How should the Backend unit be organized in the filesystem?

*Examples*:
- **Option A**: Flat structure `/backend` with all services, handlers, components in top-level modules
- **Option B**: Feature-based structure `/backend/features/{feature}/routes.py, services.py, etc.`
- **Option C**: Layer-based structure `/backend/{layer}` (handlers/, services/, repositories/, models/)
- **Option D**: Hybrid (layers at top level, then features within each layer)

[Answer]: B

---

**Q15: Frontend Directory Structure**

How should the Frontend unit be organized in the filesystem?

*Examples*:
- **Option A**: Flat structure `/frontend/src` with pages/, components/, hooks/ at top level
- **Option B**: Feature-based structure `/frontend/src/features/{feature}` with routes, components, hooks per feature
- **Option C**: Modular structure `/frontend/src/{domain}` organized by business domain
- **Option D**: Monorepo structure `/frontend/{package}` with shared UI components, state, hooks in separate packages

[Answer]: B

---

**Q16: Shared Code & Utilities**

Should Backend and Frontend units have:
- Shared utilities for domain logic (e.g., scoring calculation)?
- Shared type definitions (TypeScript types for API contracts)?
- Shared validation logic (Pydantic on backend, Zod on frontend)?

How should shared code be organized?

*Examples*:
- **Option A**: Separate shared directory (`/shared/`) with common utilities
- **Option B**: Each unit owns its logic independently; no shared code
- **Option C**: Monorepo with `/packages/shared/` for npm packages and `/libs/shared/` for Python
- **Option D**: Shared logic lives in Backend; Frontend imports via API

[Answer]: D

---

## Summary Table

| Category | Decision Point | Status |
|---|---|---|
| **Decomposition** | 2-unit (Backend + Frontend)? | Pending User Input |
| **Backend Subdivision** | Monolithic vs Modular vs Microservices | Pending User Input |
| **Frontend Subdivision** | Monolithic vs Feature Modules vs Monorepo | Pending User Input |
| **Story Grouping** | Hybrid stories: assign to one unit or split? | Pending User Input |
| **API Contract** | Backend-first, collaborative, or contract-first? | Pending User Input |
| **WebSocket Events** | Independent or collaborative schema design? | Pending User Input |
| **Shared Types** | Independent models, shared types, or auto-generated? | Pending User Input |
| **Team Structure** | Coordinator agent, peer communication, or formal gates? | Pending User Input |
| **Deployment** | Single vs separate vs independent deployments? | Pending User Input |
| **Code Organization** | Layer-based, feature-based, or monorepo? | Pending User Input |

---

## Next Steps

1. **Review** the questions above
2. **Provide answers** to ALL [Answer]: tags
3. **Submit** completed plan for analysis
4. **Clarify** any ambiguous answers via follow-up questions
5. **Approve** decomposition plan
6. **Proceed** to Part 2: Generation (create unit artifacts)

