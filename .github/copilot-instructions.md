# Global Development Standards

This repository follows a strict spec-driven workflow and secure development discipline.

## Workflow: Spec-Driven Development (SDD)

Every non-trivial feature or refactor follows four mandatory phases. Do NOT skip ahead.

1. Specify — Identify business requirements, user journeys, scope boundaries (what is explicitly out of scope), and verifiable acceptance criteria.
2. Plan — Produce a technical Design Doc (Markdown). Translate the spec into architectural decisions without writing final code yet.
3. Tasks — Break the plan into atomic, isolated, testable tasks (max 2–3 levels of depth).
4. Implement — Execute tasks in small increments, validating at checkpoints.

### Design Doc requirement

For every non-trivial task, generate a `.md` file before writing any implementation code and save it to `/docs/design-docs/` (or `/docs/adrs/` for architectural decisions, `/docs/rfcs/` for proposals). The document must contain:

- Summary & Motivation — what and why
- Objectives & Non-Goals — explicit scope boundaries
- Detailed Design & Task Decomposition — architecture + atomic task list
- Security & Privacy Considerations — data flow, secrets, attack vectors

After saving, ask: "Você aprova este plano de implementação para iniciarmos a Fase de Testes/Codificação?"

If the approach changes mid-implementation (spec drift), update the `.md` first, then continue coding.

### Test-First (Fail-First)

Before writing production code for any task:
1. Write automated tests derived from the spec (unit or contract tests).
2. Confirm the tests fail (proving the feature does not yet exist).
3. Only then write the implementation that makes them pass.

The spec and tests are the primary artifacts. Implementation code is a byproduct.

---

## Architecture Principles

### SOLID / SRP
- Every module, class, and function has exactly one reason to change.
- Isolate business logic from infrastructure concerns (UI, DB, external APIs).
- Avoid monolithic files — split by responsibility, not by convenience.

### C4 Model thinking
Before proposing or modifying a design, reason through:
- Context — how the system interacts with users and external entities
- Container — deployable units and how they communicate
- Component — logical blocks within a container (repositories, services, controllers) with explicitly defined interfaces

### API Design-First
If creating an API, define the contract (e.g., OpenAPI spec) first. Never break compatibility without explicit semantic versioning (MAJOR.MINOR.PATCH).

### Dependency discipline
Do not introduce new third-party library dependencies without explicit justification in the architectural plan. Prefer standard library or already-approved dependencies.

---

## Security Standards (Secure-by-Design)

Aligned with NIST SP 800-218A (Secure Software Development Framework).

### Input validation
Never trust data from users or external systems. Validate type, length, and format at every system boundary. Never interpolate untrusted input directly into queries, commands, or prompts.

### CWE mitigations (mandatory)
| CWE | Vulnerability | Control |
|-----|--------------|---------|
| CWE-89 | SQL Injection | Strict parameterized queries only — no string concatenation |
| CWE-79 | XSS | Sanitize and encode all output sent to clients |
| CWE-522 | Weak credential storage | Hash with strong algorithm + salt (bcrypt/argon2) |

### Secrets management
Never hardcode API keys, tokens, passwords, or sensitive URLs in source code. Always use environment variables, Vault services, or a secrets manager.

### Minimum privilege
Every component, service, and user role must have only the permissions strictly required for its function. Authenticate and authorize on every critical route/method.

### Threat annotation
Add an inline comment to every security control explaining which specific threat vector it mitigates.

---

## Global Invariants

**Never:**
- Jump directly to code generation upon receiving a requirement — always go through the SDD phases first
- Write implementation code before saving the design doc to `/docs` and receiving explicit approval
- Write production code before writing the failing test that validates it
- Expose or generate code containing hardcoded secrets, tokens, or credentials
- Disable SSL/TLS certificate validation
- Log PII (personally identifiable information) in plaintext
- Introduce strong coupling or new third-party dependencies without an explicit architectural justification

**Always:**
- Confirm the spec and proposed tests with the user before proceeding to implementation
- Annotate security controls with the threat vector they mitigate
- Define explicit interfaces/contracts between components before implementing internal logic
- Update the design doc before changing approach mid-implementation
- End planning responses by asking for explicit approval to proceed to coding
