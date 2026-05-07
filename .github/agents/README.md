# Copilot Agents for BJJ-BetSports

This folder contains specialized agents for GitHub Copilot, mirroring the `.claude/agents` setup.

## Available Agents

- `orchestrator.agent.md` — Intake, classification, delegation, and Spec Kit enforcement.
- `frontend.agent.md` — Frontend work (`frontend/`).
- `backend.agent.md` — Backend APIs and services (`backend/`).
- `architecture.agent.md` — Cross-domain architecture and contracts.
- `speckit.*.agent.md` — Spec Kit pipeline agents (specify, plan, tasks, implement, etc.).

## Available Skills (co-activated by orchestrator)

| Skill | Trigger |
|---|---|
| `code-quality` | Always on code writes |
| `linting` | ESLint, Prettier, TypeScript |
| `devops` | Docker, CI/CD, GitHub Actions |
| `conventional-commits` | Commits, PRs, changelogs |
| `accessibility` | WCAG 2.2, a11y audits |
| `bash-defensive-patterns` | Production shell scripts |
| `frontend-design` | Polished UI / visual design |
| `python-executor` | Python execution, data analysis |
| `python-testing-patterns` | pytest, TDD, test suites |
| `seo` | Meta tags, structured data, search ranking |

## Default Tone

All agents default to caveman full: terse, direct, and compact.

## Spec Kit Compatibility

Agents work with Spec Kit prompts under `.github/prompts/`:

1. `/speckit.constitution`
2. `/speckit.specify`
3. `/speckit.clarify` (optional)
4. `/speckit.plan`
5. `/speckit.tasks`
6. `/speckit.implement`

## Mapping to Claude Setup

| Claude source | Copilot equivalent |
|---|---|
| `.claude/agents/orchestrator.md` | `orchestrator.agent.md` |
| `.claude/skills/frontend/SKILL.md` | `frontend.agent.md` |
| `.claude/skills/backend/SKILL.md` | `backend.agent.md` |
| `.claude/skills/architecture/SKILL.md` | `architecture.agent.md` |
| `.claude/skills/*/SKILL.md` | co-activated by orchestrator |
