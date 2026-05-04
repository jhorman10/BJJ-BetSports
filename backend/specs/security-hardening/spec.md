---
title: Cierre de Gaps de Seguridad Full-Stack
author: GitHub Copilot
date: 2026-04-29
status: proposed
tags: [security, backend, frontend, platform, hardening]
---

Resumen ejecutivo
-----------------
Esta especificación define una intervención transversal para cerrar los gaps de
seguridad verificados en la aplicación: bypass administrativo por host,
poisoning anónimo del aprendizaje, exposición innecesaria de superficies
operativas, defaults inseguros de base de datos, embebidos externos sin
restricciones suficientes y persistencia/cache excesiva de datos en el cliente.

El objetivo no es "mejorar seguridad" de forma abstracta, sino convertir estas
superficies en límites explícitos, verificables y cerrados por defecto. La
intervención debe dejar evidencia técnica de cierre mediante tests de regresión,
configuración fail-closed y documentación operativa alineada con el runtime.

Contexto y motivación
---------------------
- La auditoría read-only del 2026-04-29 confirmó gaps reales y explotables en
  backend, frontend y configuración.
- El proyecto ya dispone de un gate de calidad full-stack verde, pero no existe
  aún un baseline de seguridad equivalente que impida regresiones obvias.
- Varios de los riesgos actuales no dependen de un atacante sofisticado, sino de
  callers anónimos, errores de configuración o datos externos no confiables.
- Subir código con estos gaps abiertos mantiene una deuda operativa innecesaria
  sobre rutas sensibles, estado persistente y despliegue.

Modelo de amenaza y activos a proteger
--------------------------------------

Actores de amenaza considerados
-------------------------------
- Caller anónimo desde Internet contra rutas públicas del backend.
- Caller desde red local o entorno de desarrollo mal aislado que puede alcanzar
  rutas administrativas.
- Usuario legítimo del frontend que recibe datos externos o URLs no confiables.
- Proveedor externo o feed comprometido que devuelve contenido inesperado.
- Operador que despliega con variables incompletas o defaults inseguros.
- Futuras iteraciones del producto que añadan endpoints más sensibles bajo rutas
  ya cacheadas o expuestas hoy.

Activos y propiedades a preservar
---------------------------------
- Integridad de las rutas administrativas y de entrenamiento.
- Integridad de `LearningWeights` y del feedback que ajusta sugerencias.
- Confidencialidad de detalles internos de infraestructura, DSN y errores.
- Integridad de la capa de persistencia Mongo/PostgreSQL.
- Confianza del cliente al abrir media o navegación externa.
- Privacidad de datos funcionales persistidos en navegador y service worker.

Fronteras de confianza
----------------------
- Browser `frontend/` <-> backend FastAPI `backend/src/api/`
- Backend <-> MongoDB / PostgreSQL
- Backend <-> proveedores externos (Football-Data, ESPN, odds, etc.)
- Frontend <-> URLs externas de highlights / embebidos
- Frontend <-> localStorage / IndexedDB / service worker cache
- Configuración del repo <-> entorno real de despliegue (Render, Docker local)

Gaps verificados y estrategia de cierre
---------------------------------------

1. Bypass administrativo por host local
---------------------------------------
Severidad: Alta

Evidencia verificada
- `backend/src/api/security.py`
- `backend/src/api/main.py`
- `backend/src/api/routers/labeler.py`
- `backend/src/api/routers/monitor.py`
- `backend/tests/unit/test_api_admin_security.py`

Problema
- La autorización administrativa depende hoy de un bypass por host loopback y de
  `API_ONLY_MODE`, no exclusivamente de autenticación explícita.
- Ese diseño convierte una excepción de desarrollo en comportamiento de runtime.
- El mismo guard protege rutas que disparan entrenamiento, backlog y labeler.

Impacto
- Una mala configuración o un entorno parcialmente expuesto puede ejecutar
  operaciones administrativas sin identidad real.
- La seguridad queda acoplada a topología/red en vez de a credenciales.

Dirección de cierre
- Eliminar el bypass por host del runtime productivo.
- Separar explícitamente los modos `test/dev-only` de las dependencias reales de
  auth, sin que el servidor los active por defecto.
- Exigir credencial siempre para rutas administrativas, incluso en local, salvo
  harnesses de test controlados.

2. Feedback anónimo con efecto persistente en aprendizaje
---------------------------------------------------------
Severidad: Alta

Evidencia verificada
- `backend/src/api/routers/picks.py`
- `backend/src/application/use_cases/suggested_picks_use_case.py`
- `backend/src/domain/services/learning_service.py`

Problema
- `POST /api/v1/suggested-picks/feedback` acepta escritura anónima.
- El payload actual actualiza pesos persistidos que influyen en sugerencias
  futuras y puede observarse por `GET /learning-stats`.
- No existe validación suficiente para garantizar que el feedback proviene de una
  fuente confiable ni que corresponde a un partido/mercado coherente.

Impacto
- Caller anónimo puede degradar la integridad del sistema de aprendizaje.
- El modelo de picks queda expuesto a poisoning intencional o ruido masivo.

Dirección de cierre
- Proteger feedback y learning stats con auth explícita.
- Introducir validaciones de coherencia del payload y del `match_id`.
- Aplicar rate limit y auditoría de escrituras.
- Mantener como mínimo un camino seguro con API keys internas hasta que exista
  identidad de usuario final real.

3. Superficie operativa pública y fuga de errores internos
----------------------------------------------------------
Severidad: Alta-Media

Evidencia verificada
- `backend/src/api/main.py`
- `backend/src/api/routers/monitor.py`
- `backend/src/api/routers/metrics.py`
- `backend/src/infrastructure/database/database_service.py`

Problema
- La app expone docs/OpenAPI por defecto, `/_ready`, rutas de monitor y métricas.
- Algunas respuestas devuelven texto crudo de excepción.
- El servicio de base de datos loggea suficiente información para reconstruir
  host o partes sensibles del DSN.

Impacto
- Aumenta el fingerprinting de infraestructura y la capacidad de enumeración.
- Ayuda a un atacante a entender dependencias, nombres de servicios y fallos.

Dirección de cierre
- Minimizar endpoints operativos públicos al subconjunto estrictamente necesario.
- Desactivar docs en despliegues expuestos a Internet.
- Sanitizar respuestas y logs con `error_id` o mensajes opacos.
- Mover detalles técnicos solo a logs sanitizados y observabilidad interna.

4. Configuración Mongo insegura y no fail-closed
------------------------------------------------
Severidad: Media

Evidencia verificada
- `backend/src/infrastructure/repositories/mongo_repository.py`
- `backend/src/infrastructure/repositories/async_mongo_repository.py`
- `backend/src/infrastructure/repositories/async_mongo_adapter.py`
- `docker-compose.dev.yml`
- `backend/.env.example`
- `backend/README.md`

Problema
- Persisten fallbacks a `admin/adminpassword@localhost` en varios code paths.
- Docker local publica Mongo con credenciales predecibles y privilegio alto.
- No todos los paths fallan cerrado cuando falta `MONGO_URI`.

Impacto
- Errores de configuración terminan en credenciales conocidas y comportamiento
  implícito en vez de detener el proceso.
- Se normaliza un contrato de seguridad débil en docs y tooling local.

Dirección de cierre
- Exigir `MONGO_URI` explícito en todos los repositorios/adapters.
- Eliminar credenciales hardcoded del runtime.
- Endurecer Docker local para no publicar Mongo al host salvo necesidad
  explícita y para evitar root credentials predecibles.

5. Media externa sin política de confianza en frontend
------------------------------------------------------
Severidad: Media

Evidencia verificada
- `frontend/src/presentation/components/MatchDetails/MatchDetailsModal.tsx`
- `frontend/src/presentation/components/MatchCard/MatchCard.tsx`
- `frontend/src/presentation/components/MatchDetails/components/PreMatchPrediction.tsx`
- `frontend/index.html`

Problema
- El frontend navega o embebe `highlights_url` sin allowlist de host, sin
  validación estricta de esquema y sin sandbox suficiente en `iframe`.
- Tampoco existe hoy una CSP base en el HTML de entrada.

Impacto
- Un backend, cache o proveedor comprometido puede hacer que el cliente abra o
  embeba contenido externo inesperado.
- El navegador queda más expuesto a ataques de navegación cruzada, tabnabbing o
  contenidos maliciosos embebidos.

Dirección de cierre
- Introducir una política única de URLs externas seguras.
- Aceptar solo `https` y hosts aprobados.
- Añadir `rel="noopener noreferrer"`, `sandbox`, `referrerPolicy` y fallback de
  renderizado si la URL no pasa validación.
- Añadir CSP explícita y alinearla con los dominios realmente necesarios.

6. Persistencia y cache del cliente demasiado amplias
-----------------------------------------------------
Severidad: Media-Baja

Evidencia verificada
- `frontend/src/application/stores/useParleyStore.ts`
- `frontend/src/application/stores/usePredictionStore.ts`
- `frontend/src/application/stores/useBotStore.ts`
- `frontend/src/infrastructure/storage/indexedDBStorage.ts`
- `frontend/vite.config.ts`

Problema
- El navegador persiste estado funcional de negocio en localStorage/IndexedDB.
- Workbox cachea de forma genérica cualquier `GET` bajo `/api`.
- La retención no está clasificada por sensibilidad, TTL o justificación.

Impacto
- Dispositivos compartidos o comprometidos pueden recuperar más información de la
  necesaria.
- Endpoints futuros podrían quedar cacheados por una regla demasiado amplia.

Dirección de cierre
- Clasificar datos persistibles versus volátiles.
- Mantener en storage solo preferencias inocuas y estado realmente necesario.
- Reducir la cache PWA a endpoints explícitamente aprobados y excluir superficies
  operativas o sensibles.

Alcance (in-scope)
------------------
- Auth y autorización de rutas administrativas y operativas en backend.
- Protección del feedback y learning stats contra escritura anónima.
- Rate limiting y límites de abuso para rutas costosas o sensibles.
- Sanitización de errores y reducción de superficies públicas.
- Hardening de configuración Mongo y secretos locales/de despliegue.
- Política de URLs externas seguras en frontend.
- CSP y hardening de enlaces/iframes externos.
- Clasificación de persistencia local y service worker caching.
- Tests de regresión de seguridad para garantizar cierre sostenido.
- Documentación operativa alineada con el comportamiento final.

Fuera de alcance (out-of-scope)
-------------------------------
- Introducir un sistema completo de identidad de usuario final con cuentas,
  sesiones, RBAC y recuperación de credenciales.
- Reemplazar en esta iteración todos los proveedores externos por agregación
  server-side propia.
- Hacer un pentest exhaustivo de dependencias de terceros o supply chain.
- Diseñar un WAF, mTLS, zero trust o segmentación completa de red productiva.
- Reescribir por completo la arquitectura PWA o de almacenamiento offline.

Requisitos y criterios de aceptación
------------------------------------
- Ninguna ruta administrativa devuelve `200` sin credencial válida.
- El backend no depende de topología de red para decidir privilegios.
- `POST /api/v1/suggested-picks/feedback` deja de aceptar escritura anónima.
- Feedback inválido o incoherente es rechazado antes de persistirse.
- Endpoints operativos no devuelven `str(exc)` ni detalles internos del DSN.
- Docs/OpenAPI quedan desactivados en despliegues expuestos, salvo habilitación
  explícita controlada.
- Los repositorios Mongo fallan cerrado cuando falta configuración requerida.
- El frontend rechaza URLs externas no aprobadas y los embeds quedan sandboxed.
- La PWA no cachea de forma genérica todo `/api`.
- El navegador no persiste datos funcionales sensibles o de alto valor sin una
  decisión explícita y justificada.
- Existen tests backend/frontend que fallan si estos gaps reaparecen.

Diseño propuesto
----------------

Decisión 1: Auth explícita y sin bypass implícito
-------------------------------------------------
- `require_admin_key` dejará de depender de `client.host` como criterio de
  autorización en runtime.
- La necesidad de desarrollo local se resolverá con uno de estos patrones:
  - dependencia alternativa solo para tests,
  - env flag estrictamente de test no cargado en runtime normal,
  - API key local explícita generada por entorno.
- No se aceptará un bypass silencioso ligado a loopback.

Decisión 2: Privilegios mínimos por tipo de endpoint
----------------------------------------------------
- No todo debe colgar del mismo nivel de privilegio.
- Se definen al menos tres categorías:
  - admin mutation: train, labeler, operaciones que mutan estado operativo,
  - ops read: readiness/monitor/metrics si siguen existiendo,
  - feedback write: mientras no haya auth de usuario, se trata como escritura
    privilegiada y no pública.
- La solución mínima aceptable puede reutilizar API keys, pero con separación de
  responsabilidad y sin sobreexponer `ADMIN_API_KEY` donde no haga falta.

Decisión 3: Superficie pública mínima
-------------------------------------
- `GET /health` permanece como endpoint público de vida.
- `/_ready`, monitor, métricas y docs deben:
  - quedar protegidos,
  - o quedar apagados,
  - o moverse a exposición solo interna.
- No se aceptan respuestas con excepciones crudas hacia el cliente.

Decisión 4: Configuración fail-closed
-------------------------------------
- Mongo y PostgreSQL deben fallar si la configuración requerida no existe.
- Se eliminan defaults ejecutables con credenciales conocidas del runtime.
- Los archivos de ejemplo/documentación usarán placeholders o valores no
  privilegiados explícitamente locales, nunca root credentials asumidas.

Decisión 5: Frontera externa segura en frontend
-----------------------------------------------
- Se centraliza una utilidad para validar URLs externas.
- Solo se permiten esquemas y hosts aprobados.
- Todo `iframe` externo se monta con restricciones explícitas.
- La app define CSP base y headers/hardening consistentes con esa política.

Decisión 6: Persistencia mínima del cliente
-------------------------------------------
- Todo estado persistido se clasifica en:
  - preferencias de UX persistibles,
  - estado funcional de negocio no persistible,
  - cache temporal con TTL controlado.
- Workbox deja de usar una regla catch-all para `/api`.
- Los datos persistidos deben tener motivo explícito, TTL y mecanismo de purge.

Plan de implementación (alto nivel)
-----------------------------------
1. Contención inmediata de rutas críticas y feedback.
2. Cierre del bypass admin y endurecimiento de auth/rate limiting.
3. Reducción de exposición operativa y sanitización de errores.
4. Eliminación de defaults inseguros y contracto fail-closed de Mongo.
5. Hardening frontend para media externa, CSP y persistencia local.
6. Tests de regresión y documentación de cierre.

Riesgos y mitigaciones
----------------------
- Riesgo: cerrar feedback anónimo afecte una funcionalidad de producto existente.
  - Mitigación: definir primero un modo seguro mínimo con credencial interna o
    feature flag, y luego evolucionar a auth de usuario real si el producto lo
    exige.
- Riesgo: apagar superficies operativas complique observabilidad.
  - Mitigación: distinguir claramente vida (`/health`) de diagnóstico interno y
    mover lo segundo detrás de auth o red interna.
- Riesgo: endurecer CSP o URLs externas rompa highlights legítimos.
  - Mitigación: inventariar hosts permitidos antes de activar la policy y añadir
    fallback seguro cuando una URL no pase la validación.
- Riesgo: reducir persistencia offline afecte UX percibida.
  - Mitigación: conservar solo preferencias necesarias y medir qué estado
    realmente requiere rehidratación entre sesiones.

Pruebas y validación
--------------------
- Backend
  - Tests unitarios de auth para demostrar que rutas admin fallan sin key.
  - Tests de feedback para validar rechazo de anónimos y de payloads inválidos.
  - Tests de readiness/monitor para asegurar ausencia de excepciones crudas.
  - Tests de repositorios para fallar cuando `MONGO_URI` no está presente.
  - Revalidación con `./scripts/quality_gate.sh backend`.
- Frontend
  - Tests de utilidad de URL segura: esquemas, host allowlist y rechazos.
  - Tests de componentes para verificar `noopener`, `sandbox` y fallback visual.
  - Tests de configuración de cache o snapshots controlados del service worker.
  - Revalidación con `./scripts/quality_gate.sh frontend`.
- Cierre full-stack
  - `./scripts/quality_gate.sh all`
  - Revisión manual de headers/config de despliegue cuando aplique.

Entregables
-----------
- `backend/specs/security-hardening/spec.md`
- `backend/specs/security-hardening/plan.md`
- `backend/specs/security-hardening/tasks.md`
- Suite mínima de regresión de seguridad backend/frontend
- Documentación de desarrollo y despliegue actualizada

Supuestos y decisiones no resueltas
-----------------------------------
- Se asume que el producto no tiene todavía identidad de usuario final robusta,
  por lo que el cierre inicial de feedback priorizará seguridad sobre apertura.
- Se asume que `GET /health` debe seguir público por necesidades de Render.
- Si el equipo decide mantener métricas públicas por compatibilidad, necesitará
  justificarlo explícitamente fuera de esta spec porque hoy no es el baseline
  seguro.

Siguientes pasos inmediatos
---------------------------
1. Atacar primero los gaps de severidad alta: bypass admin y feedback anónimo.
2. Cerrar la fuga de errores y superficies operativas expuestas.
3. Endurecer el contrato Mongo y después pasar al frontend/PWA.