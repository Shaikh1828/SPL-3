# User Stories — Generation Plan

**Project**: Archery Scoring System  
**Date**: 2026-05-23  
**Phase**: INCEPTION — User Stories (Part 1: Planning)  

---

## PART 1: STORY GENERATION PLAN

This document outlines the comprehensive plan for generating user stories and personas. Please answer all questions below to guide story creation.

---

## Step 1: Story Format & Granularity

### Question 1: Story Format Preference
Which user story format is preferred for this project?

A) **Standard Gherkin Format**
```gherkin
As a [role]
I want to [action]
So that [benefit]

Given [context]
When [action]
Then [expected result]
```

B) **Narrative Format with Acceptance Criteria**
```
Story: [Title]
As a [role], I want to [action] so that [benefit]
Acceptance Criteria:
  - Criterion 1
  - Criterion 2
  - Criterion 3
```

C) **Lean Format (minimal)**
```
[Role] [Action] [Benefit]
Acceptance: [Quick criteria list]
```

D) **Other** — Please describe

[Answer]: A

---

### Question 2: Story Granularity (Story Size)
What size stories are preferred?

A) **Epic-Level** — Large stories representing major workflows (e.g., "Complete a Tournament Round") that would be broken into smaller stories
B) **Feature-Level** — Mid-size stories representing major features (e.g., "Score a Single End") that fit within 1-2 day sprints
C) **Task-Level** — Small, atomic stories (e.g., "Override a Single Arrow Score") that fit within 2-4 hour work items
D) **Mixed Granularity** — Use different sizes as appropriate for different story types
E) **Other** — Please describe

[Answer]: B

---

### Question 3: Acceptance Criteria Detail Level
How detailed should acceptance criteria be?

A) **High Detail** — 5-8 specific criteria per story with edge cases and error scenarios defined
B) **Standard Detail** — 3-4 main criteria per story covering happy path and common error cases
C) **Minimal Detail** — 1-2 main criteria per story with general guidance
D) **Scenario-Based** — Use scenario tables (Given/When/Then) for complex criteria
E) **Other** — Please describe

[Answer]: B

---

## Step 2: Story Breakdown Approach

### Question 4: Primary Story Organization Method
How should stories be grouped and organized?

A) **User Journey-Based** — Stories follow a user's workflow from start to finish (e.g., Session Initialization → Scoring → Review Results → Close Session)
B) **Feature-Based** — Stories organized by system features (Cameras, Scoring, Reports, Users, Sessions)
C) **Persona-Based** — Stories grouped by user type (Admin Stories, Scorer Stories, Archer Stories, System Admin Stories)
D) **Domain-Based** — Stories organized around business domains (Tournament Management, Scoring Operations, Reporting, Access Control)
E) **Epic-Based** — Hierarchical organization with Epic stories broken into sub-stories
F) **Hybrid** — Combination (please specify in [Answer] which two to combine)

[Answer]: B

---

### Question 5: Story Cross-Mapping
Should stories be created to map across multiple organization dimensions?

A) **Single Organization Only** — Create one master list using the chosen method from Q4, no cross-mapping
B) **Cross-Reference Matrix** — Create primary organization method, plus index showing how stories map to other dimensions (persona → feature)
C) **Fully Cross-Mapped** — Create separate story lists for each dimension, with explicit relationships between them
D) **Reference Map Only** — Create stories using primary method, include traceability matrix to requirements

[Answer]: B

---

## Step 3: User Personas

### Question 6: Persona Detail Level
How detailed should user personas be?

A) **Comprehensive** — Full personas with background, motivations, technical proficiency, goals, pain points, daily workflows
B) **Standard** — Persona name, role, key goals, main pain points, typical workflows
C) **Minimal** — Persona name, role, brief description of key characteristics
D) **Other** — Please describe

[Answer]: B

---

### Question 7: Secondary Personas
Beyond the 4 primary user roles (Admin, Tournament Admin, Scorer, Archer), should secondary personas be created?

A) **Primary Roles Only** — Create 4 personas matching the system roles exactly
B) **Include Variants** — Create personas with different characteristics within each role (e.g., "tech-savvy Scorer" vs "technophobe Scorer")
C) **Include System Admin** — Create separate persona for IT/system administrator (beyond SYSTEM_ADMIN role)
D) **Include Observers** — Create personas for spectators, commentators, or live result viewers (future feature personas)
E) **Minimal Secondary** — Just mention variants, don't create separate personas

[Answer]: A

---

## Step 4: Business Process & Acceptance Criteria

### Question 8: Session Workflow Granularity
Should session workflows be broken into one detailed story or multiple focused stories?

A) **Single Epic Story** — One large story: "Complete a Scoring Session" with sub-steps in acceptance criteria
B) **Phase-Based Stories** — Separate stories for: Setup Session → Initialize → Score Ends → Close Session
C) **Action-Based Stories** — One story per operation: Start Session, Assign Camera, Score End, Confirm Score, Retake Score, End Session
D) **User-Focused Stories** — Different stories from each persona's perspective: Admin initializes, Scorer triggers, Archer views results
E) **Hybrid** — Combination of approaches, please describe

[Answer]: C

---

### Question 9: Concurrency Scenarios
Should stories include edge cases around concurrent operations?

A) **Separate Stories** — Create dedicated stories for concurrency scenarios (e.g., "Multiple Scorers on Different Cameras")
B) **Acceptance Criteria** — Include concurrency scenarios as "edge case" acceptance criteria in main stories
C) **Assume Sequential** — Don't explicitly cover concurrency; assume it's handled by backend architecture
D) **Test Cases Only** — Document concurrency in test cases, not in user stories
E) **Other** — Please describe

[Answer]: B

---

### Question 10: Score Override Workflow
Score overrides are critical audit trail operations. How detailed should this be in stories?

A) **Detailed Story Suite** — Multiple stories: "Detect Low Confidence", "Override Single Arrow", "Override Full End", "View Override Log"
B) **Single Story** — One story: "Override Computed Score" with comprehensive acceptance criteria and audit trail requirements
C) **Acceptance Criteria Only** — Include override as acceptance criteria in main scoring story
D) **Requirement-Only** — Handle as non-functional requirement, not in user stories

[Answer]: A

---

## Step 5: Permission & Role-Based Access

### Question 11: Permission Stories
Should role-based access control be defined as dedicated user stories?

A) **Dedicated Permission Stories** — Create stories like "Archer Cannot Access Tournament Admin Features", "Scorer Can Override but Cannot Delete Tournaments"
B) **Embedded in Feature Stories** — Include permission checks as acceptance criteria in each feature story (e.g., "Only Admin can see user management")
C) **Separate Permission Document** — Create a permission matrix/table instead of user stories
D) **Both Stories and Matrix** — Create both dedicated permission stories AND a reference matrix
E) **Don't Explicitly Cover** — Permissions are architectural decisions, handle in API design not stories

[Answer]: A

---

## Step 6: Error & Exception Scenarios

### Question 12: Error Handling Coverage
How should error scenarios be covered in stories?

A) **Separate Error Stories** — Create dedicated stories for error paths: "Camera Connection Fails", "Image Processing Fails", "Database Error"
B) **Acceptance Criteria** — Include error scenarios in "happy path" story acceptance criteria (happy path + failure cases)
C) **Unhappy Path Stories** — Create alternate stories for each major story covering the failure case
D) **Assumption: Happy Path Only** — Stories describe ideal scenario; error handling is implementation detail
E) **Other** — Please describe

[Answer]: B

---

## Step 7: Live Data & Real-Time Features

### Question 13: WebSocket & Live Preview Stories
How should real-time features (live camera preview, live score updates) be covered?

A) **Dedicated Real-Time Stories** — Separate stories: "View Live Camera Preview", "See Live Score Updates", "Receive Real-Time Status"
B) **Embedded in UI Stories** — Include live preview as part of main scoring page story
C) **Technical Feature Stories** — Create stories from system perspective: "WebSocket Server Handles Connections", "Deliver MJPEG Frames"
D) **Assumption: Browser-Side Only** — Focus stories on user experience (what they see), not WebSocket mechanics
E) **Other** — Please describe

[Answer]: C

---

### Question 14: Offline/Failure Recovery
Should stories cover offline or degraded-mode operation?

A) **Explicit Recovery Stories** — Create stories: "Recover from Camera Disconnect", "Retake Previous Score", "Resume after Network Outage"
B) **Acceptance Criteria Only** — Include as acceptance criteria: "System gracefully handles camera disconnect"
C) **Not in Scope** — Focus on happy path; error recovery is architectural concern
D) **Mention but Don't Story** — Acknowledge in personas/context but don't create dedicated stories

[Answer]: B

---

## Step 8: Reporting & Analytics

### Question 15: Report Generation Stories
How should report-related stories be structured?

A) **Separate Report Stories** — One story per report type: "Generate Session Report", "Generate PDF", "Generate CSV", "Generate Rankings"
B) **Single Report Epic** — One large story: "Access Reports" with different report types as acceptance criteria
C) **User-Centric Stories** — Stories from each user's perspective: "Admin Views Tournament Rankings", "Archer Downloads Own Report"
D) **Feature Stories Only** — Handle reports as feature detail, not separate stories
E) **Other** — Please describe

[Answer]: B

---

## Step 9: Non-Functional & Quality Attributes

### Question 16: Performance & Scalability in Stories
Should performance/scalability be covered in user stories?

A) **Dedicated Quality Stories** — Create stories: "System Scores within 1 Second", "Supports 4+ Concurrent Cameras", "Handles 100+ Session Records"
B) **Acceptance Criteria** — Include performance targets in relevant feature stories (e.g., "Scoring completes < 1s")
C) **Separate Document** — Handle as NFR specifications, not in stories
D) **Quality Attributes Checklist** — Create checklist of performance/reliability attributes to verify post-implementation

[Answer]: B

---

### Question 17: Security & Compliance in Stories
Should security be covered in user stories?

A) **Dedicated Security Stories** — "User Logs In Securely", "Data is Encrypted", "Override is Audited"
B) **Acceptance Criteria** — Include security as criteria in relevant stories
C) **Separate Security Policy** — Handle as security requirements, not stories
D) **Role-Based Security Stories** — Create stories for each role: "Admin Can Manage Users", "Archer Can Only View Own Data"
E) **Combination** — Mix of dedicated security stories + embedded criteria

[Answer]: D

---

## Step 10: Story Prioritization

### Question 18: Should Stories Include Priority Levels?
Should stories be prioritized (MoSCoW, 1-5 scale, etc.)?

A) **MoSCoW Method** — Must Have, Should Have, Could Have, Won't Have
B) **Priority Scale** — 1-5 or 1-10 priority ranking
C) **Phases** — Assign stories to Phase 1 (MVP), Phase 2 (enhance), Phase 3 (future)
D) **No Prioritization** — Create comprehensive list without priority; let team decide during sprint planning
E) **Other** — Please describe

[Answer]: C

---

### Question 19: MVP vs Full Feature Scope
Given you selected "Complete Implementation" (not MVP-first), should stories distinguish between:

A) **Phase 1 Complete Set** — All stories assume they'll be implemented in this release; no phasing
B) **Marked Phases** — Stories marked as Phase 1 (essential), Phase 2 (desirable), Future (nice-to-have)
C) **Core vs. Advanced** — Mark stories as "core feature" vs "advanced/optional"
D) **No Distinction** — All stories are equal priority; implementation order TBD

[Answer]: B

---

## Step 11: Dependencies & Workflows

### Question 20: Story Dependencies
Should stories document dependencies on other stories?

A) **Explicit Dependencies** — Each story lists blocking stories: "This story requires User Authentication story to be complete"
B) **Implicit Flow** — Stories are organized in logical order (dependency visible from reading order)
C) **Dependency Matrix** — Create separate matrix showing story dependencies
D) **No Dependencies** — Each story is independent; dependencies handled during sprint planning

[Answer]: A

---

## Summary — Planning Checklist

Once you complete your answers, I will:

- [ ] Analyze all answers for clarity and completeness
- [ ] Create user personas based on your specifications (4 primary roles + any secondary personas)
- [ ] Generate 15-25 user stories organized by your chosen method
- [ ] Map stories to the detailed requirements document
- [ ] Create acceptance criteria following your specified detail level
- [ ] Include error scenarios and edge cases as appropriate
- [ ] Generate story prioritization if requested
- [ ] Create traceability matrix linking stories to requirements
- [ ] Present complete stories + personas for your approval

---

## Next Steps

**Please complete all 20 questions above** (Questions 1-20). For each question:
- Read the options carefully
- Select the option that best matches your preference
- For "Other" options, describe your alternative approach in detail
- Answer as completely as possible

**Once all questions are answered**, reply with **"Story Planning Complete"** and I will:
1. Review your answers for ambiguities
2. Ask follow-up questions if needed
3. Create comprehensive user stories and personas
4. Present for your approval

**Ready to answer? Let's define your user stories!** 📖
