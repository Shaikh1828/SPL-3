# Backend Unit — NFR Requirements Clarification (Follow-ups)

**Date**: 2026-05-25  
**Status**: PENDING USER CLARIFICATION

---

## Critical Ambiguities Identified

All 26 questions were answered, but 5 areas show contradictions or conflicts with prior design decisions. Clarification needed before proceeding to artifact generation.

---

## Follow-up #1: Scoring Latency (Q1 vs. Functional Design)

**Conflict**: 
- **Q1 Answer**: C (Best-effort latency target, no hard deadline)
- **Functional Design**: Explicitly specifies < 1 second end-to-end as a key performance target (200+300+200+150+50ms breakdown)
- **Requirements**: States "< 1s scoring latency" as performance goal

**Question**: 
Is the < 1 second scoring latency a:
- **A)** Hard requirement (must enforce, fail if exceeds, critical for UX)
- **B)** Best-effort goal (optimize for < 1s, but acceptable if occasional results exceed)
- **C)** Infrastructure design consideration (implement caching/optimizations, monitor, but not a blocking requirement)

[Answer]: B

---

## Follow-up #2: WebSocket Event Latency (Q5 vs. Requirements)

**Conflict**:
- **Q5 Answer**: E (No specific target, fire-and-forget)
- **Requirements**: Specification mentioned < 100ms target for real-time event delivery
- **Real-Time Scoring**: Users watching live updates expect responsive UI

**Question**:
WebSocket event delivery latency should be:
- **A)** < 100ms (requirement-mandated, critical for real-time UX)
- **B)** < 500ms (soft real-time, acceptable)
- **C)** No specific target (acceptable to be slower, depends on network)

[Answer]: B

---

## Follow-up #3: Concurrent Camera Scoring (Q7 vs. Q6)

**Conflict**:
- **Q6 Answer**: B (Design for 4-6 users typical, scale to 10+)
- **Q7 Answer**: E (Sequential scoring, not a concern for concurrent cameras)
- **Logic Issue**: If 4-6 users are concurrent, some must be triggering scoring from different cameras simultaneously. How can this be sequential?

**Clarification Question**:
How are concurrent users (Q6: 4-6 concurrent) managed when triggering scoring?
- **A)** Each user triggers their own camera/lane scoring independently → requires concurrent camera handling (contradicts Q7 answer)
- **B)** Only one user can trigger scoring at a time (queue/lock) → sequential, single camera scoring (matches Q7 answer, but conflicts with Q6 scaling)
- **C)** Multiple cameras score in parallel via ThreadPool, but from single user's control (explains Q7 sequential user actions, but Q6 is for operator concurrency)

Please clarify the actual workflow:

[Answer]: C

---

## Follow-up #4: Security Baseline Enforcement (Q10 vs. Mandatory Rules)

**Conflict**:
- **Q10 Answer**: C (Core security rules mandatory, others best-effort)
- **Project Requirements** (copilot-instructions.md): States that **ALL 11 Security Baseline rules are MANDATORY** - non-compliance is a blocking finding
- **Similar Mandatory**: 9 Property-Based Testing rules also mandatory

**Clarification Question**:
Understanding the constraint that ALL 11 Security Baseline rules are mandatory:
- **A)** Proceed with all 11 rules mandatory (Q10 answer was misunderstanding, override to A)
- **B)** Accept some rules as best-effort, document exceptions (but this blocks project requirements)
- **C)** Core rules (e.g., encryption, auth) are hard blockers, others are mandatory but can have phased implementation

[Answer]: A

---

## Follow-up #5: Scaling Architecture (Q16 vs. Q23)

**Conflict**:
- **Q16 Answer**: D (Auto-scale resources under overload)
- **Q23 Answer**: A (Single server, no load balancing)
- **Contradiction**: How can a single server auto-scale? Auto-scaling implies multiple server instances.

**Clarification Question**:
Should the deployment architecture support auto-scaling?
- **A)** Single server, no auto-scaling (Q23 answer, keep simple)
- **B)** Single server initially, but designed for multi-server deployment later (prepare for scaling)
- **C)** Multiple servers behind load balancer with auto-scaling (Q16 answer, higher complexity)
- **D)** Start single server, transition to auto-scaling if load becomes issue (phased approach)

[Answer]: B

---

## Summary of Follow-ups

| # | Question | Conflict | Resolution |
|---|---|---|---|
| 1 | Scoring Latency | Best-effort vs < 1s spec | Define strictness of 1s target |
| 2 | WebSocket Latency | No target vs < 100ms spec | Define real-time expectations |
| 3 | Concurrent Cameras | Sequential (Q7) vs Concurrent users (Q6) | Clarify scoring workflow parallelism |
| 4 | Security Baseline | Core only vs All 11 mandatory | Enforce mandatory requirement |
| 5 | Scaling | Auto-scale vs Single server | Clarify deployment scaling strategy |

---

## Next Steps

1. **Please provide answers to all 5 follow-up clarifications above**
2. Once all are answered, system will validate for remaining ambiguities
3. Generate final NFR Requirements artifacts (nfr-requirements.md, tech-stack-decisions.md)
4. Present for approval with standard 2-option format

