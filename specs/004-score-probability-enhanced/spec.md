# Feature Specification: Marcador Tentativo Avanzado

**Feature Branch**: `004-score-probability-enhanced`  
**Created**: 2026-08-07  
**Status**: Draft  
**Input**: Mejora de "Marcador Tentativo" existente incorporando: (1) matriz completa de scores, (2) desglose xG por equipo en cada score, (3) histórico de precisión por liga, (4) modal dedicada de visualización.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Visualizar matriz completa de scores (Priority: P1)

Como usuario, quiero ver una matriz/grilla completa de todos los scores posibles (0-5 goles por equipo) con sus probabilidades, para entender la distribución completa y no solo los top-5.

**Why this priority**: Es la mejora más visible y tangible. El usuario pidió "más posibilidades", y la matriz completa entrega eso directamente.

**Independent Test**: Abrir el detalle de un partido, hacer clic en "Marcador Tentativo" y verificar que aparece una matriz 6x6 (0-5 goles) con todas las probabilidades visibles.

**Acceptance Scenarios**:

1. **Given** un partido con predicciones, **When** el usuario abre la sección "Marcador Tentativo", **Then** ve una matriz 6x6 con celdas coloreadas por intensidad de probabilidad.
2. **Given** la matriz de scores, **When** el usuario observa una celda, **Then** muestra el score exacto y su probabilidad porcentual.
3. **Given** la matriz de scores, **When** el usuario compara celdas, **Then** las celdas con mayor probabilidad tienen mayor intensidad de color.

---

### User Story 2 - Desglose xG por equipo en cada score (Priority: P1)

Como usuario, quiero ver en cada score exacto qué porcentaje del mismo se explica por el xG del local vs el xG del visitante, para entender la contribución ofensiva/defensiva de cada equipo.

**Why this priority**: El usuario pidió usar "modelos estadísticos avanzados" y el desglose xG agrega transparencia y profundidad analítica al marcador tentativo.

**Independent Test**: Verificar que cada celda de la matriz incluye un tooltip o badge que muestra la contribución porcentual del xG local y visitante a ese score.

**Acceptance Scenarios**:

1. **Given** una celda de la matriz con score 2-1, **When** el usuario hace hover o expande la celda, **Then** ve algo como "Local: 62% | Visitante: 38%" que explica la contribución ofensiva de cada equipo a ese resultado.
2. **Given** un score donde domina claramente el local (ej: 3-0), **When** se muestra el desglose xG, **Then** la contribución del local es mayor al 70%.

---

### User Story 3 - Histórico de precisión del modelo por liga (Priority: P2)

Como usuario, quiero ver un indicador de confiabilidad histórica del modelo para la liga del partido, para saber si el "Marcador Tentativo" suele acertar en esa competición.

**Why this priority**: Añade contexto crucial para interpretar el marcador. El usuario pidió un "nivel de confianza basado en la fiabilidad estadística del modelo", y el histórico es la medición directa de esa fiabilidad.

**Independent Test**: Verificar que el modal o tarjeta de "Marcador Tentativo" muestra un indicador tipo "Precisión histórica: 34% en Liga MX" o similar.

**Acceptance Scenarios**:

1. **Given** una liga con historial de predicciones almacenado, **When** se muestra el marcador tentativo, **Then** aparece un indicador de precisión histórica (ej: "Acierto exacto: 28% en últimos 50 partidos").
2. **Given** una liga sin historial suficiente, **When** se muestra el indicador, **Then** muestra "Datos insuficientes" o similar.
3. **Given** el histórico de precisión, **When** el usuario compara dos ligas, **Then** puede ver que una tiene mayor fiabilidad que otra.

---

### User Story 4 - Modal dedicada de visualización avanzada (Priority: P1)

Como usuario, quiero acceder a una vista dedicada y expandida del "Marcador Tentativo" desde la tarjeta del partido, para analizar los scores con comodidad sin saturar la vista principal.

**Why this priority**: La matriz completa y el desglose xG necesitan espacio. Un modal dedicado es la solución estándar para visualizaciones densas sin comprometer la UX del listado.

**Independent Test**: Hacer clic en el chip/badge "Marcador Tentativo" en `MatchCard` o en la sección de `PreMatchPrediction`, y verificar que se abre un modal con la matriz completa, desglose xG e histórico de precisión.

**Acceptance Scenarios**:

1. **Given** un partido con predicciones, **When** el usuario hace clic en el indicador de "Marcador Tentativo", **Then** se abre un modal con la matriz completa de scores.
2. **Given** el modal abierto, **When** el usuario observa la matriz, **Then** puede ver el desglose xG y el histórico de precisión en la misma vista.
3. **Given** el modal abierto, **When** el usuario hace clic fuera o en cerrar, **Then** el modal se cierra y vuelve a la vista anterior.

---

### Edge Cases

- **Liga sin historial**: Si no hay predicciones pasadas para una liga, el sistema muestra "Precisión: N/A" en lugar de un número.
- **xG muy bajo**: Si `predicted_home_goals` o `predicted_away_goals` son muy bajos (< 0.3), el desglose xG se muestra con advertencia "Baja muestra".
- **Performance de la matriz**: La matriz completa es solo 36 celdas (6x6), pero si se expande a 10x10, se debe cachear el cálculo.
- **Responsive**: El modal debe funcionar en mobile con la matriz en formato vertical/scroll.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El backend DEBE exponer `score_matrix` como array 2D en `PredictionModel`, donde cada celda contiene `{home_goals, away_goals, probability, home_xg_contribution, away_xg_contribution}`.
- **FR-002**: El backend DEBE calcular `home_xg_contribution` y `away_xg_contribution` para cada score, basándose en la proporción de `predicted_home_goals` vs `predicted_away_goals` dentro de la probabilidad conjunta.
- **FR-003**: El backend DEBE exponer `score_accuracy_history` en `PredictionModel` con `{league_id, total_predictions, exact_score_hits, accuracy_percentage}` o `null` si no hay datos.
- **FR-004**: El backend DEBE calcular `score_accuracy_history` consultando predicciones pasadas en MongoDB que tengan `score_probabilities` y comparando el score real vs el más probable.
- **FR-005**: El frontend DEBE renderizar una matriz 6x6 de scores en el modal dedicado, con celdas coloreadas por intensidad de probabilidad.
- **FR-006**: El frontend DEBE mostrar el desglose xG (local vs visitante) en tooltip o badge al hover de cada celda.
- **FR-007**: El frontend DEBE mostrar el histórico de precisión en el modal, con formato "Acierto exacto: X% (Y/Z partidos)".
- **FR-008**: El frontend DEBE abrir el modal al hacer clic en el chip/badge de "Marcador Tentativo" en `MatchCard` o `PreMatchPrediction`.
- **FR-009**: Los campos nuevos DEBEN ser opcionales en el schema Pydantic y TypeScript para mantener retrocompatibilidad.

### Key Entities *(include if feature involves data)*

- **Prediction (backend entity)**: Se agrega `score_matrix: Optional[list[list[dict]]]` y `score_accuracy_history: Optional[dict]`.
- **PredictionModel (Pydantic schema)**: Se agregan `score_matrix` y `score_accuracy_history`.
- **Prediction (frontend interface)**: Se agregan `score_matrix?: ScoreCell[][]` y `score_accuracy_history?: ScoreAccuracyHistory`.
- **ScoreCell (nuevo)**: `{home_goals: number, away_goals: number, probability: number, home_xg_contribution: number, away_xg_contribution: number}`.
- **ScoreAccuracyHistory (nuevo)**: `{league_id: string, total_predictions: number, exact_score_hits: number, accuracy_percentage: number}`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las predicciones con xG definido incluyen `score_matrix` con 36 celdas (6x6).
- **SC-002**: El 100% de las predicciones con xG definido incluyen `home_xg_contribution` y `away_xg_contribution` en cada celda.
- **SC-003**: El 100% de las ligas con ≥5 predicciones pasadas incluyen `score_accuracy_history` con accuracy calculada.
- **SC-004**: El modal se abre en <200ms y renderiza la matriz completa sin lag.
- **SC-005**: Los tests unitarios existentes siguen pasando al 100% (regression zero).
- **SC-006**: La cobertura de tests para los nuevos campos y métodos es ≥80%.

## Assumptions

- **Assumption**: MongoDB tiene colección de predicciones históricas con `score_probabilities` y resultado real del partido para calcular accuracy.
- **Assumption**: El frontend puede usar Material-UI `Dialog` para el modal dedicado.
- **Assumption**: `predicted_home_goals` y `predicted_away_goals` son suficientes para calcular la contribución xG por score.
- **Assumption**: La matriz se limita a 0-5 goles por equipo (36 celdas) para mantener performance y legibilidad.
- **Assumption**: El cálculo de `score_accuracy_history` se hace on-the-fly consultando MongoDB, no se cachea en Redis por complejidad.
