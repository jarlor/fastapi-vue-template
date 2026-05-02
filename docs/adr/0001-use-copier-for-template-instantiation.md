# ADR 0001: Use Copier for Template Instantiation

## Status

Accepted

## Context

This repository is a production-grade project template for Vibe Coding and Harness Engineering. A generated project should be reproducible, updateable, and verifiable by repository-owned harness checks.

The current `scripts/init.sh` flow performs broad text replacement of `app_name` and then repairs known false replacements. That approach is fragile because:

- placeholder replacement can affect semantic field names and examples
- new files can accidentally opt into replacement
- generated projects do not retain structured template answers
- updating an existing generated project from a newer template is not modeled

## Decision

Use Copier as the template engine for future project instantiation and updates.

Copier is selected because it supports:

- declarative template questions in `copier.yml`
- generated-project answer files
- updating existing generated projects from newer template revisions
- Jinja templating for file contents and paths
- a Python-native toolchain that fits the existing backend stack

Cookiecutter remains a valid one-shot scaffolding tool, but it does not make template updates a first-class workflow in the same way. This template needs updateability because the harness itself will evolve.

## Consequences

- `scripts/init.sh` will be deprecated rather than extended.
- New template variables must be declared in `copier.yml`.
- The repository harness must include a generated-project smoke test before `scripts/init.sh` is removed.
- Documentation must teach `copier copy` for new projects and `copier update` for existing generated projects.
- Broad `app_name` replacement should be removed after Copier covers package names, project names, frontend metadata, and ports.

## Migration Plan

1. Add `copier.yml` and a minimal generated-project smoke test while keeping `scripts/init.sh`.
2. Move package/module placeholders to Copier variables.
3. Replace broad text replacement in `scripts/init.sh` with a compatibility message or thin Copier wrapper.
4. Add a template harness check that generates a temporary project and runs its core checks.
5. Remove `scripts/init.sh` once the Copier path is fully documented and tested.
