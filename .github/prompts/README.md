# Spec Kit Prompts for Copilot

This folder exposes Spec Kit workflows as Copilot slash prompts.

## Available Prompts

- `/speckit.constitution`
- `/speckit.specify`
- `/speckit.clarify`
- `/speckit.plan`
- `/speckit.tasks`
- `/speckit.analyze`
- `/speckit.checklist`
- `/speckit.implement`
- `/speckit.taskstoissues`

## Compatibility Strategy

Each `.prompt.md` is a thin Copilot shim that routes to the corresponding
Spec Kit agent under `.github/agents/`. Claude-specific command files live under
`.claude/commands/` and are maintained separately by the official Spec Kit
integration.

## Mandatory Policy for Code Interventions

Any activity that implies code modification must follow this mandatory path:

1. The **Orchestrator** handles intake and routing.
2. `/speckit.specify` creates or updates `spec.md`.
3. `/speckit.clarify` runs when the specification still has open ambiguities.
4. `/speckit.plan` creates `plan.md`.
5. `/speckit.tasks` creates `tasks.md`.
6. Implementation starts only after the previous steps are completed.

### Hard Gate

- No code edits without the full pipeline artifacts (`spec.md`, `plan.md`, `tasks.md`) for that intervention.
- If a code request reaches a specialist directly without spec context,
  it must be redirected to the **Orchestrator** first.
