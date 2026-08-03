# Architecture

This document is the authoritative description of repository-owned architecture invariants. Automated checks provide
specific evidence for them; they are not a proof of every runtime behavior. The coverage table below is the exact
boundary between machine evidence and human review.

Run `uv run poe verify` for complete local product verification. The pinned central CI Harness reruns it and adds the
repository-wide architecture, frontend-boundary, security, and supply-chain checks.

## Repository Invariants

### A1. Dependency Direction

Backend contexts use an inward dependency direction:

```text
interface      -> application -> domain
infrastructure -> application ports + domain
```

- `domain` contains business types and rules and has no framework or external-I/O dependency.
- `application` coordinates use cases and depends on domain types and ports, not concrete clients.
- `infrastructure` implements application ports and owns concrete persistence, network, and provider integrations.
- `interface` translates transport input and output and invokes application behavior.

Create only the layers a context needs. Empty scaffolding is not an architectural achievement.

### A2. Context Isolation

A context must not import another context's internal modules. The lean default is a consumer-owned application port:
an adapter under `app/integrations` may translate between contexts, and `app/bootstrap.py` wires it. Stable integration
messages may live under `app/contracts` only after ownership and compatibility are recorded in an ADR. Context code
still never imports another context directly. Shared code represents a stable cross-cutting concept, not a shortcut
around ownership.

### A3. External I/O Containment

Database drivers, HTTP clients, message brokers, file access, email, payment, search, and model-provider SDKs belong
behind an application port and are implemented in the context's `infrastructure` layer. A small context may put an
implementation directly in that layer; adapter/repository/gateway subdirectories are optional. Domain and application
modules use `PurePath` or owned value types rather than `pathlib.Path`, and remain testable without external resources.

### A4. Runtime Construction

- `create_app()` is the FastAPI application factory.
- Importing a module must not create settings with external effects, open files, connect to services, or start background work.
- Lifespan owns resource startup and shutdown.
- Health behavior remains available without requiring unrelated optional integrations.

### A5. Frontend Network Boundary

Vue components and stores do not call `fetch`, `axios`, `EventSource`, or `XMLHttpRequest` directly. Browser I/O lives under `src/frontend/src/api`, where transport behavior, generated types, streaming, and error translation can be verified consistently.

### A6. Contract Fidelity

- OpenAPI is the public HTTP contract.
- Generated frontend API types are derived artifacts and are not edited by hand.
- Contract changes update their acceptance or integration tests in the same change.
- Compatibility is preserved unless a human-approved change contract explicitly authorizes a break.

### A7. Configuration and Secrets

- Non-sensitive defaults may live in tracked configuration.
- Credentials and environment-specific secrets never enter source control, examples, logs, fixtures, or error responses.
- Input is validated at the system boundary.
- Internal exception details are not exposed as public API responses.

### A8. Reproducible Verification

- Dependency lockfiles and repository-owned generated contracts remain synchronized.
- Required CI actions and permissions follow the repository supply-chain policy.
- A gate evaluates repository artifacts, not whether a human or agent claimed to follow a process.

## Enforcement Coverage

| Invariant | Automated evidence | Still requires human review |
|---|---|---|
| A1–A2 | CI Harness AST import/layer checks | whether a proposed context split or integration contract is the right design |
| A3 | CI Harness client/stdlib import bans and `pathlib.Path` exclusion; local Ruff and unit tests | dynamic calls, indirect side effects, and whether each new port captures the right boundary |
| A4 | app-factory, lifespan, health, and dependency-injection integration tests | startup/shutdown correctness for every newly introduced resource |
| A5 | CI Harness TypeScript/Vue AST network-boundary checker across JS, TS, TSX, and SFC scripts | whether API behavior and error UX are product-correct |
| A6 | generated OpenAPI drift check, typed request/response usage, integration and acceptance tests | whether a contract break is intended and compatible; no base-vs-head policy is inferred |
| A7 | CI Harness Git-aware secret scan; local Ruff and validation/error-response tests | data classification, privacy, authorization, and residual security risk |
| A8 | CI Harness lockfile, package-manager, workflow pin/permission, and Dependabot checks; local generated-contract check | accepting a dependency or CI-policy change |

Do not upgrade a human-review item into a blocking heuristic unless it meets the low-false-positive requirements in
`CONTRIBUTING.md` and has both pass and fail tests.

## Reference Context

`src/app/contexts/tasks` is a complete, deliberately small reference slice:

```text
interface/api -> application/services -> application/ports <- infrastructure/repositories
                                      -> domain
```

`src/app/bootstrap.py` selects the concrete repository and builds the application container. The context demonstrates
the dependency direction; it does not require every future context to copy every directory. Add a layer only when the
feature has a real responsibility for it, and add a port only when an external effect or replaceable dependency exists.

On the frontend, pages consume typed functions from `src/frontend/src/api`; generated OpenAPI types remain below that
transport boundary. Feature-specific components and state should stay near the feature rather than accumulating in a
global `shared` directory.

## Human-Reviewed Design Decisions

The harness does not decide:

- where a new product capability belongs;
- whether a contract should intentionally break;
- which persistence, provider, or deployment trade-off is acceptable;
- whether a module should be split or two contexts should collaborate through a port or event;
- whether the residual risk of a security, privacy, or migration decision is acceptable.

These decisions require the human workflow in [CONTRIBUTING.md](CONTRIBUTING.md). Durable or difficult-to-reverse choices use [the ADR template](docs/adr/0000-template.md).

## Changing an Invariant

An architecture-invariant change is protected-risk work. It requires:

1. a human-confirmed change contract;
2. an ADR explaining the decision and alternatives;
3. updates to the implementation and deterministic verification;
4. maintainer review of both the invariant and its enforcement.

Do not retain obsolete prose checks after an invariant has executable verification. The checker and its pass/fail tests are the enforcement source; this document explains the stable boundary and rationale.
