# Arquitectura del Frontend - BJJ-BetSports

## Estructura de Tipos e Interfaces

### Ubicación de Tipos

Todos los tipos, interfaces y types deben estar en `/src/types/`:

- **`/src/types/index.ts`**: Tipos principales de dominio (Match, Prediction, League, Team, etc.)
- **`/src/types/components.ts`**: Props de componentes React

### Reglas de Componentes `.tsx`

1. **NO declarar interfaces/types localmente** - importar siempre desde `/src/types/`
2. **Separar lógica de presentación**:

   - Componentes `.tsx` solo deben contener JSX y lógica mínima de UI
   - Lógica de negocio debe estar en hooks custom (`/src/hooks/`)
   - Utilidades y helpers en `/src/utils/` (crear si no existe)

3. **Imports organizados**:

   ```tsx
   // 1. React y librerías externas
   import React from "react";
   import { Box, Typography } from "@mui/material";

   // 2. Tipos
   import { MatchPrediction, MatchCardProps } from "../../types";

   // 3. Hooks y servicios
   import { usePredictions } from "../../hooks/usePredictions";
   import { api } from "../../services/api";

   // 4. Componentes
   import MatchDetails from "../MatchDetails/MatchDetailsModal";
   ```

### Componentes Actualizados

✅ **completados**:

- `/components/BotDashboard/BotDashboard.tsx` - usa `TrainingStatus` desde types
- `/components/BotDashboard/MatchHistoryTable.tsx` - usa `MatchPredictionHistory`, `MatchHistoryTableProps`

⚠️ **Pendientes** (aún tienen interfaces locales):

- `/components/Parley/ParleySlip.tsx` - `ParleyPickItem`, `ParleySlipProps`
- `/components/Parley/ParleySection.tsx` - `ParleySectionProps`
- `/components/MatchCard/MatchCard.tsx` - `MatchCardProps`
- `/components/PredictionGrid/PredictionGridList.tsx` - `PredictionGridListProps`
- `/components/PredictionGrid/PredictionGridHeader.tsx` - `PredictionGridHeaderProps`
- `/components/PredictionGrid/PredictionGrid.tsx` - `PredictionGridProps`
- `/components/LiveMatches/LiveMatches.tsx` - `MatchCardProps` (conflicto de nombre)
- `/components/MatchDetails/MatchDetailsModal.tsx` - `MatchDetailsModalProps`
- `/components/MatchDetails/SuggestedPicksTab.tsx` - `SuggestedPicksTabProps`
- `/components/MatchDetails/LiveMatchesList.tsx` - `LiveMatchesListProps`
- `/components/MatchDetails/LiveMatchesView.tsx` - `LiveMatchesViewProps`
- `/components/MatchDetails/LiveMatchCard.tsx` - `LiveMatchCardProps`
- `/components/LeagueSelector/LeagueSelector.tsx` - `LeagueSelectorProps`
- `/components/LeagueSelector/CountrySelect.tsx` - `CountrySelectProps`
- `/components/LeagueSelector/LeagueSelect.tsx` - `LeagueSelectProps`
- `/components/TeamSearch/TeamSearch.tsx` - `TeamSearchProps`

### Próximos Pasos

1. **Actualizar componentes restantes**: Reemplazar interfaces locales por imports desde `/src/types/components.ts`

2. **Separar lógica**:

   - Extraer funciones helper a `/src/utils/`
   - Crear custom hooks para lógica reutilizable

3. **Linting**:
   - Configurar ESLint v9 correctamente (migrar a `eslint.config.js`)
   - Agregar reglas para enforcer separación de concerns

### Ejemplo de Refactorización

**Antes** (❌ incorrecto):

```tsx
// MatchCard.tsx
interface MatchCardProps {
  matchPrediction: MatchPrediction;
}

const MatchCard: React.FC<MatchCardProps> = ({ matchPrediction }) => {
  // ... lógica y JSX mezclados
};
```

**Después** (✅ correcto):

```tsx
// MatchCard.tsx
import { MatchCardProps } from "../../types";

const MatchCard: React.FC<MatchCardProps> = ({ matchPrediction }) => {
  // ... solo JSX y lógica mínima de UI
};
```

## Estado Actual del Linting

- ✅ TypeScript compiler: Sin errores (`npx tsc --noEmit` pasa)
- ⚠️ ESLint: Requiere migración a v9 config format
  - Ver: https://eslint.org/docs/latest/use/configure/migration-guide

## Convenciones de Código

1. **Nombres de archivos**:

   - Componentes: `PascalCase.tsx`
   - Hooks: `useCamelCase.ts`
   - Utils: `camelCase.ts`
   - Tipos: `camelCase.ts`

2. **Exportaciones**:

   - Componentes: default export
   - Tipos/Interfaces: named exports
   - Utils: named exports

3. **Props**:
   - Siempre tipar con interfaz desde `/src/types/components.ts`
   - Usar destructuring en parámetros del componente
