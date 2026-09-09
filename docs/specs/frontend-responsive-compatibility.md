# Spec: Frontend Responsive & Multi-Platform Compatibility

## Intent
Garantizar que la aplicación BJJ-BetSports sea **totalmente funcional, visualmente consistente y performante** en cualquier combinación de:
- **Dispositivos**: mobile (320px+), tablet (768px+), desktop (1024px+), ultrawide (1440px+)
- **Navegadores**: Chrome, Firefox, Safari, Edge (últimas 2 versiones)
- **Sistemas operativos**: iOS, Android, macOS, Windows, Linux
- **Orientaciones**: portrait, landscape
- **Densidades de píxel**: 1x, 2x (Retina), 3x+

## Scope
- **In scope**: todos los componentes de `src/presentation/`, CSS global, breakpoints, touch targets, viewport meta, fuentes fluidas, imágenes responsive, navegación mobile, formularios, tablas, modales, skeletons, estados de carga/error
- **Out of scope**: lógica de negocio, APIs, backend, CI/CD, testing E2E (cubierto por spec separado)

## Requirements

### R1: Viewport & Meta Tags
- **R1.1** `index.html` debe tener `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`
- **R1.2** `theme-color` definido para mobile browsers
- **R1.3** `apple-mobile-web-app-capable` y `apple-mobile-web-app-status-bar-style` para iOS PWA

### R2: Breakpoint System (CSS)
- **R2.1** Breakpoints definidos como CSS custom properties:
  - `--bp-xs: 320px` (mobile small)
  - `--bp-sm: 480px` (mobile large)
  - `--bp-md: 768px` (tablet)
  - `--bp-lg: 1024px` (desktop)
  - `--bp-xl: 1440px` (desktop large)
  - `--bp-2xl: 1920px` (ultrawide)
- **R2.2** Breakpoints usados consistentemente en todo el CSS (no magic numbers)
- **R2.3** Container queries donde sea apropiado (cards, grids internos)

### R3: Fluid Typography & Spacing
- **R3.1** Sistema de fuentes fluidas usando `clamp()`:
  - `--fs-xs: clamp(0.75rem, 0.7rem + 0.25vw, 0.875rem)`
  - `--fs-sm: clamp(0.875rem, 0.8rem + 0.35vw, 1rem)`
  - `--fs-base: clamp(1rem, 0.9rem + 0.5vw, 1.125rem)`
  - `--fs-lg: clamp(1.125rem, 1rem + 0.6vw, 1.25rem)`
  - `--fs-xl: clamp(1.25rem, 1.1rem + 0.75vw, 1.5rem)`
  - `--fs-2xl: clamp(1.5rem, 1.25rem + 1.25vw, 2rem)`
  - `--fs-3xl: clamp(2rem, 1.5rem + 2.5vw, 3rem)`
- **R3.2** Espaciado fluido con `--space-*` usando `clamp()`
- **R3.3** Line-height mínimo 1.5 para body, 1.2 para headings

### R4: Touch Targets & Interactions
- **R4.1** Mínimo 44×44px (iOS) / 48×48dp (Material) para todos los touch targets
- **R4.2** Espaciado mínimo 8px entre touch targets adyacentes
- **R4.3** Estados `:active`, `:hover`, `:focus-visible` diferenciados
- **R4.4** No hover-only functionality en mobile (progressive enhancement)
- **R4.5** Scroll suave nativo (`scroll-behavior: smooth`)

### R5: Layout & Grid Systems
- **R5.1** CSS Grid / Flexbox como base (no floats)
- **R5.2** Grids responsive con `repeat(auto-fit, minmax(280px, 1fr))` o similar
- **R5.3** Container queries para componentes que se reusan en distintos contenedores
- **R5.4** Sidebar/drawer mobile: off-canvas con `transform` + `overlay`, no `position: fixed` que rompa scroll
- **R5.5** Header sticky con `position: sticky` + `top: 0` + `z-index` apropiado

### R6: Navigation Mobile
- **R6.1** Hamburger menu / bottom nav en < 768px
- **R6.2** Focus trap en modales/drawers
- **R6.3** ARIA labels y roles correctos (`role="navigation"`, `aria-label`, `aria-expanded`)
- **R6.4** Skip link para accesibilidad teclado

### R7: Forms & Inputs
- **R7.1** `input[type="text"]` mínimo 16px font-size (evita zoom iOS)
- **R7.2** Labels asociados correctamente (`htmlFor` / `id`)
- **R7.3** Validación inline con `aria-live="polite"`
- **R7.3** Autocomplete attributes correctos (`autocomplete="email"`, etc.)

### R8: Tables & Data Grids
- **R8.1** Horizontal scroll en mobile con `overflow-x: auto` + shadow indicador
- **R8.2** Sticky first column en desktop
- **R8.3** Card view alternativo en < 640px (stack rows as cards)
- **R8.4** Paginación touch-friendly (botones 44px+)

### R9: Images & Media
- **R9.1** `srcset` + `sizes` para imágenes responsivas
- **R9.2** `loading="lazy"` para imágenes below-the-fold
- **R9.3** Aspect-ratio preservado (`aspect-ratio` CSS)
- **R9.4** Placeholders (blur-up, skeleton) durante carga

### R10: Modals, Drawers, Overlays
- **R10.1** Portal para modales (render outside root)
- **R10.2** Body scroll lock (`overflow: hidden` + padding-right compensation)
- **R10.3** Focus restoration al cerrar
- **R10.4** Close en Esc, click overlay, swipe down (mobile)

### R11: Performance & Loading
- **R11.1** Skeleton loaders con misma geometría que contenido real
- **R11.2** `content-visibility: auto` para listas largas
- **R11.3** Code-splitting por ruta (`React.lazy` + `Suspense`)
- **R11.4** Preload critical assets (`<link rel="preload">`)

### R12: Cross-Browser Consistency
- **R12.1** CSS reset/normalize incluido
- **R12.2** Prefijos autoprefixer (configurado en Vite/PostCSS)
- **R12.3** Fallbacks para CSS moderno (`@supports`, graceful degradation)
- **R12.4** Testing visual en Chrome, Firefox, Safari (Desktop + Mobile)

### R13: Accessibility (WCAG 2.2 AA)
- **R13.1** Contraste mínimo 4.5:1 (texto), 3:1 (UI components)
- **R13.2** Focus visible siempre visible (`:focus-visible`)
- **R13.3** Semántica HTML correcta (landmarks, headings hierarchy)
- **R13.4** Reduced motion support (`@media (prefers-reduced-motion)`)

### R13: PWA Readiness
- **R14.1** `manifest.json` con icons 192/512, theme_color, display: standalone
- **R14.2** Service Worker para offline-first (cache-first para assets, network-first para API)
- **R14.3** `apple-touch-icon` + `maskable-icon` para iOS

## Acceptance Criteria
| ID | Criterion | Verification |
|----|-----------|--------------|
| AC1 | Viewport meta correcto | Manual + Lighthouse |
| AC2 | Breakpoints funcionan en 320/480/768/1024/1440 | Chrome DevTools device toolbar |
| AC3 | Touch targets ≥ 44px en mobile | Lighthouse Accessibility + manual |
| AC4 | Tipografía fluida sin overflow horizontal | Resize viewport 320→1920px |
| AC5 | Navegación mobile usable (hamburger/drawer) | Manual testing iOS Safari + Chrome Android |
| AC6 | Modales/drawers accesibles (focus trap, Esc, swipe) | axe-core + manual |
| AC7 | Formularios usables en mobile (16px font, labels) | Manual + axe |
| AC8 | Tablas usables en mobile (scroll horizontal o card view) | Manual |
| AC9 | Imágenes lazy + responsive (srcset) | Network tab + Lighthouse |
| AC10 | Lighthouse Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90 | Lighthouse CI |
| AC11 | Sin errores de consola en Chrome/Firefox/Safari mobile | Manual testing |
| AC12 | React Doctor score ≥ 90 (0 critical, ≤ 5 warnings) | `npx react-doctor` |

## Non-Goals
- E2E testing con Playwright/Cypress (spec separado)
- Backend API changes
- Internationalization (i18n) - spec separado
- Animaciones complejas (Framer Motion) - opcional

## Dependencies
- React Doctor issues resueltos (pre-requisito)
- Tailwind CSS / CSS-in-JS configurado para breakpoints
- Lighthouse CI en pipeline

## Risks
- Componentes gigantes (`no-giant-component`) dificultan responsive → refactor previo
- Array index as key → keys estables rompen virtualización en listas largas
- Empty default props en memo → rompen memoización en mobile (re-renders excesivos)
- Large components → difíciles de testear responsive