# Context Contracts

## What Is a Context Contract?

A context contract defines the public interface of a bounded context -- what it exposes to the rest of the system and what it depends on. Each context is an isolated domain module that owns its data, defines its events, and communicates with other contexts only through well-defined boundaries.

Context contracts prevent tight coupling. Without them, modules accumulate hidden dependencies that make changes risky and testing difficult. A contract makes these boundaries explicit and enforceable.

## Contract Template

Every bounded context must define a contract using this template. Keep it in `docs/context-contracts.md` and update it whenever the public interface changes.

```markdown
### {Context Name}

**Location:** `src/app_name/contexts/{context_name}/`

#### Public Interfaces

Functions and classes that other contexts may import or call via dependency injection.

| Interface | Type | Description |
|-----------|------|-------------|
| `get_user_by_id(user_id)` | async function | Returns user or None |
| `UserPort` | Protocol | Abstract interface for user operations |

#### Owned Collections

MongoDB collections that only this context may read from or write to.

| Collection | Description |
|------------|-------------|
| `users` | User accounts and profiles |

#### Produced Events

Events this context emits for other contexts to consume.

| Event | Payload | When |
|-------|---------|------|
| `user.created` | `{user_id, email}` | After successful registration |

#### Consumed Events

Events this context listens to from other contexts.

| Event | Source Context | Handler |
|-------|---------------|---------|
| `subscription.activated` | billing | `handle_subscription_activated` |

#### Port Dependencies

External services this context requires, defined as Protocol/ABC interfaces.

| Port | Description |
|------|-------------|
| `EmailPort` | Send transactional emails |
```

## Example: Auth Context

### Auth

**Location:** `src/app_name/contexts/auth/`

#### Public Interfaces

| Interface | Type | Description |
|-----------|------|-------------|
| `authenticate(token)` | async function | Validates bearer token, returns user identity |
| `create_token(user_id)` | function | Issues a new access token |
| `AuthPort` | Protocol | Abstract auth operations for dependency injection |

#### Owned Collections

| Collection | Description |
|------------|-------------|
| `auth_tokens` | Active access and refresh tokens |
| `auth_sessions` | Server-side session records |

#### Produced Events

| Event | Payload | When |
|-------|---------|------|
| `auth.login` | `{user_id, timestamp}` | After successful authentication |
| `auth.logout` | `{user_id, timestamp}` | After explicit logout |
| `auth.token_refreshed` | `{user_id, timestamp}` | After token refresh |

#### Consumed Events

| Event | Source Context | Handler |
|-------|---------------|---------|
| `user.created` | user | `handle_user_created` (initialize auth record) |
| `user.deleted` | user | `handle_user_deleted` (revoke all tokens) |

#### Port Dependencies

| Port | Description |
|------|-------------|
| `PasswordHasherPort` | Hash and verify passwords |
| `TokenStorePort` | Persist and retrieve tokens |

## Rules

1. **Contexts communicate only through events and ports.** No context may directly import internal modules from another context. Use the public interfaces listed in the contract.

2. **No direct cross-context imports.** If context A needs functionality from context B, it depends on B's Port (Protocol/ABC) and receives the implementation via dependency injection.

3. **Bulk update semantics stay inside gateways.** If a context needs to update multiple records in another context's collection, it emits an event. The owning context handles the bulk operation internally. Callers never perform batch writes against collections they do not own.

4. **Contract changes require documentation updates.** Any change to a public interface, owned collection, produced event, or consumed event must be reflected in this document before the PR is merged.

5. **One owner per collection.** Each MongoDB collection is owned by exactly one context. Other contexts access that data through the owning context's public interfaces or events.
