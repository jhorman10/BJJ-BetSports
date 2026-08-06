# Feature Specification: Entrenamiento On-Demand desde la Web y Ejecucion Agnostica de Modelo

**Feature Branch**: `[001-web-on-demand-ai-training]`  
**Created**: 2026-05-04  
**Status**: Draft  
**Input**: User description: "Necesito poder entrenar el modelo en el momento que quiera desde la aplicacion web, genera un spec super detallado para poder hacer la ejecucion con cualquier modelo de IA"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Lanzar y seguir un entrenamiento real desde la web (Priority: P1)

Como operador autorizado, quiero iniciar un entrenamiento desde la aplicacion web y seguir su estado por `job_id`, incluso cuando el API esta desplegado separado del runtime de entrenamiento, para no depender de ejecucion pesada dentro del proceso web.

**Why this priority**: Sin este slice no existe valor operacional real. El problema actual es justamente que el trigger web esta acoplado al proceso del API.

**Independent Test**: Puede probarse creando un job desde la UI o API, verificando que el sistema responde con `job_id`, persiste el snapshot del pedido y expone estados/progreso sin entrenar dentro del request lifecycle.

**Acceptance Scenarios**:

1. **Given** un operador autenticado, un modelo habilitado y un ejecutor disponible, **When** crea un entrenamiento manual, **Then** el sistema devuelve un `job_id` estable, registra la receta usada y deja el job en un estado inicial observable.
2. **Given** que el backend web esta desplegado separado del runtime de entrenamiento, **When** el operador crea un entrenamiento manual, **Then** el sistema acepta y registra el job sin ejecutar el entrenamiento pesado dentro del proceso web.
3. **Given** que el ejecutor elegido deja de estar disponible, **When** el operador intenta crear el job, **Then** la respuesta explica por que no puede ejecutarse y la UI muestra una razon accionable en lugar de un error generico.

---

### User Story 2 - Elegir modelo, receta y ejecutor desde un catalogo de capacidades (Priority: P2)

Como operador autorizado, quiero elegir desde la web que modelo entrenar, con que preset y sobre que ejecutor, para que la plataforma no quede acoplada a un solo stack de IA ni a una unica forma de ejecucion.

**Why this priority**: El boton de entrenamiento solo escala si el backend publica capacidades reales. Sin este catalogo, cada modelo nuevo obligaria a tocar endpoints y UI a mano.

**Independent Test**: Puede probarse consultando `capabilities`, abriendo el formulario web y verificando que solo se permiten combinaciones validas de modelo, receta, ligas y ejecutor.

**Acceptance Scenarios**:

1. **Given** un catalogo de capacidades publicado por backend, **When** el operador abre el formulario de entrenamiento, **Then** la UI muestra modelos, presets, restricciones y ejecutores realmente soportados.
2. **Given** una combinacion invalida de modelo y ejecutor, **When** el operador intenta enviarla, **Then** el sistema rechaza la solicitud con una razon clara y sin crear el job.
3. **Given** que se registra un segundo adaptador de modelo, **When** el operador consulta capacidades, **Then** puede seleccionarlo usando el mismo contrato sin requerir un endpoint publico nuevo.

---

### User Story 3 - Promover un artefacto entrenado de forma explicita y auditable (Priority: P3)

Como operador autorizado, quiero revisar artefactos candidatos y promover uno como modelo activo en una accion separada, para no mezclar entrenamiento con publicacion productiva.

**Why this priority**: Entrenar y publicar son decisiones distintas. Si el sistema activa automaticamente un resultado nuevo, el riesgo operativo y de regresion sube demasiado.

**Independent Test**: Puede probarse completando un job, verificando que el artefacto queda como candidato y ejecutando luego una promocion separada con auditoria y validacion de permisos.

**Acceptance Scenarios**:

1. **Given** un job completado con un artefacto valido, **When** un operador con permiso de promocion lo promueve, **Then** el modelo activo se actualiza y la accion queda auditada con usuario, fecha y origen.
2. **Given** un job fallido, cancelado o sin artefacto publicable, **When** alguien intenta promover su resultado, **Then** el sistema rechaza la accion y conserva intacto el modelo activo actual.
3. **Given** un job ya completado, **When** un operador solicita retry o cancel segun corresponda, **Then** el sistema solo permite transiciones validas y deja trazabilidad completa de la decision.

### Edge Cases

- Que ocurre si existe un job equivalente en progreso para la misma receta, modelo y scope operativo?
- Como se comporta el sistema si el API se reinicia mientras un ejecutor externo sigue trabajando?
- Que pasa si el ejecutor reporta `COMPLETED` pero no produce un artefacto compatible con el contrato de metricas?
- Como se informa una incapacidad temporal cuando hay modelos registrados pero ningun ejecutor saludable?
- Que sucede si un usuario puede leer el estado de entrenamiento pero no tiene permiso para crear, cancelar o promover?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST publicar un catalogo de capacidades que incluya modelos disponibles, ejecutores disponibles, presets compatibles, restricciones de combinacion y razones de indisponibilidad.
- **FR-002**: El sistema MUST permitir que operadores autorizados creen jobs de entrenamiento manual desde la web usando un contrato validado y versionado.
- **FR-003**: El sistema MUST responder a cada solicitud aceptada con un `job_id` estable que permita consultar el ciclo de vida completo del entrenamiento.
- **FR-004**: El sistema MUST ejecutar el entrenamiento fuera del request lifecycle del API y fuera del proceso web cuando el despliegue del backend web este separado del runtime de entrenamiento.
- **FR-005**: El sistema MUST persistir para cada job un snapshot de la receta pedida, estado canonico, fase, progreso, timestamps, errores, resumen de logs y referencias al ejecutor.
- **FR-006**: El sistema MUST exponer consulta por job individual, historial de jobs y timeline de eventos para que la UI pueda mostrar progreso y diagnostico.
- **FR-007**: El sistema MUST soportar `retry` y `cancel` solo para estados compatibles y registrar la razon operativa de cada accion.
- **FR-008**: El sistema MUST separar el registro de modelos del registro de ejecutores para que agregar un nuevo modelo no requiera endpoints publicos nuevos.
- **FR-009**: El sistema MUST validar `model_key`, `executor_target`, `league_ids`, `days_back`, `feature_profile`, `hyperparameter_profile` y `publish_strategy` contra capacidades permitidas antes de crear un job.
- **FR-010**: El sistema MUST registrar al menos un artefacto candidato por job exitoso con metadata de metricas, version de contrato y provenance suficiente para auditoria.
- **FR-011**: El sistema MUST mantener separado el estado de artefacto candidato del puntero de modelo activo.
- **FR-012**: El sistema MUST requerir una accion explicita de promocion para activar un nuevo modelo y MUST impedir promociones automaticas implcitas al finalizar un entrenamiento.
- **FR-013**: El sistema MUST exigir autenticacion y autorizacion explicitas para `training:read`, `training:write` y `training:promote`, sin depender de bypass por loopback.
- **FR-014**: El sistema MUST devolver codigos de razon y mensajes accionables cuando un job no puede crearse o un ejecutor/modelo no esta disponible.
- **FR-015**: El sistema MUST ofrecer una estrategia de compatibilidad para el trigger manual legacy de entrenamiento y sus consultas relacionadas hasta completar la migracion del dashboard actual.
- **FR-016**: El sistema MUST registrar auditoria para crear, reintentar, cancelar y promover jobs o artefactos.
- **FR-017**: El sistema MUST operar con el mismo contrato externo aunque el ejecutor real sea local controlado, despachado desde integracion continua o un worker dedicado futuro.

### Key Entities *(include if feature involves data)*

- **TrainingRecipe**: Intencion de entrenamiento validada, con modelo objetivo, scope de datos, perfiles de features e hiperparametros, destino de ejecucion y estrategia de publicacion.
- **TrainingJob**: Ejecucion concreta de una receta, con `job_id`, estado, fase, progreso, timestamps, resumen de error, referencias al ejecutor y trazabilidad operativa.
- **ModelAdapterDefinition**: Declaracion del contrato de un modelo entrenable, incluyendo `model_key`, perfiles soportados, schema de metricas, formato de artefacto y compatibilidad de inferencia.
- **ExecutorDefinition**: Declaracion del backend de ejecucion disponible, incluyendo tipo, estado de salud, restricciones operativas y capacidades observables.
- **ModelArtifact**: Resultado versionado de un job exitoso, con metadata de metricas, provenance, compatibilidad y estado de publicacion.
- **ActiveModelPointer**: Referencia auditable al artefacto actualmente activo para un scope concreto de inferencia.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las solicitudes aceptadas de entrenamiento manual devuelven un `job_id` y quedan en estado observable inicial en menos de 2 segundos.
- **SC-002**: En despliegues donde el backend web esta separado del runtime de entrenamiento, iniciar un entrenamiento manual no requiere ejecutar el pipeline dentro del proceso del API.
- **SC-003**: La plataforma puede registrar y lanzar al menos dos adaptadores de modelo distintos usando el mismo contrato de creacion de jobs y los mismos endpoints publicos.
- **SC-004**: Ningun entrenamiento activa automaticamente un modelo nuevo; toda activacion ocurre unicamente mediante una accion explicita de promocion.
- **SC-005**: Un operador autorizado puede distinguir desde API/UI si un entrenamiento esta bloqueado, en cola, corriendo, fallido, cancelado o completado sin inspeccionar logs del servidor.
- **SC-006**: Cada accion de crear, cancelar, reintentar o promover deja trazabilidad consultable con actor, timestamp y objetivo afectado.

## Assumptions

- La autenticacion administrativa existente puede endurecerse para introducir permisos explicitos de lectura, escritura y promocion de entrenamiento.
- El pipeline actual de entrenamiento puede reutilizarse como primer adaptador de modelo durante la migracion.
- El primer ejecutor formal puede apoyarse en un entorno local controlado o en un despachador basado en integracion continua, pero el contrato debe seguir siendo intercambiable.
- La metadata de jobs y artefactos puede persistirse separada del binario pesado del modelo, que podria vivir en almacenamiento distinto.