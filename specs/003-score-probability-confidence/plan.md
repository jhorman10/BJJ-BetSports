# Technical Plan: Marcador Tentativo con Distribución de Poisson y Nivel de Confianza

**Feature Branch**: `003-score-probability-confidence`  
**Created**: 2026-08-07  
**Status**: Draft  
**Spec**: `specs/003-score-probability-confidence/spec.md`

## Architecture Context

El proyecto usa **Clean Architecture** con separación clara en `domain`, `application`, `infrastructure`, `api` y `presentation`. La predicción ya tiene:
- Poisson PMF y distribución recursiva en `prediction_service.py`
- Cálculo de xG (`predicted_home_goals`, `predicted_away_goals`)
- Sistema de confianza 0-1 multi-factor
- Esquemas Pydantic y mappers para API
- Componentes React en `frontend/src/presentation/components/MatchCard/` y `MatchDetails/`

## Approach

### Estrategia General
El enfoque es **mínimo e incremental**:
1. Agregar método `calculate_score_probabilities()` en `PredictionService` que usa los xG existentes como λ de Poisson.
2. Agregar método `calculate_score_confidence_tier()` que mapea la confianza existente + entropía de score matrix a Alta/Media/Baja.
3. Integrar ambos métodos en el flujo de generación de predicciones.
4. Exponer en Pydantic schema y mapper.
5. Mostrar en frontend como nueva sección en `PreMatchPrediction.tsx` o pestaña en `SuggestedPicksTab.tsx`.

### Por qué no un nuevo modelo ML
- El usuario pidió Poisson/xG como metodología principal.
- El proyecto ya tiene Poisson implementado y validado.
- Agregar un nuevo modelo de ML para exact score requeriría datos de entrenamiento específicos (historial de marcadores exactos) que no existen hoy.
- Poisson con xG como λ es el estándar de la industria para exact score prediction.

## Technical Decisions

| Decision | Opciones | Elegido | Razón |
|---|---|---|---|
| Cálculo de score matrix | Poisson completo vs top-N heurístico | Poisson completo con top-N cacheado | Poisson es exacto; top-N evita arrays enormes |
| Límite de marcadores | Top 3 vs Top 5 vs Top 10 | Top 5 configurables | Suficiente para UI, performance aceptable |
| Cálculo de confianza | Nueva métrica vs reutilizar existente | Reutilizar `confidence` + entropía | No reinventar; la confianza existente ya considera data quality |
| Cache | Redis vs memoria vs recalcular | Memoria por predicción | Los xG ya están calculados; Poisson es O(n*m) liviano |
| Frontend location | Nueva pestaña vs sección inline | Sección inline en detalle | Mejor UX; el usuario ve el marcador sin cambiar de pestaña |

## Scope

### In Scope
- Backend: método `calculate_score_probabilities()` en `PredictionService`
- Backend: método `calculate_score_confidence_tier()` en `PredictionService`
- Backend: integración en flujo de generación de predicciones
- Backend: actualización de `PredictionModel` schema
- Backend: actualización de `prediction_mapper.py`
- Frontend: sección "Marcador Tentativo" en componente de detalle
- Frontend: badge de confianza (Alta/Media/Baja)
- Tests unitarios para nuevos métodos

### Out of Scope
- Nuevo modelo ML para exact score
- Histórico de marcadores tentativos para comparación
- Notificaciones push cuando el marcador tentativo cambia
- Soporte para múltiples ligas con diferentes formatos de marcador

## Data Model Changes

### Backend Entity (`Prediction`)
```python
@dataclass
class Prediction:
    # ... campos existentes ...
    score_probabilities: Optional[list[dict]] = None  # [{"home_goals": 2, "away_goals": 1, "probability": 0.15}, ...]
    score_confidence_tier: Optional[str] = None  # "Alta" | "Media" | "Baja" | "N/A"
```

### Pydantic Schema (`PredictionModel`)
```python
class ScoreProbability(BaseModel):
    home_goals: int
    away_goals: int
    probability: float

class PredictionModel(BaseModel):
    # ... campos existentes ...
    score_probabilities: Optional[list[ScoreProbability]] = None
    score_confidence_tier: Optional[str] = None
```

### Frontend Interface (`Prediction`)
```typescript
interface ScoreProbability {
  home_goals: number;
  away_goals: number;
  probability: number; // 0-1, se muestra como %
}

interface Prediction {
  // ... campos existentes ...
  score_probabilities?: ScoreProbability[];
  score_confidence_tier?: "Alta" | "Media" | "Baja" | "N/A";
}
```

## Algorithm

### Cálculo de Score Probabilities (Poisson)
```
Para cada home_goals en 0..MAX_GOALS:
  Para cada away_goals en 0..MAX_GOALS:
    p = PoissonPMF(home_goals, λ=predicted_home_goals) * PoissonPMF(away_goals, λ=predicted_away_goals)
    Agregar (home_goals, away_goals, p) al array

Ordenar array por p descendente
Retornar top N (default 5)
```

Donde `PoissonPMF(k, λ) = (e^-λ * λ^k) / k!`

### Cálculo de Confidence Tier
```
entropy = -Σ p_i * log2(p_i) para los top N scores
max_entropy = log2(N)  # entropía máxima teórica
normalized_entropy = entropy / max_entropy  # 0 = un score domina, 1 = todos iguales

sample_quality = confidence_existente  # 0-1, ya considera data quality

# Mapeo:
# - Alta: normalized_entropy < 0.4 Y sample_quality > 0.6
# - Media: (0.4 <= normalized_entropy < 0.7) O (0.3 < sample_quality <= 0.6)
# - Baja: normalized_entropy >= 0.7 O sample_quality <= 0.3
# - N/A: predicted_home_goals o predicted_away_goals es None
```

## API Changes

### Response Schema (extiende `PredictionModel`)
```json
{
  "match_id": "123",
  "home_win_probability": 0.45,
  "predicted_home_goals": 1.8,
  "predicted_away_goals": 1.2,
  "score_probabilities": [
    {"home_goals": 2, "away_goals": 1, "probability": 0.1523},
    {"home_goals": 1, "away_goals": 1, "probability": 0.1287},
    {"home_goals": 2, "away_goals": 0, "probability": 0.1105}
  ],
  "score_confidence_tier": "Alta"
}
```

### Endpoints afectados
- `GET /api/v1/predictions/league/{league_id}` — ahora incluye `score_probabilities` y `score_confidence_tier` en cada predicción.
- `GET /api/v1/predictions/match/{match_id}` — mismos campos nuevos.
- No se agregan endpoints nuevos; se extienden los existentes.

## Frontend Changes

### Componentes a modificar
1. **`PreMatchPrediction.tsx`**: Agregar sección "Marcador Tentativo" debajo de las probabilidades 1X2.
2. **`MatchCard.tsx`**: Mostrar badge de confianza en la tarjeta de predicción.
3. **`predictionUtils.ts`**: Agregar helper `formatScoreProbability()` para mostrar "2-1 (15.2%)".

### UX Decisions
- Top 3-5 marcadores mostrados como pills/badges: `2-1 15.2%`
- Badge de confianza con color: 🟢 Alta, 🟡 Media, 🔴 Baja, ⚪ N/A
- Orden: más probable primero
- Si `score_probabilities` está vacío, mostrar "No disponible" en gris

## Testing Strategy

### Unit Tests (Backend)
- `test_score_probabilities_basic`: Verifica que la suma de probabilidades de top-N es razonable.
- `test_score_probabilities_most_probable_first`: Verifica orden descendente.
- `test_score_probabilities_symmetric`: Verifica que P(2-1) ≈ P(1-2) cuando λ_home ≈ λ_away.
- `test_score_confidence_tier_alta`: Verifica mapeo a "Alta" con baja entropía.
- `test_score_confidence_tier_baja`: Verifica mapeo a "Baja" con alta entropía.
- `test_score_probabilities_no_xg`: Verifica retorno de [] y "N/A" cuando no hay xG.

### Integration Tests
- Verificar que el endpoint `/api/v1/predictions/match/{id}` incluye los nuevos campos.
- Verificar que el mapper convierte correctamente `score_probabilities` desde MongoDB.

### Frontend Tests
- Verificar que `PreMatchPrediction` renderiza la sección "Marcador Tentativo".
- Verificar que el badge de confianza muestra el texto correcto.

## Migration Strategy

No requiere migración de base de datos. Los campos nuevos son opcionales y se calculan on-the-fly durante la generación de predicciones. Las predicciones existentes en MongoDB sin estos campos mostrarán "N/A" hasta que se re-generen.

## Risks & Mitigations

| Risk | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Performance degradation en ligas con muchos partidos | Media | Medio | Cachear score_probabilities por predicción; MAX_GOALS=8 limita el cálculo a 81 combinaciones máx |
| Valores de xG muy bajos/históricos generan scores poco realistas | Media | Bajo | Clamp λ a mínimo 0.3 para evitar underflow; loguear warning |
| Frontend no tiene espacio para nueva sección | Baja | Bajo | Usar collapse/expand si es necesario; sección compacta |
| Retrocompatibilidad con clientes API antiguos | Baja | Medio | Campos opcionales en schema; versionado no requerido |
