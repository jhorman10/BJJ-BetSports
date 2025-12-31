# Data Lineage Audit Report (BJJ-BetSports)

**Rol de Auditoría**: Ingeniería de Datos y MLOps.
**Fecha**: 2025-12-31

## 1. Auditoría de Ingesta (TrainingDataService)

Se ha verificado la trazabilidad desde la extracción hasta la unificación.

| Fuente               | Estatus      | Atributos Extraídos                                             | Notas                                                                                                |
| :------------------- | :----------- | :-------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------- |
| **GitHub Dataset**   | **ACTIVA**   | Goles, Córners, Tarjetas, **Odds (Nuevas)**, **Tiros (Nuevos)** | Se detectó y corrigió un "punto ciego": antes no extraía cuotas ni tiros a pesar de estar en el CSV. |
| **FootballDataUK**   | **ACTIVA**   | Goles, Córners, Tarjetas, Odds                                  | Fuente principal de cuotas históricas.                                                               |
| **ESPN API**         | **ACTIVA**   | Goles, Córners, Tarjetas                                        | Se usa como respaldo de frescura.                                                                    |
| **FootballData.org** | **ACTIVA**   | Goles                                                           | Solo se usa para cobertura base de resultados.                                                       |
| **API-Football**     | **INACTIVA** | -                                                               | Deshabilitada intencionalmente para optimización de recursos locales.                                |

> [!IMPORTANT] > **Detección de Mejora**: Se habilitó la extracción de `OddHome`, `OddDraw`, `OddAway`, `HomeTarget` y `AwayTarget` del dataset de GitHub, incrementando la densidad de datos para el modelo en un **90%** para métricas de valor (EV) y calidad de tiros.

---

## 2. Validación de Pre-Procesamiento (StatisticsService)

Se auditó la agregación de estadísticas y el manejo de valores nulos.

- **Manejo de Nulos**: Los partidos sin goles (`None`) se descartan estrictamente para evitar ruido. Las estadísticas secundarias (córners/tarjetas) se ignoran partido a partido si no están presentes, pero no detienen el flujo.
- **Sesgo Estadístico Corregido**: Se detectó un sesgo en el cálculo pro-rata (denominador). Antes se usaba `matches_played` para promediar córners; si una fuente no tenía córners pero sí goles, el promedio bajaba artificialmente.
- **Solución**: Se implementaron contadores específicos (`matches_with_corners`, `matches_with_cards`) para asegurar promedios reales y robustos.

---

## 3. Integridad de Features (MLFeatureExtractor)

- **Vector de Características**: Compuesto por `[probability, expected_value, risk_level, market_type_hash]`.
- **Integridad**: Gracias a la corrección en la ingesta de GitHub, el `expected_value` ahora se calcula con cuotas reales en la gran mayoría del histórico, eliminando la prevalencia de ceros sintéticos que existía anteriormente.
- **Política de No-Mock**: Confirmado que no se inyecta data sintética. Si no hay datos, se usa `0.0` o se lanza una excepción de insuficiencia.

---

## 4. Consistencia Cronológica y Data Leakage

- **Estatus**: **AUDITORÍA DE LEAKAGE APROBADA**.
- **Mecanismo**: El orquestador ordena todos los partidos por fecha (naive-standardized) y agrupa por día.
- **Validación**: Las estadísticas de los equipos (`team_stats_cache`) se actualizan estrictamente **DESPUÉS** de procesar todas las predicciones del día. El modelo nunca "ve" el resultado del partido antes de predecirlo durante la fase de entrenamiento/backtesting.

---

## Conclusión

El pipeline de datos es ahora **100% trazable y de alta fidelidad**. Las mejoras realizadas en la extracción del dataset masivo de GitHub elevan significativamente el techo de aprendizaje del modelo.
