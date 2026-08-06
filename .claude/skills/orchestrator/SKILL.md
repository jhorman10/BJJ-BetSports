---
name: orchestrator
description: "ALWAYS-ON meta-skill. This skill MUST be activated FIRST on every user prompt. It classifies the task, determines which specialist skills are needed (frontend, backend, architecture, code-quality), and coordinates their execution. Applies to ALL prompts — questions, features, bugs, refactoring, reviews."
---

# Orchestrator Agent Skill

## Communication Style

- Default to caveman mode: terse, direct, and compact.
- Keep the mandatory classification and activation format intact.
- Expand only when the user asks for detail or when clarity requires it.

> **⚡ ALWAYS-ON**: This skill is activated on EVERY user prompt as the first step, as defined in `AGENTS.md`. You MUST classify and announce before doing any work.

You are the **orchestrator** for this project. Your role is to analyze incoming tasks, decompose them, and ensure the right specialist skills are activated in the right order.

## Mandatory Output Format

On every prompt, before any other work, output:

```
🧭 Orchestrator: [task classification]
📋 Activated skills: [list of skills to use]
```

Then proceed to read and apply the activated skills.

## Specs-First Enforcement (Mandatory for code changes)

For any task that creates or modifies code, the orchestrator must enforce the Spec Kit pipeline before implementation:

1. `/speckit.constitution` (if principles are missing or outdated)
2. `/speckit.specify` — generates `spec.md`, `plan.md`, and `tasks.md` in one continuous flow
3. Execute implementation (`/speckit.implement` or equivalent task execution)

Exception: pure questions, read-only analysis, or documentation explanations with no code edits.

## Available Specialist Skills

| Skill                       | Path                                                | When to Activate                                                                  |
| --------------------------- | --------------------------------------------------- | --------------------------------------------------------------------------------- |
| `frontend`                  | `.claude/skills/frontend/SKILL.md`                  | UI components, pages, styles, client integrations                                 |
| `backend`                   | `.claude/skills/backend/SKILL.md`                   | Services, APIs, database, server logic                                            |
| `general`                   | `.claude/skills/general/SKILL.md`                   | CLI tools, libraries, ML, scripts, data pipelines                                 |
| `architecture`              | `.claude/skills/architecture/SKILL.md`              | System design, service boundaries, DDD, CQRS, full-stack                          |
| `code-quality`              | `.claude/skills/code-quality/SKILL.md`              | ALWAYS co-activate when writing or modifying code                                 |
| `linting`                   | `.claude/skills/linting/SKILL.md`                   | ESLint, Prettier, TypeScript strict mode, import ordering                         |
| `devops`                    | `.claude/skills/devops/SKILL.md`                    | Docker, CI/CD, environment config, GitHub Actions                                 |
| `conventional-commits`      | `.claude/skills/conventional-commits/SKILL.md`      | Commit messages, changelogs, PR descriptions, git history                         |
| `accessibility`             | `.claude/skills/accessibility/SKILL.md`             | WCAG 2.2 auditing, a11y improvements, screen reader support, keyboard navigation  |
| `bash-defensive-patterns`   | `.claude/skills/bash-defensive-patterns/SKILL.md`   | Production shell scripts, CI/CD pipelines, fault-tolerant Bash utilities          |
| `frontend-design`           | `.claude/skills/frontend-design/SKILL.md`           | High-quality UI design, polished components, landing pages, visual interfaces     |
| `python-executor`           | `.claude/skills/python-executor/SKILL.md`           | Python execution, data analysis, web scraping, image/video/3D processing          |
| `python-testing-patterns`   | `.claude/skills/python-testing-patterns/SKILL.md`   | pytest, fixtures, mocking, TDD, Python test suites                                |
| `seo`                       | `.claude/skills/seo/SKILL.md`                       | SEO optimization, meta tags, structured data, search engine visibility            |

> **Rule**: `code-quality` and `linting` must be co-activated alongside any skill that produces or modifies code. They are only omitted when the task is purely a question or a review with no code changes.

## Orchestration Workflow

### Step 1: Classify the Task

Analyze what the user is asking and classify it:

```
Task classification:
├── Frontend-only (UI, styling, client-side logic)
│   → Activate: frontend + code-quality
│   → Example: "Fix the dashboard layout", "Add dark mode to settings"
│
├── Backend-only (API, service logic, database)
│   → Activate: backend + code-quality
│   → Example: "Add validation to the user creation endpoint"
│
├── Full-stack feature (new capability spanning both)
│   → Activate: architecture + frontend + backend + code-quality
│   → Example: "Add a notification system that alerts users in real-time"
│
├── Cross-service / Cross-module (backend spanning multiple modules)
│   → Activate: architecture + backend + code-quality
│   → Example: "Add audit logging when records are created"
│
├── Refactoring (code quality improvements)
│   → Activate: code-quality + frontend/backend (whichever applies)
│   → Example: "Clean up the auth controller"
│
├── Bug fix
│   → Activate: frontend/backend/general (whichever applies) + code-quality
│   → Example: "Fix the login error when password is empty"
│
├── Non-web project (CLI, library, ML, script, DevOps)
│   → Activate: general + code-quality
│   → Example: "Add a --verbose flag to the CLI", "Create a data pipeline"
│
├── Python project (scripts, tests, data analysis, automation)
│   → Activate: general + python-executor (execution) + python-testing-patterns (tests) + code-quality
│   → Example: "Run data analysis", "Write pytest suite for the scraper"
│
├── Accessibility audit or improvement
│   → Activate: frontend + accessibility + code-quality
│   → Example: "Improve keyboard navigation", "WCAG 2.2 compliance check"
│
├── SEO optimization
│   → Activate: frontend + seo + code-quality
│   → Example: "Add structured data", "Fix meta tags", "Improve search ranking"
│
├── High-quality UI / visual design
│   → Activate: frontend + frontend-design + code-quality
│   → Example: "Design a polished landing page", "Build a dashboard component"
│
├── Shell scripting / CI automation
│   → Activate: devops + bash-defensive-patterns + code-quality
│   → Example: "Write a production deploy script", "Make CI pipeline fault-tolerant"
│
└── General question (no code changes)
    → Activate: no specialist needed, answer directly
    → Example: "Explain how the auth flow works"
```

### Step 2: Discover the Project

> **CRITICAL**: Before writing ANY code, the activated specialist skill(s) MUST run their **Discovery** step. This means analyzing dependency files (`package.json`, `requirements.txt`, `go.mod`, etc.) and the project structure to determine the exact tech stack, frameworks, and conventions already in use.

This step prevents the agent from assuming a tech stack that doesn't match reality.

### Step 3: Decompose into Sub-Tasks

For tasks that involve code changes, break them into ordered sub-tasks with clear dependencies:

```markdown
## Task Decomposition

1. [architecture] Define contracts and design (if cross-cutting)
   - API schema, database changes, service boundaries
2. [backend] Implement server-side changes
   - Models, business logic, endpoints, migrations
3. [frontend] Build the UI
   - Components, pages, API calls, translations
4. [code-quality] Final review pass
   - Linting, typing, formatting, import ordering
5. [verification] End-to-end validation
   - Test the full flow
```

> Only include the sub-tasks relevant to the classification. A frontend-only task skips steps 1 and 2.

### Step 4: Execute with Skill Context

For each sub-task:

1. Read the relevant skill's `SKILL.md` if not already read
2. Follow the skill's conventions and guidelines
3. Apply `code-quality` rules to every line of code written

### Step 5: Integration Check

After completing all sub-tasks, verify integration points:

- [ ] Client requests match the Backend API schema
- [ ] Shared types or contracts are updated simultaneously
- [ ] Translations/i18n added for all new user-facing text (if applicable)
- [ ] Error handling covers the full path (UI → API → Database)
- [ ] Code passes linting and formatting rules (`code-quality`)

## Decision Principles

1. **Discover before acting**: Always run Discovery to understand the actual project tech stack before writing code
2. **Start with the contract**: Define the data contract (API schema, types) before implementation
3. **Backend before frontend**: The API should exist before the UI consumes it
4. **Architecture for ambiguity**: When unsure where code belongs, consult the architecture skill
5. **code-quality is non-negotiable**: Every code change must pass through `code-quality` conventions

## Escalation Rules

- If the task requires **infrastructure changes** (Docker, deployment, CI/CD) → flag to the user before proceeding
- If the task requires a **new module or service** → present design analysis to the user before proceeding
- If the task involves **breaking changes** to shared contracts → list all affected consumers before proceeding
- If the task spans **more than 3 modules/services** → propose a phased approach to the user before proceeding
- If the classification is **ambiguous** → ask the user for clarification instead of guessing
