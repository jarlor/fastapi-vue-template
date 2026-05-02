## Summary

- 

## Harness Evidence

- [ ] `uv run poe harness`
- [ ] `uv run poe agent-start` (agent-driven changes only, before first edit)
- [ ] `uv run poe template-smoke` (required when template generation, Copier config, generated-project files, or harness behavior changes)

Notes:

## Contract / Interface Impact

- [ ] No public API, context contract, config, or deployment behavior changed.
- [ ] Public API changed and docs/tests were updated.
- [ ] Backend boundaries or runtime contracts changed and relevant docs/tests/harness were updated.
- [ ] Config or secret requirements changed and examples/docs were updated.
- [ ] Deployment or CI behavior changed and docs were updated.

## Security Review

- [ ] No new secrets or credentials were added.
- [ ] No new authentication or authorization behavior was added.
- [ ] Error responses do not expose internal details.
- [ ] User input is validated at the boundary.

## Follow-ups

- 
