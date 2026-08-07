# Technical Plan: Marcador Tentativo Avanzado

**Feature Branch**: `004-score-probability-enhanced`  
**Created**: 2026-08-07  
**Status**: Draft  
**Spec**: `specs/004-score-probability-enhanced/spec.md`

## Architecture Context

Proyecto Clean Architecture + React + MUI + MongoDB. La feature básica "Marcador Tentativo" ya existe. Esta mejora extiende la salida de API y agrega un modal frontend sin cambiar contratos existentes.

## Approach

Estrategia mínima e incremental:

1. **Backend**: Extender `PredictionService` para calcular `score_matrix` completo y `score_accuracy_history`. Agregar método `calculate_score_contributions()` para desglose xG por score.
2. **Backend**: Actualizar `Prediction` entity, `PredictionModel` schema y `prediction_mapper.py`.
3. **Backend**: Agregar endpoint auxiliar `GET /api/v1/predictions/accuracy/{league_id}` para histórico de precisión (opcional, puede ir en el schema de predicción).
4. **Frontend**: Crear componente `ScoreMatrixModal.tsx` con matriz 6x6 coloreada, tooltips con xG breakdown, y sección de accuracy history.
5. **Frontend**: Integrar modal en `PreMatchPrediction.tsx` y `MatchCard.tsx`.

## Technical Decisions

| Decision | Opciones | Elegido | Razón |
|---|---|---|---|
| Matriz completa | API separada vs campo en Prediction | Campo en Prediction | No requiere nuevo endpoint; retrocompatible |
| Límite matriz | 6x6 vs 8x8 vs 10x10 | 6x6 (0-5 goles) | 36 celdas es óptimo para UI; 8x8 = 64 celdas satura |
| xG contribution | Fórmula Bayesiana vs proporción simple | Proporción simple: `(score_prob / total_prob) * (xG_home / (xG_home + xG_away))` | Suficiente para tooltip informativo |
| Accuracy history | Nueva colección MongoDB vs query agregada | Query agregada sobre colección existente de predicciones | Sin migración; reusa datos existentes |
| Modal | Drawer vs Dialog | MUI Dialog | Estándar en el proyecto; ya usado en MatchDetailsModal |
| Color encoding | Escala continua vs 5 niveles | 5 niveles discretos (muy bajo/bajo/medio/alto/muy alto) | Mejor accesibilidad y legibilidad |

## Scope

### In Scope
- Backend: `calculate_score_matrix()` con contribuciones xG
- Backend: `calculate_score_accuracy_history()` consultando MongoDB
- Backend: actualización de entity, schema y mapper
- Backend: tests unitarios
- Frontend: `ScoreMatrixModal.tsx` con matriz 6x6, tooltips, accuracy history
- Frontend: integración en `PreMatchPrediction.tsx` y `MatchCard.tsx`
- Frontend: tests de componente

### Out of Scope
- Gráfico de línea de accuracy histórica por fecha
- Comparación entre ligas
- Exportación de la matriz a imagen
- Animaciones avanzadas en el modal

## Data Model Changes

### Backend Entity (`Prediction`)
```python
@dataclass
class Prediction:
    # ... campos existentes ...
    score_matrix: Optional[list[list[dict]]] = None  # 6x6 matrix
    score_accuracy_history: Optional[dict] = None  # accuracy stats
```

### Pydantic Schema (`PredictionModel`)
```python
class ScoreCell(BaseModel):
    home_goals: int
    away_goals: int
    probability: float
    home_xg_contribution: float  # 0-1
    away_xg_contribution: float  # 0-1

class ScoreAccuracyHistory(BaseModel):
    league_id: str
    total_predictions: int
    exact_score_hits: int
    accuracy_percentage: float

class PredictionModel(BaseModel):
    # ... campos existentes ...
    score_matrix: Optional[list[list[ScoreCell]]] = None
    score_accuracy_history: Optional[ScoreAccuracyHistory] = None
```

### Frontend Interfaces
```typescript
interface ScoreCell {
  home_goals: number;
  away_goals: number;
  probability: number;
  home_xg_contribution: number;
  away_xg_contribution: number;
}

interface ScoreAccuracyHistory {
  league_id: string;
  total_predictions: number;
  exact_score_hits: number;
  accuracy_percentage: number;
}

interface Prediction {
  // ... campos existentes ...
  score_matrix?: ScoreCell[][];
  score_accuracy_history?: ScoreAccuracyHistory;
}
```

## Algorithm

### Score Matrix con xG Contribution
```python
# Para cada h en 0..5, a en 0..5:
#   P(h,a) = Poisson(h, λ_home) * Poisson(a, λ_away)
#   home_contrib = (λ_home / (λ_home + λ_away)) * normalizar(P(h,a))
#   away_contrib = (λ_away / (λ_home + λ_away)) * normalizar(P(h,a))
```

Donde `normalizar` escala la contribución para que sume 1 entre ambos equipos por score.

### Accuracy History
```python
# Query MongoDB:
#   predictions con score_probabilities y match con resultado real
#   Agrupar por league_id
#   Calcular: exact_score_hits = count donde max(score_probabilities).score == real_score
#   accuracy_percentage = exact_score_hits / total_predictions
```

## API Changes

### Response Schema (extiende `PredictionModel`)
```json
{
  "match_id": "123",
  "predicted_home_goals": 1.8,
  "predicted_away_goals": 1.2,
  "score_probabilities": [...],
  "score_confidence_tier": "Alta",
  "score_matrix": [
    [{"home_goals":0,"away_goals":0,"probability":0.08,"home_xg_contribution":0.6,"away_xg_contribution":0.4}, ...],
    ...
  ],
  "score_accuracy_history": {
    "league_id": "Liga MX",
    "total_predictions": 47,
    "exact_score_hits": 13,
    "accuracy_percentage": 0.277
  }
}
```

### Endpoints afectados
- `GET /api/v1/predictions/league/{league_id}` — ahora incluye `score_matrix` y `score_accuracy_history`
- `GET /api/v1/predictions/match/{match_id}` — mismos campos nuevos
- No se agregan endpoints nuevos; se extienden los existentes.

## Frontend Changes

### Componentes nuevos
1. **`ScoreMatrixModal.tsx`**: Modal con matriz 6x6, celdas coloreadas, tooltips con xG breakdown, sección de accuracy.

### Componentes modificados
1. **`PreMatchPrediction.tsx`**: Cambiar chips de score_probabilities por botón que abre `ScoreMatrixModal`.
2. **`MatchCard.tsx`**: Cambiar chip de confianza por botón que abre `ScoreMatrixModal`.

### UX Decisions
- Matriz 6x6 con celdas tipo heatmap (5 niveles de opacidad/color)
- Tooltip al hover: "2-1 | Prob: 15.2% | Local: 62% | Visitante: 38%"
- Sección accuracy: "Acierto exacto: 27.7% (13/47 partidos)"
- Botón de apertura: chip/badge clickeable con etiqueta "Marcador Tentativo"
- Responsive: en mobile, matriz en scroll horizontal

## Testing Strategy

### Backend Tests
- `test_score_matrix_basic`: Verifica que la matriz es 6x6 y suma de probabilidades ~1.
- `test_score_matrix_xg_contributions`: Verifica que home_xg_contribution + away_xg_contribution ≈ 1 por celda.
- `test_score_accuracy_history_calculation`: Verifica cálculo de accuracy desde MongoDB.
- `test_score_accuracy_history_no_data`: Verifica retorno de None cuando no hay historial.
- `test_generate_prediction_includes_matrix`: Verifica que generate_prediction pobla score_matrix.

### Frontend Tests
- `ScoreMatrixModal.test.tsx`: Verifica renderizado de matriz, tooltips, accuracy section.
- `PreMatchPrediction.test.tsx`: Verifica que el botón abre el modal.

## Migration Strategy

No requiere migración de base de datos. Los campos nuevos son opcionales y se calculan on-the-fly. Retrocompatibilidad garantizada.

## Risks & Mitigations

| Risk | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Performance query accuracy history | Media | Medio | Cachear por league_id en memoria (TTL 5 min) |
| Matriz 6x6 muy densa en mobile | Baja | Bajo | Scroll horizontal + celdas compactas |
| xG contribution contraintuitive | Media | Bajo | Mostrar tooltip explicativo "Contribución ofensiva" |
| MongoDB query lenta en ligas con muchos partidos | Media | Medio | Limitar query a últimos 100 partidos; índice en league_id |
