# Extension Configuration & Compliance Notes

**Project**: Archery Scoring System  
**Date**: 2026-05-23  
**Phase**: INCEPTION — Requirements Analysis

---

## Extension Configuration

| Extension | Enabled | Decision | Rules |
|---|---|---|---|
| **Security Baseline** | ✅ YES | User selected Option A (enforce all rules) | All 11 security rules (SECURITY-01 through SECURITY-11) |
| **Property-Based Testing** | ✅ YES | User selected Option A (enforce all rules) | All 9 PBT rules (PBT-01 through PBT-09) |

---

## Security Extension — Enforcement Summary

**Status**: ENABLED (all 11 rules are MANDATORY blocking constraints)

### Applicable Rules for This Project

| Rule ID | Rule Name | Applicable? | Implementation Plan |
|---|---|---|---|
| **SECURITY-01** | Encryption at Rest/Transit | ✅ YES | PostgreSQL TLS, native encryption at rest, HTTPS via Nginx reverse proxy |
| **SECURITY-02** | Access Logging on Intermediaries | ✅ YES | Nginx access logs, FastAPI request logging with correlation IDs |
| **SECURITY-03** | Application-Level Logging | ✅ YES | structlog framework, centralized logs/ directory, no secrets in logs |
| **SECURITY-04** | HTTP Security Headers | ✅ YES | CSP, HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy on all responses |
| **SECURITY-05** | Input Validation on All API Parameters | ✅ YES | Pydantic models on all endpoints, max-length constraints, parameterized SQL queries (ORM) |
| **SECURITY-06** | Least-Privilege Access Policies | ✅ YES | Fine-grained role-based permissions (4 roles), no wildcard actions |
| **SECURITY-07** | Restrictive Network Configuration | ✅ YES | Deny-by-default firewall rules, public access only on 80/443 via Nginx |
| **SECURITY-08** | Application-Level Access Control | ✅ YES | Auth middleware on all routes, object-level IDOR checks, CORS restricted to trusted origins |
| **SECURITY-09** | Security Hardening & Misconfiguration Prevention | ✅ YES | No default credentials, minimal base images, error responses don't leak internals |
| **SECURITY-10** | Software Supply Chain Security | ✅ YES | Poetry lock file, bandit dependency scanning, no `latest` tags in Docker, SBOM for prod |
| **SECURITY-11** | Secure Design Principles | ✅ YES | Auth/AuthZ isolated in middleware, separation of concerns enforced |

### Enforcement Points
- **Functional Design Phase**: Verify all security requirements documented
- **NFR Requirements Phase**: Confirm security controls for each component
- **Infrastructure Design Phase**: Validate network and storage encryption
- **Code Generation Phase**: Ensure all security rules implemented in code
- **Build & Test Phase**: Run security scanning tools (bandit, OWASP checks)

**Blocking Finding Behavior**: If ANY security rule is not met during code generation or testing, the stage will **NOT proceed to next phase** until resolved.

---

## Property-Based Testing Extension — Enforcement Summary

**Status**: ENABLED (all 9 rules are MANDATORY blocking constraints)

### Applicable Rules for This Project

| Rule ID | Rule Name | Applicable? | Implementation Plan |
|---|---|---|---|
| **PBT-01** | Property Identification During Design | ✅ YES | Functional design identifies scoring algorithm properties (invariant, idempotence) |
| **PBT-02** | Round-Trip Properties | ⚠️ PARTIAL | JSON serialization (session data, user data), image metadata round-trips |
| **PBT-03** | Invariant Properties | ✅ YES | Scoring engine invariants: zone count preserved, score range [0-10], X count accurate |
| **PBT-04** | Idempotency Properties | ✅ YES | API endpoints (PUT, DELETE), score override operations, session state management |
| **PBT-05** | Oracle and Model-Based Testing | ⚠️ CONDITIONAL | Reference scoring algorithm (simple distance-based) vs optimized version |
| **PBT-06** | Stateful Property Testing | ✅ YES | Session state machine, score accumulation, camera status transitions |
| **PBT-07** | Generator Quality | ✅ YES | Custom generators for Score, Session, User, Image domain objects |
| **PBT-08** | Shrinking and Reproducibility | ✅ YES | CI pipeline includes random seed logging, reproducible failures |
| **PBT-09** | Framework Selection | ✅ YES | Hypothesis (Python) for backend PBT, ts-check-types (TypeScript) for frontend |

### Priority PBT Components
1. **Scoring Engine** (highest priority) — Invariant and idempotency testing
2. **Session State Management** — Stateful property testing
3. **API Input Validation** — Oracle testing against constraint models
4. **Image Serialization** — Round-trip property testing

### Enforcement Points
- **Functional Design Phase**: Identify properties for scoring engine, session state, serialization
- **Code Generation Phase**: Generate PBT tests alongside unit tests
- **Build & Test Phase**: Verify all PBT tests pass, shrinking enabled, seed logging in CI

**Blocking Finding Behavior**: If ANY PBT rule is not met during testing, the stage will **NOT proceed to next phase** until resolved.

---

## Risk Assessment for Extensions

| Extension | Risk | Mitigation |
|---|---|---|
| **Security** | Increases initial development time by ~10-15% for compliance validation | Clear security requirements upfront; use established patterns (Nginx reverse proxy, ORM for SQL injection prevention) |
| **PBT** | Learning curve for team unfamiliar with property-based testing | Use well-documented frameworks (Hypothesis), start with scoring engine (high-value target) |
| **Combined Compliance** | Must track both extensions through all phases | Create compliance checklist in build-and-test phase, automate security scanning |

---

## Next Actions

1. ✅ Extensions enabled and documented
2. ✅ Comprehensive requirements document created
3. ⏳ **Next**: User Stories evaluation (needed for 4-role RBAC, multi-step workflows, acceptance criteria)
4. ⏳ **Then**: Workflow Planning (unit decomposition, team assignments)
5. ⏳ **Then**: Code Generation (backend API, frontend UI, test suites)
