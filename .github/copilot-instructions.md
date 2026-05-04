# Copilot Instructions

## Scope

These instructions apply to the whole workspace.

## Language

- Respond in the same language as the user.

## Default Tone

- Default to caveman full: terse, direct, and compact.
- Keep answers short unless more detail is necessary.

## Mandatory Orchestration

- Start with task classification (frontend, backend, architecture, or general).
- Use the specialists in `.github/agents/` for domain execution:
  - `Orchestrator`
  - `Frontend`
  - `Backend`
  - `Architecture`
- Any request that may modify code MUST be routed through `Orchestrator` first.
- Specialists (`Frontend`, `Backend`, `Architecture`) MUST NOT start implementation directly from first contact.

## Specs-First Workflow (required for code changes)

For any feature, bug fix with code edits, or refactor, follow this sequence before implementation:

1. `/speckit.constitution` (when principles are missing/outdated)
2. `/speckit.specify` — creates or updates `spec.md`
3. `/speckit.clarify` (optional, when the spec still has ambiguities)
4. `/speckit.plan` — creates `plan.md`
5. `/speckit.tasks` — creates `tasks.md`
6. implement from generated tasks (`/speckit.implement` or equivalent)

### Hard Gate (Mandatory)

- No code edits are allowed before the full spec pipeline has run for the intervention.
- Minimum required artifacts before coding: `spec.md`, `plan.md`, and `tasks.md`.
- For any code intervention, the expected path is:
  `Orchestrator` → `/speckit.specify` → `/speckit.plan` → `/speckit.tasks` → implementation.
- If a request arrives directly to a specialist with no spec context, the specialist must stop and redirect to `Orchestrator`.

For read-only questions or explanations with no code changes, answer directly.

## Project Boundaries

Before any implementation, agents must discover the project structure by reading config files (`package.json`, `tsconfig.json`, `go.mod`, `requirements.txt`, etc.) and directory layout. Do not assume tech stack or directory names.

## Engineering Rules

- Identify and respect existing API boundaries (REST, GraphQL, gRPC, etc.) from project config.
- Keep strict typing; avoid `any`.
- Keep changes small, testable, and aligned with existing structure.
- Preserve existing lint/format rules; avoid unrelated refactors.

## Quality Gates Before Finishing

- Validate edits for lint/type errors.
- Ensure i18n strings are updated in both `Front/messages/en.json` and `Front/messages/es.json` when adding user-facing text.
- Ensure task status/progress is updated when working from Spec Kit artifacts.

## Sources of Truth

- Agent definitions: `.github/agents/`
- Spec Kit prompts: `.github/prompts/`
- Legacy/extended guidance: `AGENTS.md`, `CLAUDE.md`, `.claude/skills/`
