# Workspace Agent Rules

## 🔒 Mandatory First Step: Orchestrator Activation

**On EVERY user prompt**, before doing anything else, you MUST:

1. **Read** the orchestrator skill at `.github/skills/orchestrator/SKILL.md`
2. **Follow** the orchestrator's full workflow (classify → announce → activate → execute)

This applies to ALL prompts — questions, feature requests, bug fixes, refactoring, reviews, etc.

For any prompt that requires code changes, follow a specs-first flow before implementation:

1. `/speckit.constitution` (when principles are missing/outdated)
2. `/speckit.specify`
3. `/speckit.plan`
4. `/speckit.tasks`
5. implement from generated tasks (`/speckit.implement` or equivalent)

### Hard Gate (Mandatory)

- No code edits are allowed before a feature specification exists for the intervention.
- Minimum required artifacts before coding: `spec.md`, `plan.md`, and `tasks.md`.
- For any code intervention, the expected path is:
	`orchestrator` → `/speckit.specify` → `/speckit.plan` → `/speckit.tasks` → implementation.
- If a request arrives directly to a specialist with no spec context, the specialist must stop and redirect to `orchestrator`.

> The orchestrator will determine which specialist skills to activate. Do NOT skip this step. Do NOT guess which skills to use without reading the orchestrator first.

### Specialist Skills Available

| Skill                   | Path                                                | Scope                                                    |
| ----------------------- | --------------------------------------------------- | -------------------------------------------------------- |
| `frontend`              | `.github/skills/frontend/SKILL.md`                   | Everything in the frontend directory                     |
| `backend`               | `.github/skills/backend/SKILL.md`                    | Everything in the backend directory                      |
| `general`               | `.github/skills/general/SKILL.md`                    | CLI, libraries, ML, scripts, non-web code                |
| `architecture`          | `.github/skills/architecture/SKILL.md`               | Cross-cutting, system design                             |
| `software-architecture` | `.github/skills/software-architecture/SKILL.md`      | Clean Arch, Hexagonal, DDD, CQRS, microservices          |
| `design-patterns`       | `.github/skills/design-patterns/SKILL.md`            | GoF patterns, NestJS/React-specific patterns             |
| `clean-code`            | `.github/skills/clean-code/SKILL.md`                 | Naming, functions, comments, error handling              |
| `best-practices`        | `.github/skills/best-practices/SKILL.md`             | SOLID, DRY, YAGNI, security baseline, testing            |
| `linting`               | `.github/skills/linting/SKILL.md`                    | ESLint, Prettier, TypeScript strict mode                 |
| `devops`                | `.github/skills/devops/SKILL.md`                     | Docker, CI/CD pipelines, GitHub Actions                  |
| `conventional-commits`  | `.github/skills/conventional-commits/SKILL.md`       | Commit messages, changelogs, git history                 |
| `code-quality`          | `.github/skills/code-quality/SKILL.md`               | SOLID, typing, linting, commits — always-on for code     |
| `orchestrator`          | `.github/skills/orchestrator/SKILL.md`               | Task routing & decomposition (always-on)                 |

### Specialist Agents Available (Claude Code)

| Agent          | Path                            | Scope                                     |
| -------------- | ------------------------------- | ----------------------------------------- |
| `orchestrator` | `.claude/agents/orchestrator.md`| Prompt intake, routing, specs-first flow  |

> Claude custom agent selector is intentionally restricted to the `orchestrator` entrypoint.
> Domain specialization is applied through skills (`frontend`, `backend`, `architecture`) after orchestration.

### Copilot Agents

Copilot workspace agents live in `.github/agents/` and are documented in `.github/agents/README.md`.

- `hypergenia-backend.agent.md`
- `hypergenia-frontend.agent.md`
- `hypergenia-architecture.agent.md`
- `hypergenia-orchestrator.agent.md`

## Language

Respond in the same language the user writes in.

## Default Tone

Use caveman full by default: terse, direct, and compact. Prefer the shortest useful answer unless the user asks for more detail.
