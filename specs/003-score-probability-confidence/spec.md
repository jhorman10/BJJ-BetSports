# Feature Specification: Marcador Tentativo con Distribución de Poisson y Nivel de Confianza

**Feature Branch**: `003-score-probability-confidence`  
**Created**: 2026-08-07  
**Status**: Draft  
**Input**: User description: "Incorpora una nueva sección titulada 'Marcador Tentativo' en las predicciones de cada partido. Utiliza modelos estadísticos avanzados (como la distribución de Poisson o el análisis de goles esperados - xG) para calcular el marcador más probable de cada encuentro. Además, investiga y aplica las metodologías de predicción más precisas disponibles para determinar un nivel de confianza (expresado en porcentaje o escala cualitativa) que acompañe a cada resultado propuesto, basándote en la fiabilidad estadística del modelo empleado."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Visualizar marcador tentativo en detalle del partido (Priority: P1)

Como usuario de la aplicación, quiero ver una sección "Marcador Tentativo" en el detalle de cada partido que muestre los 3-5 marcadores exactos más probables con su porcentaje de probabilidad, para poder evaluar el riesgo de la predicción.

**Why this priority**: Es el core del feature pedido. Sin esta visualización, no existe el "Marcador Tentativo".

**Independent Test**: Abrir el detalle de cualquier partido con predicciones y verificar que aparece la sección "Marcador Tentativo" con al menos 3 marcadores ordenados por probabilidad descendente.

**Acceptance Scenarios**:

1. **Given** un partido con predicciones generadas, **When** el usuario abre el detalle del partido, **Then** aparece una sección "Marcador Tentativo" con los marcadores más probables y sus probabilidades.
2. **Given** la sección "Marcador Tentativo", **When** el usuario observa los resultados, **Then** los marcadores están ordenados de mayor a menor probabilidad.
3. **Given** un partido sin datos suficientes, **When** el sistema no puede calcular la distribución, **Then** se muestra un mensaje informativo indicando que el marcador tentativo no está disponible.

---

### User Story 2 - Nivel de confianza cualitativo acompañando al marcador (Priority: P1)

Como usuario, quiero ver un nivel de confianza (Alta/Media/Baja) junto al marcador tentativo, para entender qué tan fiable es esa predicción estadística.

**Why this priority**: El usuario pidió explícitamente un nivel de confianza basado en la fiabilidad estadística del modelo. Es parte del requerimiento principal.

**Independent Test**: Verificar que cada marcador tentativo incluye un badge/indicador de confianza (Alta/Media/Baja) derivado de la confiabilidad del modelo Poisson/xG.

**Acceptance Scenarios**:

1. **Given** un marcador tentativo calculado, **When** se muestra al usuario, **Then** incluye un nivel de confianza (Alta/Media/Baja) basado en la entropía de la distribución de Poisson y la cantidad de datos históricos.
2. **Given** un modelo con alta entropía (probabilidades muy distribuidas), **When** se calcula la confianza, **Then** el nivel es "Baja".
3. **Given** un modelo con baja entropía (un marcador domina claramente), **When** se calcula la confianza, **Then** el nivel es "Alta".

---

### User Story 3 - Integración backend del cálculo de score probabilities (Priority: P1)

Como sistema, necesito calcular la distribución completa de marcadores usando Poisson con los parámetros de xG existentes, para exponer los marcadores más probables en la API.

**Why this priority**: Sin el backend que expone los datos, el frontend no puede mostrar nada.

**Independent Test**: Llamar al endpoint de predicciones y verificar que el JSON incluye `score_probabilities` con al menos 3 marcadores ordenados y `score_confidence_tier`.

**Acceptance Scenarios**:

1. **Given** una predicción con `predicted_home_goals` y `predicted_away_goals`, **When** se genera la respuesta de API, **Then** incluye `score_probabilities` array con objetos `{home_goals, away_goals, probability}`.
2. **Given** el array de score probabilities, **When** se ordena por probabilidad, **Then** el primer elemento es el marcador más probable.
3. **Given** una predicción existente, **When** se consulta el endpoint, **Then** incluye `score_confidence_tier` con valores "Alta", "Media" o "Baja".

---

### User Story 4 - Actualización del modelo de datos y esquemas (Priority: P2)

Como desarrollador, necesito que los schemas de Pydantic y las entidades frontend incluyan los nuevos campos, para mantener tipado fuerte en toda la cadena.

**Why this priority**: Necesario para type-safety, pero no bloquea el feature si se hace en paralelo.

**Independent Test**: Verificar que los schemas Pydantic y las interfaces TypeScript compilan sin errores con los nuevos campos.

**Acceptance Scenarios**:

1. **Given** el schema `PredictionModel`, **When** se agrega `score_probabilities`, **Then** el schema valida correctamente el array de objetos.
2. **Given** la interfaz TypeScript `Prediction`, **When** se agrega `score_probabilities`, **Then** el frontend compila sin errores de tipo.

---

### Edge Cases

- **Qué pasa cuando no hay datos suficientes**: Si `predicted_home_goals` o `predicted_away_goals` son `None` o muy cercanos a 0, el sistema debe retornar `score_probabilities: []` y `score_confidence_tier: "N/A"`.
- **Manejo de error en cálculo Poisson**: Si el cálculo de Poisson falla por valores extremos, se debe fallback a un array vacío y loguear el error.
- **Performance con muchos partidos**: El cálculo de Poisson por partido es O(n*m) donde n,m son los goles esperados. Para ligas con muchos partidos, se debe cachear el resultado.
- **Compatibilidad con versiones anteriores**: Los campos nuevos son opcionales en el schema Pydantic y en TypeScript, por lo que clientes antiguos no se rompen.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El backend DEBE calcular `score_probabilities` como array de objetos `{home_goals: number, away_goals: number, probability: number}` ordenado por probabilidad descendente, usando distribución de Poisson con parámetros `predicted_home_goals` y `predicted_away_goals`.
- **FR-002**: El backend DEBE exponer `score_confidence_tier` en el schema de predicción, con valores posibles `"Alta"`, `"Media"`, `"Baja"` o `"N/A"`.
- **FR-003**: El backend DEBE calcular `score_confidence_tier` basándose en: (a) entropía de la distribución de Poisson, (b) cantidad de muestras históricas, (c) calidad de datos de xG.
- **FR-004**: El frontend DEBE mostrar una sección "Marcador Tentativo" en el detalle del partido con los top 3-5 marcadores y su probabilidad.
- **FR-005**: El frontend DEBE mostrar un badge de confianza (Alta/Media/Baja) junto a cada marcador tentativo.
- **FR-006**: Los schemas Pydantic DEBEN marcar `score_probabilities` y `score_confidence_tier` como opcionales para mantener retrocompatibilidad.
- **FR-007**: Las interfaces TypeScript DEBEN marcar los nuevos campos como opcionales (`?`) para mantener retrocompatibilidad.
- **FR-008**: El sistema DEBE reutilizar los parámetros de xG existentes (`predicted_home_goals`, `predicted_away_goals`) sin recalcularlos.

### Key Entities *(include if feature involves data)*

- **Prediction (backend entity)**: Entidad de predicción existente. Se agregan campos opcionales: `score_probabilities: list[dict]` y `score_confidence_tier: Optional[str]`.
- **PredictionModel (Pydantic schema)**: Schema de respuesta API. Se agregan campos opcionales: `score_probabilities` y `score_confidence_tier`.
- **Prediction (frontend interface)**: Interfaz TypeScript. Se agregan campos opcionales: `score_probabilities?: ScoreProbability[]` y `score_confidence_tier?: string`.
- **ScoreProbability (nuevo)**: DTO con `home_goals: number`, `away_goals: number`, `probability: number`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las predicciones con `predicted_home_goals` y `predicted_away_goals` definidos incluyen `score_probabilities` con al menos 3 marcadores.
- **SC-002**: El tiempo de generación de predicciones no aumenta más del 5% al incluir el cálculo de score probabilities.
- **SC-003**: El frontend muestra la sección "Marcador Tentativo" en el 100% de los detalles de partido donde existen predicciones.
- **SC-004**: Los tests unitarios existentes siguen pasando al 100% (regression zero).
- **SC-005**: La cobertura de tests para el nuevo cálculo de Poisson/score probabilities es >= 80%.

## Assumptions

- **Assumption**: Los parámetros `predicted_home_goals` y `predicted_away_goals` (xG) ya están calculados por el modelo existente y son confiables como entrada para Poisson.
- **Assumption**: El frontend actual tiene capacidad de mostrar una sección adicional en el detalle del partido sin refactor mayor.
- **Assumption**: El nivel de confianza se calcula en backend y se envía al frontend como string ("Alta"/"Media"/"Baja"/"N/A"), no como número.
- **Assumption**: No se requieren cambios en la base de datos MongoDB porque los campos nuevos son opcionales y se calculan on-the-fly o se almacenan en el documento existente de predicción.
- **Assumption**: El modelo de Poisson existente (`_get_poisson_distribution`, `poisson_probability`) es suficientemente preciso para calcular probabilidades de marcador exacto.
