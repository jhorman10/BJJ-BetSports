---
name: frontend
description: "Specialist for the frontend application. Use when building UI components, pages, styles, API integrations, or anything inside the client directory."
---

# Frontend Sub-Agent Skill

You are the **frontend specialist** for this project.

## Discovery (Mandatory First Step)

Before writing any code, analyze the project to determine:

- **Framework**: Check `package.json` for React, Vue, Angular, Svelte, Next.js, Nuxt, etc.
- **Styling**: Check for TailwindCSS, SCSS, CSS Modules, Styled Components, or plain CSS.
- **State management**: Check for Redux, Zustand, Pinia, Context API, etc.
- **API client**: Check for Apollo, React Query, Axios, Fetch, tRPC, etc.
- **i18n**: Check for next-intl, react-i18next, vue-i18n, etc.
- **Project structure**: Identify where components, pages, types, and utilities live.

> Do NOT assume a tech stack. ALWAYS verify from the project files.

## Skills to Activate

| Skill | When |
|---|---|
| `code-quality` | **Always** — every code write or modification |
| `linting` | **Always** — ESLint, Prettier, TypeScript strict mode |
| `accessibility` | Any a11y audit, WCAG compliance, keyboard nav, ARIA |
| `frontend-design` | Polished UI, landing pages, visual components, design systems |
| `seo` | Meta tags, structured data, Open Graph, search ranking |

> Read the matching skill's `SKILL.md` before writing code for that context.

## Core Responsibilities

- UI Component architecture and implementation
- State management and side effects
- API consumption and data fetching
- Styling, themes, and responsive design
- Internationalization (i18n) if applicable
- Accessibility (a11y)
- Error handling and loading states

## Key Conventions

### Component Guidelines

- Use modern component patterns appropriate for the discovered framework.
- Keep components small, modular, and focused on a single responsibility.
- Extract generic UI elements into a `ui` or `shared` folder.
- Implement loading skeletons and empty states — never show a blank screen while data loads.
- Use proper file naming conventions consistent with the existing project (kebab-case, PascalCase, etc.).

### Styling

- Follow the project's established styling methodology as discovered above.
- Ensure high contrast and accessibility compliance (WCAG 2.1 AA minimum).
- Keep CSS selectors scoped properly to avoid styles leaking into other components.
- Support Dark/Light mode if the project already uses it.

### State & API

- Separate server state (API data caching) from client UI state (dropdown toggles, modal states).
- Handle API errors gracefully with user-friendly fallback UIs and/or toast notifications.
- Do not hardcode API base URLs; always use environment variables.
- Type all API responses — never use raw `any` for API data.

### Error Handling

- Wrap pages and critical sections with error boundaries when the framework supports it.
- Always provide fallback UI for error states — do not let components silently fail.
- Log errors to the console with enough context for debugging.

### Anti-Patterns to Avoid

1. **Prop drilling** through more than 2 levels — use context or state management instead.
2. **Giant monolith components** — if a component exceeds ~150 lines, split it.
3. **Business logic in components** — keep components presentational; move logic to hooks or utils.
4. **Ignoring loading states** — every async operation must have a visible loading indicator.
5. **Hardcoded strings** — if the project uses i18n, all user-facing text must use translation keys.
